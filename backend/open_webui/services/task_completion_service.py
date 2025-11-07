import logging
import time
from collections import Counter
from typing import Dict, List, Optional

from open_webui.models.hsai_projects import HSAIProjects
from open_webui.models.hsai_tasks import (
    HSAITasks,
    HSAITaskModel,
    HSAITaskStatus,
    HSAITaskUpdateForm,
    HSAITaskStateLogs,
)
from open_webui.models.hsai_materials import HSAIMaterials
from open_webui.models.hsai_blueprint_progress import HSAIBlueprintProgressTable
from open_webui.models.social_accounts import SocialAccounts
from open_webui.models.admin_checklists import ChecklistTemplates
from open_webui.models.hsai_business_video_content_learned import (
    HSAIBusinessVideoContentLearneds,
)
from open_webui.services.task_template_registry import task_template_registry

log = logging.getLogger(__name__)

DEFAULT_RULES: Dict[str, Dict[str, object]] = {
    "social_matrix_setup": {
        "platform": "tiktok",
        "required_accounts": 3,
    },
    "material_enrichment": {
        "required_items": 12,
        "checklist_template_code": None,
    },
    "video_learning": {
        "script_threshold": 10,
        "status_whitelist": ["pending", "unused", None],
    },
}


def evaluate_project_tasks(project_id: str, user_id: str) -> List[str]:
    """Evaluate auto-completion rules for blueprint tasks."""
    project = HSAIProjects.get_project_by_id(project_id)
    if not project:
        return []

    blueprint = HSAIBlueprintProgressTable.get_by_project(project_id)
    results: List[str] = []

    result = _evaluate_social_matrix(project, blueprint)
    if result:
        results.append(result)

    result = _evaluate_material_enrichment(project, blueprint)
    if result:
        results.append(result)

    result = _evaluate_video_learning(project)
    if result:
        results.append(result)

    return results


def _evaluate_social_matrix(project, blueprint) -> Optional[str]:
    template_key = "social_matrix_setup"
    tasks = _get_tasks_for_template(project.id, template_key)
    if not tasks:
        return None

    rule = _get_rule(template_key)
    platform = str(rule.get("platform") or "tiktok")
    required_accounts = int(rule.get("required_accounts") or 1)
    if blueprint and blueprint.required_tiktok_accounts:
        try:
            required_accounts = max(
                required_accounts, int(blueprint.required_tiktok_accounts)
            )
        except (TypeError, ValueError):
            pass

    company_id = project.company_id
    active_accounts = SocialAccounts.count_active_accounts(company_id, platform=platform)

    metrics = {
        "platform": platform,
        "active_accounts": active_accounts,
        "required_accounts": required_accounts,
    }

    message: Optional[str] = None
    status: Optional[HSAITaskStatus] = None
    if active_accounts >= required_accounts:
        status = HSAITaskStatus.COMPLETED
        message = f"{platform} 账号满足条件 ({active_accounts}/{required_accounts})"
    else:
        message = f"{platform} 账号不足 ({active_accounts}/{required_accounts})"

    for task in tasks:
        _update_task_progress(task, status=status, progress=metrics, message=message)

    return f"social_matrix: {metrics}"


