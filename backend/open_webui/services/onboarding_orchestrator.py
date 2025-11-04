"""
用户首次进入后的企业/默认项目/主线任务幂等补种编排器
"""

import logging
import time
import uuid
from typing import Dict, Any

from sqlalchemy.exc import SQLAlchemyError

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import get_db
from open_webui.models.users import User
from open_webui.models.hsai_companies import Company
from open_webui.models.hsai_projects import HSAIProject
from open_webui.models.hsai_tasks import (
    HSAITask,
    HSAITaskStatus,
    HSAIRecurringState,
)
from open_webui.models.hsai_outbox import (
    HSAIOutboxEvent,
    OutboxEventStatus,
)
from open_webui.models.hsai_idempotent_ops import (
    HSAIIdempotentOperation,
    OperationStatus,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


def _get_business_name(user: User) -> str:
    business_name = getattr(user, "business_name", None)
    if business_name:
        return business_name
    info = getattr(user, "info", None)
    if isinstance(info, dict) and info.get("business_name"):
        return str(info.get("business_name"))
    return "HSAI"


def _build_operation_id(user_id: str, business_name: str) -> str:
    return f"onboarding:{user_id}:{business_name.lower()}"


def ensure_company_project_and_main_tasks(user_id: str) -> Dict[str, Any]:
    """
    幂等地确保：
        1. 企业记录存在
        2. 默认项目存在
        3. 主线任务按照模板补种

    Returns:
        Dict[str, Any]: 执行摘要
    """
    summary = {
        "created_company": False,
        "created_project": False,
        "seeded_main_tasks": [],
    }

    with get_db() as db:
        user = db.get(User, user_id)
        if not user:
            log.warning("ensure_company_project_and_main_tasks: 用户不存在 user_id=%s", user_id)
            return summary

        business_name = _get_business_name(user)
        operation_id = _build_operation_id(user_id, business_name)
        now_ts = int(time.time())

        record = (
            db.query(HSAIIdempotentOperation)
            .filter_by(operation_id=operation_id)
            .with_for_update(nowait=False)
            .first()
        )
        if record and record.status == OperationStatus.COMPLETED:
            log.debug("幂等操作已完成 operation_id=%s", operation_id)
            return summary

        if not record:
            record = HSAIIdempotentOperation(
                id=str(uuid.uuid4()),
                operation_id=operation_id,
                status=OperationStatus.PENDING,
                context={"user_id": user_id, "business_name": business_name},
                created_at=now_ts,
                updated_at=now_ts,
            )
            db.add(record)
        else:
            record.status = OperationStatus.PENDING
            record.updated_at = now_ts

        try:
            company = (
                db.query(Company)
                .filter_by(name=business_name)
                .with_for_update(nowait=False)
                .first()
            )
            if not company:
                company = Company(
                    id=str(uuid.uuid4()),
                    name=business_name,
                    description=None,
                    owner_user_id=user_id,
                    company_info=None,
                    status="active",
                    config=None,
                    created_at=now_ts,
                    updated_at=now_ts,
                )
                db.add(company)
                summary["created_company"] = True

            default_project_name = f"{business_name}-默认项目"
            project = (
                db.query(HSAIProject)
                .filter_by(name=default_project_name, user_id=user_id)
                .with_for_update(nowait=False)
                .first()
            )
            if not project:
                project = HSAIProject(
                    id=str(uuid.uuid4()),
                    name=default_project_name,
                    description="系统自动创建的默认项目",
                    business_name=business_name,
                    company_info=None,
                    user_id=user_id,
                    status="active",
                    config={"is_default": True},
                    company_id=getattr(company, "id", None),
                    created_at=now_ts,
                    updated_at=now_ts,
                )
                db.add(project)
                summary["created_project"] = True

            try:
                from open_webui.routers.hsai_projects import PROJECT_MAIN_TASK_TEMPLATES
            except Exception:  # pylint: disable=broad-except
                PROJECT_MAIN_TASK_TEMPLATES = {}

            existing_titles = {
                row[0]
                for row in db.query(HSAITask.title).filter_by(
                    project_id=project.id,
                    task_category="main",
                )
            }
            seeded_titles = []
            for template_key, tmpl in (PROJECT_MAIN_TASK_TEMPLATES or {}).items():
                title = tmpl.get("title")
                if not title or title in existing_titles:
                    continue
                is_recurring = bool((tmpl.get("config") or {}).get("recurring"))
                task = HSAITask(
                    id=str(uuid.uuid4()),
                    title=title,
                    description=tmpl.get("description"),
                    task_type=tmpl.get("task_type") or "workflow_execution",
                    task_category=tmpl.get("task_category") or "main",
                    status=HSAITaskStatus.PENDING.value,
                    user_id=user_id,
                    assignee_id=None,
                    chat_id=None,
                    project_id=project.id,
                    config=tmpl.get("config"),
                    prompt_config=tmpl.get("prompt_config") or {},
                    is_recurring=is_recurring,
                    recurring_state=HSAIRecurringState.IDLE.value if is_recurring else None,
                    last_run_at=None,
                    next_run_at=None,
                    external_controller=None,
                    recurring_meta=None,
                    workflow_id=None,
                    parent_task_id=None,
                    priority=int(tmpl.get("priority") or 0),
                    created_at=now_ts,
                    updated_at=now_ts,
                )
                db.add(task)
                existing_titles.add(title)
                seeded_titles.append(title)
                log.debug("主线任务补种 success title=%s template_key=%s", title, template_key)

            summary["seeded_main_tasks"].extend(seeded_titles)

            if summary["created_company"] or summary["created_project"] or seeded_titles:
                event = HSAIOutboxEvent(
                    id=str(uuid.uuid4()),
                    operation_id=operation_id,
                    event_type="onboarding.seed_summary",
                    payload={
                        "user_id": user_id,
                        "company_id": getattr(company, "id", None),
                        "project_id": project.id,
                        "seeded_titles": seeded_titles,
                        "flags": {
                            "created_company": summary["created_company"],
                            "created_project": summary["created_project"],
                        },
                    },
                    status=OutboxEventStatus.PENDING,
                    attempts=0,
                    last_error=None,
                    scheduled_at=None,
                    created_at=now_ts,
                    updated_at=now_ts,
                )
                db.add(event)

            record.status = OperationStatus.COMPLETED
            record.context = {
                "company_id": getattr(company, "id", None),
                "project_id": project.id,
                "seeded_titles": seeded_titles,
            }
            record.last_error = None
            record.updated_at = int(time.time())
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            log.error("Onboarding orchestration SQL error: user_id=%s err=%s", user_id, exc, exc_info=True)
            record.status = OperationStatus.FAILED
            record.last_error = str(exc)
            record.updated_at = int(time.time())
            try:
                db.commit()
            except SQLAlchemyError as inner_exc:
                db.rollback()
                log.error("Failed to persist idempotent operation failure: %s", inner_exc, exc_info=True)
        except Exception as exc:  # pylint: disable=broad-except
            db.rollback()
            log.error("Onboarding orchestration unexpected error: user_id=%s err=%s", user_id, exc, exc_info=True)
            record.status = OperationStatus.FAILED
            record.last_error = str(exc)
            record.updated_at = int(time.time())
            try:
                db.commit()
            except SQLAlchemyError as inner_exc:
                db.rollback()
                log.error("Failed to persist idempotent operation failure: %s", inner_exc, exc_info=True)

    return summary

