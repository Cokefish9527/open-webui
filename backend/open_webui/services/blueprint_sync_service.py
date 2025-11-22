"""
Strategic blueprint synchronization service.

When a `blue_image_content` message is received from the Redis queue this
service pulls the latest blueprint information from the n8n database,
persists it into the main blueprint progress tables, keeps an audit trail,
and ensures the corresponding main tasks are created or updated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from zoneinfo import ZoneInfo

from open_webui.internal.db_n8n import get_n8n_db
from open_webui.models.hsai_blueprint_progress import (
    BlueprintProgressState,
    HSAIBlueprintProgressModel,
    HSAIBlueprintProgressTable,
    HSAITaskBlueprintLinksTable,
    HSAITaskBlueprintLinkModel,
)
from open_webui.models.hsai_projects import HSAIProjects
from open_webui.models.hsai_tasks import (
    HSAITasks,
    HSAITaskForm,
    HSAITaskModel,
    HSAITaskStatus,
    HSAITaskUpdateForm,
    HSAIRecurringState,
    HSAITaskStateLogs,
)
from open_webui.services.onboarding_orchestrator import ensure_company_project_and_main_tasks
from open_webui.services.task_completion_service import evaluate_project_tasks
from open_webui.services.task_template_registry import (
    TaskTemplate,
    get_task_template,
    task_template_registry,
)
from open_webui.socket.hsai_events import HSAI_WEBSOCKET_EVENTS
from open_webui.utils.conversation_ender import end_conversation_for_task_completion

log = logging.getLogger(__name__)

COMPANY_INFO_TEMPLATE_KEY = "company_info_collection"


@dataclass
class BlueprintSyncNotification:
    event: str
    payload: Dict[str, Any]


@dataclass
class BlueprintSyncResult:
    progress: Optional[HSAIBlueprintProgressModel] = None
    created_tasks: List[HSAITaskModel] = field(default_factory=list)
    updated_tasks: List[HSAITaskModel] = field(default_factory=list)
    generated_subtasks: List[HSAITaskModel] = field(default_factory=list)
    notifications: List[BlueprintSyncNotification] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)


def _fetch_latest_blueprint_from_n8n() -> Optional[Dict[str, Any]]:
    with get_n8n_db() as db:
        stmt = text(
            """
            SELECT
                id,
                blueprintversion AS "blueprintVersion",
                executiondurationdays AS "executionDurationDays",
                plannedtotalposts AS "plannedTotalPosts",
                postingfrequency AS "postingFrequency",
                requiredtiktokaccounts AS "requiredTiktokAccounts",
                session_id,
                request_id,
                user_id,
                socket_id,
                blue_image,
                createdat AS "createdAt",
                updatedat AS "updatedAt"
            FROM hsai_extraction_blueprint
            ORDER BY createdat DESC
            LIMIT 1
            """
        )
        row = db.execute(stmt).mappings().first()
        return dict(row) if row else None


def _resolve_project_for_user(user_id: str) -> Optional[str]:
    projects = HSAIProjects.get_projects_by_user_id(user_id, limit=50)
    default_project = None
    for project in projects:
        config = project.config or {}
        if isinstance(config, dict) and config.get("is_default"):
            default_project = project
            break
    if not default_project and projects:
        default_project = projects[0]

    if default_project:
        return default_project.id

    summary = ensure_company_project_and_main_tasks(user_id)
    log.info(
        "ensure_company_project_and_main_tasks summary for user %s: %s",
        user_id,
        summary,
    )
    projects = HSAIProjects.get_projects_by_user_id(user_id, limit=1)
    return projects[0].id if projects else None


def _derive_daily_cycle_config(
    blueprint_row: Dict[str, Any],
    existing_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cycle_template = get_task_template("daily_publish_cycle")
    base_window = {}
    if cycle_template:
        base_window = (cycle_template.config or {}).get("default_window", {})
    frequency_text = blueprint_row.get("postingFrequency") or "1条/天"

    occurrences_per_day = 1
    try:
        if "/" in frequency_text:
            value, unit = frequency_text.split("/", maxsplit=1)
            value = "".join([c for c in value if c.isdigit()])
            occurrences = int(value) if value else 1
            if "天" in unit or "day" in unit.lower():
                occurrences_per_day = max(1, occurrences)
    except Exception as exc:
        log.warning("Failed to parse posting frequency '%s': %s", frequency_text, exc)

    config = existing_config.copy() if isinstance(existing_config, dict) else {}
    config.update(
        {
            "frequency": frequency_text,
            "occurrences_per_day": occurrences_per_day,
            "window": base_window or {"hour": 9, "minute": 0, "timezone": "Asia/Shanghai"},
        }
    )
    return config


def _build_progress_payload(
    blueprint_row: Dict[str, Any],
    existing_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    summary_md = blueprint_row.get("blue_image")
    digest = {
        "blueprint_id": str(blueprint_row.get("id")),
        "session_id": blueprint_row.get("session_id"),
        "request_id": blueprint_row.get("request_id"),
        "user_id": blueprint_row.get("user_id"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    daily_cycle_config = _derive_daily_cycle_config(blueprint_row, existing_config)
    return {
        "blueprint_version": blueprint_row.get("blueprintVersion") or "v1",
        "execution_duration_days": blueprint_row.get("executionDurationDays"),
        "planned_total_posts": blueprint_row.get("plannedTotalPosts"),
        "posting_frequency": blueprint_row.get("postingFrequency"),
        "required_tiktok_accounts": blueprint_row.get("requiredTiktokAccounts"),
        "summary_md": summary_md,
        "blueprint_raw": summary_md,
        "latest_digest": digest,
        "progress_state": BlueprintProgressState.RUNNING,
        "daily_cycle_config": daily_cycle_config,
    }


def _create_or_update_task_from_template(
    template_key: str,
    template: TaskTemplate,
    user_id: str,
    project_id: str,
    link: Optional[HSAITaskBlueprintLinkModel],
    blueprint_version: str,
    progress_id: str,
) -> Tuple[Optional[HSAITaskModel], Optional[HSAITaskModel]]:
    """Return (created_task, updated_task)."""
    config = dict(template.config or {})
    config.setdefault("blueprint_version", blueprint_version)
    config.setdefault("template_key", template_key)
    config.setdefault("progress_id", progress_id)

    is_recurring = bool(config.get("recurring"))

    if link:
        existing_task = HSAITasks.get_task_by_id(link.task_id)
        if not existing_task:
            link = None  # treat as missing
        else:
            needs_update = False
            update_payload: Dict[str, Any] = {}
            if existing_task.title != template.title:
                update_payload["title"] = template.title
                needs_update = True
            if template.description and existing_task.description != template.description:
                update_payload["description"] = template.description
                needs_update = True
            merged_config = existing_task.config or {}
            merged = {**merged_config, **config}
            if merged != merged_config:
                update_payload["config"] = merged
                needs_update = True

            if existing_task.is_recurring != is_recurring:
                update_payload["is_recurring"] = is_recurring
                needs_update = True
            if is_recurring and not (existing_task.recurring_state or ""):
                update_payload["recurring_state"] = HSAIRecurringState.IDLE.value
                needs_update = True
            if not is_recurring and (existing_task.recurring_state or None):
                update_payload["recurring_state"] = None
                update_payload["external_controller"] = None
                update_payload["next_run_at"] = None
                update_payload["last_run_at"] = None
                needs_update = True

            if needs_update:
                updated = HSAITasks.update_task_by_id(
                    existing_task.id, HSAITaskUpdateForm(**update_payload)
                )
                return (None, updated)
            return (None, None)

    form = HSAITaskForm(
        title=template.title,
        description=template.description,
        task_type=template.task_type,
        task_category=template.task_category,
        project_id=project_id,
        config=config,
        prompt_config=template.prompt_config,
        priority=int(template.priority or 0),
        is_recurring=is_recurring,
        recurring_state=HSAIRecurringState.IDLE.value if is_recurring else None,
    )
    created = HSAITasks.insert_new_task(user_id, form)
    return (created, None)


def _complete_company_info_task(project_id: str, user_id: str) -> Optional[HSAITaskModel]:
    # 处理多种模板键
    template_keys = ["company_info_collection", "company_info_collection_fallback"]
    
    tasks = HSAITasks.get_tasks_by_user_id(
        user_id=user_id,
        project_id=project_id,
        limit=50,
    )
    for task in tasks:
        config = task.config or {}
        if config.get("template_key") not in template_keys:
            continue
        if task.status == HSAITaskStatus.COMPLETED.value:
            continue  # 已完成的任务跳过
        updated = HSAITasks.update_task_by_id(
            task.id,
            HSAITaskUpdateForm(status=HSAITaskStatus.COMPLETED.value),
        )
        if updated:
            try:
                HSAITaskStateLogs.append_log(
                    task_id=updated.id,
                    from_state=task.status,
                    to_state=HSAITaskStatus.COMPLETED.value,
                    operator_id=user_id,
                    operator_name=None,
                    source="blueprint_sync",
                    message="蓝图同步完成，企业信息收集任务自动完成",
                    snapshot_json={"auto_completed": True},
                )
            except Exception as exc:  # pylint: disable=broad-except
                log.warning("Failed to append info collection task log: %s", exc)
        return updated or task
    return None


def _sync_task_links(
    progress: HSAIBlueprintProgressModel,
    user_id: str,
) -> Tuple[List[HSAITaskModel], List[HSAITaskModel]]:
    created: List[HSAITaskModel] = []
    updated: List[HSAITaskModel] = []

    try:
        blueprint_templates = list(task_template_registry.iter_blueprint_templates())
    except Exception as registry_exc:  # pylint: disable=broad-except
        log.error("Failed to load blueprint task templates: %s", registry_exc)
        blueprint_templates = []

    for template in blueprint_templates:
        template_key = template.key
        link = None
        links = HSAITaskBlueprintLinksTable.get_by_progress(progress.id, template_key=template_key)
        if links:
            link = links[0]

        created_task, updated_task = _create_or_update_task_from_template(
            template_key=template_key,
            template=template,
            user_id=user_id,
            project_id=progress.project_id,
            link=link,
            blueprint_version=progress.blueprint_version,
            progress_id=progress.id,
        )
        if created_task:
            created.append(created_task)
            if created_task.is_recurring:
                try:
                    HSAITaskStateLogs.append_log(
                        task_id=created_task.id,
                        from_state=None,
                        to_state=created_task.recurring_state or HSAIRecurringState.IDLE.value,
                        operator_id=user_id,
                        operator_name=None,
                        source="blueprint_sync",
                        message="初始化循环任务状态",
                        snapshot_json=created_task.model_dump(),
                    )
                except Exception as exc:
                    log.warning("Failed to append recurring log for %s: %s", created_task.id, exc)
            HSAITaskBlueprintLinksTable.upsert_link(
                progress_id=progress.id,
                task_id=created_task.id,
                template_key=template_key,
                link_metadata={
                    "blueprint_version": progress.blueprint_version,
                    "progress_id": progress.id,
                },
            )
        if updated_task:
            updated.append(updated_task)
            HSAITaskBlueprintLinksTable.upsert_link(
                progress_id=progress.id,
                task_id=updated_task.id,
                template_key=template_key,
                link_metadata={
                    "blueprint_version": progress.blueprint_version,
                    "progress_id": progress.id,
                },
            )

    return created, updated


def _all_prerequisites_completed(
    progress_id: str,
    user_id: str,
    project_id: str,
) -> bool:
    cycle_template = get_task_template("daily_publish_cycle")
    config = cycle_template.config if cycle_template else {}
    prerequisite_keys = (config or {}).get("dependencies", [])
    if not prerequisite_keys:
        return True
    links = HSAITaskBlueprintLinksTable.get_by_progress(progress_id)
    template_map = {link.template_key: link for link in links}
    for key in prerequisite_keys:
        link = template_map.get(key)
        if not link:
            return False
        task = HSAITasks.get_task_by_id(link.task_id)
        if not task or task.status != HSAITaskStatus.COMPLETED.value:
            return False
    return True


def _get_timezone(window_cfg: Dict[str, Any]) -> timezone:
    tz_name = window_cfg.get("timezone") or "UTC"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        log.warning("Unsupported timezone '%s', falling back to UTC", tz_name)
        return timezone.utc


def _maybe_generate_daily_subtask(
    progress: HSAIBlueprintProgressModel,
    user_id: str,
    project_id: str,
) -> Optional[HSAITaskModel]:
    config = progress.daily_cycle_config or {}
    window_cfg = config.get("window", {})
    tz = _get_timezone(window_cfg)

    now_local = datetime.now(tz)
    scheduled_time = now_local.replace(
        hour=int(window_cfg.get("hour", 9)),
        minute=int(window_cfg.get("minute", 0)),
        second=0,
        microsecond=0,
    )

    if now_local < scheduled_time:
        return None

    if not _all_prerequisites_completed(progress.id, user_id, project_id):
        return None

    # locate main cycle task
    links = HSAITaskBlueprintLinksTable.get_by_progress(progress.id, template_key="daily_publish_cycle")
    if not links:
        return None
    cycle_task = HSAITasks.get_task_by_id(links[0].task_id)
    if not cycle_task:
        return None

    # check whether today's subtask already exists
    tasks = HSAITasks.get_tasks_by_user_id(
        user_id=user_id,
        project_id=project_id,
        task_category="blueprint_daily",
        limit=200,
    )
    today_key = now_local.strftime("%Y-%m-%d")
    for task in tasks:
        task_config = task.config or {}
        if task_config.get("scheduled_for") == today_key and task.parent_task_id == cycle_task.id:
            return None

    title = f"{today_key} 视频发布"
    description = "依据战略蓝图配置完成当日视频发布动作，并回填效果数据。"
    subtask_form = HSAITaskForm(
        title=title,
        description=description,
        task_type="platform_publishing",
        task_category="blueprint_daily",
        project_id=project_id,
        parent_task_id=cycle_task.id,
        priority=max(10, (cycle_task.priority or 0) - 10),
        config={
            "scheduled_for": today_key,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "template_key": "daily_publish_cycle",
        },
    )
    return HSAITasks.insert_new_task(user_id, subtask_form)


def sync_blueprint_for_user(
    message: Dict[str, Any],
) -> BlueprintSyncResult:
    """
    Sync blueprint progress for the user behind the incoming Redis message.
    """
    result = BlueprintSyncResult()

    user_id = message.get("user_id")
    if not user_id:
        result.logs.append("消息缺少 user_id，跳过蓝图同步。")
        return result

    project_id = _resolve_project_for_user(user_id)
    if not project_id:
        result.logs.append("未能定位或创建项目，无法关联蓝图进度。")
        return result

    blueprint_row = _fetch_latest_blueprint_from_n8n()
    if not blueprint_row:
        result.logs.append("n8n_workflow 库未找到战略蓝图记录。")
        return result

    existing = HSAIBlueprintProgressTable.get_by_project(project_id)
    payload = _build_progress_payload(
        blueprint_row,
        existing_config=existing.daily_cycle_config if existing else None,
    )
    progress = HSAIBlueprintProgressTable.upsert_progress(
        project_id=project_id,
        payload=payload,
        operator_id=user_id,
    )
    result.progress = progress
    result.logs.append(f"战略蓝图版本 {progress.blueprint_version} 已同步至项目 {project_id}。")

    # 只有在首次处理蓝图时才更新信息收集状态
    info_task = None
    if not progress.info_collection_processed:
        info_task = _complete_company_info_task(project_id=project_id, user_id=user_id)
        if info_task:
            result.updated_tasks.append(info_task)
            result.logs.append("企业信息收集任务已在蓝图同步后标记为完成")
            
            # 使用新的通用对话结束机制
            try:
                # 在新线程中运行异步函数
                import asyncio
                import threading
                
                def run_async(coro):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(coro)
                    finally:
                        loop.close()
                
                # 获取session_id用于对话结束通知
                session_id = message.get("session_id")
                
                # 在新线程中调用异步函数
                thread = threading.Thread(
                    target=run_async,
                    args=(end_conversation_for_task_completion(
                        user_id=user_id,
                        task_id=info_task.id,
                        session_id=session_id,
                        task_type="企业信息收集"
                    ),)
                )
                thread.start()
            except Exception as e:
                log.error(f"发送对话结束通知时发生错误: {e}")
            
            # 更新蓝图进度记录，标记信息收集已完成处理
            try:
                HSAIBlueprintProgressTable.upsert_progress(
                    project_id=project_id,
                    payload={"info_collection_processed": True},
                    operator_id=user_id,
                )
                result.logs.append("已标记信息收集状态为已处理")
            except Exception as exc:
                log.warning("更新蓝图信息收集处理状态失败: %s", exc)
        else:
            result.logs.append("未找到需要完成的企业信息收集任务")
    else:
        result.logs.append("信息收集状态已处理过，跳过重复处理")

    created_tasks, updated_tasks = _sync_task_links(progress, user_id=user_id)
    result.created_tasks.extend(created_tasks)
    result.updated_tasks.extend([task for task in updated_tasks if task])

    for task in created_tasks:
        result.notifications.append(
            BlueprintSyncNotification(
                event="hsai_task_blueprint_update",
                payload={
                    "action": "created",
                    "task_id": task.id,
                    "project_id": project_id,
                    "template_key": task.config.get("template_key") if task.config else None,
                    "title": task.title,
                    "status": task.status,
                },
            )
        )
    for task in updated_tasks:
        if not task:
            continue
        result.notifications.append(
            BlueprintSyncNotification(
                event="hsai_task_blueprint_update",
                payload={
                    "action": "updated",
                    "task_id": task.id,
                    "project_id": project_id,
                    "template_key": task.config.get("template_key") if task.config else None,
                    "title": task.title,
                    "status": task.status,
                },
            )
        )

    subtask = _maybe_generate_daily_subtask(progress, user_id=user_id, project_id=project_id)
    if subtask:
        result.generated_subtasks.append(subtask)
        result.notifications.append(
            BlueprintSyncNotification(
                event="hsai_task_blueprint_update",
                payload={
                    "action": "created",
                    "task_id": subtask.id,
                    "project_id": project_id,
                    "template_key": "daily_publish_cycle_sub",
                    "title": subtask.title,
                    "status": subtask.status,
                },
            )
        )

    result.notifications.append(
        BlueprintSyncNotification(
            event=HSAI_WEBSOCKET_EVENTS.get("RESPONSE", "hsai_response"),
            payload={
                "type": "hsai_blueprint_progress",
                "success": True,
                "progress": progress.model_dump(),
                "message": "战略蓝图进度已更新。",
            },
        )
    )

    try:
        evaluations = evaluate_project_tasks(project_id=project_id, user_id=user_id)
        for summary in evaluations:
            result.logs.append(f"任务评估: {summary}")
    except Exception as exc:  # pylint: disable=broad-except
        log.error("任务评估失败 project=%s: %s", project_id, exc, exc_info=True)

    return result