def _evaluate_material_enrichment(project, blueprint) -> Optional[str]:
    template_key = "material_enrichment"
    tasks = _get_tasks_for_template(project.id, template_key)
    if not tasks:
        return None

    rule = _get_rule(template_key)
    checklist_code = rule.get("checklist_template_code")
    required_items = int(rule.get("required_items") or 10)

    checklist_template = ChecklistTemplates.get_by_code(checklist_code)
    if checklist_template:
        required_items = (
            checklist_template.required_items
            or checklist_template.total_items
            or required_items
        )

    owner_user_id = project.user_id
    materials = HSAIMaterials.get_materials_by_user_id(owner_user_id)
    type_counter = Counter()
    for material in materials:
        material_type = (material.material_type or "unknown").lower()
        type_counter[material_type] += 1

    total_materials = sum(type_counter.values())
    metrics = {
        "total_materials": total_materials,
        "required_items": required_items,
        "type_counts": dict(type_counter),
    }

    status: Optional[HSAITaskStatus] = None
    message: Optional[str] = None
    if total_materials >= required_items:
        status = HSAITaskStatus.COMPLETED
        message = f"已上传 {total_materials}/{required_items} 项素材"
    else:
        message = f"素材不足 {total_materials}/{required_items}"

    for task in tasks:
        _update_task_progress(task, status=status, progress=metrics, message=message)

    return f"material_enrichment: {metrics}"


def _evaluate_video_learning(project) -> Optional[str]:
    template_key = "video_learning"
    tasks = _get_tasks_for_template(project.id, template_key)
    if not tasks:
        return None

    rule = _get_rule(template_key)
    threshold = int(rule.get("script_threshold") or 10)
    whitelist = rule.get("status_whitelist")
    if isinstance(whitelist, list):
        status_whitelist = whitelist
    else:
        status_whitelist = ["pending", "unused", None]

    business_name = getattr(project, "business_name", None)
    available_scripts = HSAIBusinessVideoContentLearneds.count_unused_scripts(
        business_name=business_name,
        status_whitelist=status_whitelist,
    )

    metrics = {
        "business_name": business_name,
        "available_scripts": available_scripts,
        "required_scripts": threshold,
    }

    status: Optional[HSAITaskStatus] = None
    message: Optional[str] = None
    if available_scripts >= threshold:
        status = HSAITaskStatus.COMPLETED
        message = f"脚本库存满足 {available_scripts}/{threshold}"
    else:
        message = f"脚本库存不足 {available_scripts}/{threshold}"

    for task in tasks:
        _update_task_progress(task, status=status, progress=metrics, message=message)

    return f"video_learning: {metrics}"


def _get_rule(template_key: str) -> Dict[str, object]:
    template = task_template_registry.get(template_key)
    base = dict(DEFAULT_RULES.get(template_key, {}))
    if template and isinstance(template.config, dict):
        base.update(template.config)
    return base


def _get_tasks_for_template(project_id: str, template_key: str) -> List[HSAITaskModel]:
    tasks = HSAITasks.get_tasks_by_project_id(project_id, limit=200)
    filtered: List[HSAITaskModel] = []
    for task in tasks:
        template = (task.config or {}).get("template_key")
        if template == template_key:
            filtered.append(task)
    return filtered


def _update_task_progress(
    task: HSAITaskModel,
    *,
    status: Optional[HSAITaskStatus],
    progress: Dict[str, object],
    message: Optional[str],
) -> None:
    updates: Dict[str, object] = {}
    config = dict(task.config or {})
    existing_metrics = config.get("progress_metrics") or {}
    if isinstance(existing_metrics, dict):
        existing_metrics.update(progress)
    else:
        existing_metrics = progress
    config["progress_metrics"] = existing_metrics
    updates["config"] = config

    if status and task.status != status.value:
        updates["status"] = status.value
    if status == HSAITaskStatus.COMPLETED and not task.completed_at:
        updates["completed_at"] = int(time.time())

    updated: Optional[HSAITaskModel] = None
    if updates:
        updated = HSAITasks.update_task_by_id(task.id, HSAITaskUpdateForm(**updates))

    if updated and "status" in updates:
        try:
            HSAITaskStateLogs.append_log(
                task_id=task.id,
                from_state=task.status,
                to_state=updates["status"],
                operator_id=None,
                operator_name=None,
                source="task_auto_evaluator",
                message=message,
                snapshot_json={"progress_metrics": existing_metrics},
            )
        except Exception as exc:  # pylint: disable=broad-except
            log.warning("Failed to append task log %s: %s", task.id, exc)
