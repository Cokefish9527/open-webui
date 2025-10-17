"""
用户首次进入后的企业/默认项目/主线任务幂等补种编排器
"""

import logging
from typing import Optional, Dict, Any, List

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.users import Users
from open_webui.models.hsai_companies import Companies, CompanyForm
from open_webui.models.hsai_projects import (
    HSAIProjects,
    HSAIProjectForm,
)
from open_webui.models.hsai_tasks import (
    HSAITasks,
    HSAITaskForm,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


def _get_business_name(user) -> str:
    if getattr(user, "business_name", None):
        return user.business_name
    info = getattr(user, "info", None)
    if isinstance(info, dict) and info.get("business_name"):
        return str(info.get("business_name"))
    return "HSAI"


def ensure_company_project_and_main_tasks(user_id: str) -> Dict[str, Any]:
    """
    幂等地确保：
    1) 用户所属公司存在（按名称），
    2) 存在默认项目（按约定名称），
    3) 主线任务按模板派生（不重复）。
    返回执行摘要。
    """
    summary = {
        "created_company": False,
        "created_project": False,
        "seeded_main_tasks": [],
    }

    user = Users.get_user_by_id(user_id)
    if not user:
        log.warning(f"ensure_company_project_and_main_tasks: 用户不存在 user_id={user_id}")
        return summary

    business_name = _get_business_name(user)

    # 1) Company（按名称幂等）
    company = Companies.get_company_by_name(business_name)
    if not company:
        form = CompanyForm(name=business_name)
        company = Companies.insert_new_company(owner_user_id=user_id, form_data=form)
        if company:
            summary["created_company"] = True
            log.info(f"创建公司成功 name={business_name}")
        else:
            log.error("创建公司失败，将继续后续幂等检查（允许无 company_id 的项目创建）")

    # 2) 默认项目（名称规则）
    default_project_name = f"{business_name}-默认项目"
    existing_projects = HSAIProjects.get_projects_by_user_id(user_id, status=None, limit=100, offset=0)
    project = None
    for p in existing_projects:
        if p.name == default_project_name:
            project = p
            break
    if not project:
        pform = HSAIProjectForm(
            name=default_project_name,
            description="系统自动创建的默认项目",
            business_name=business_name,
            company_info=None,
            config={"is_default": True},
            organization_id=None,
        )
        project = HSAIProjects.insert_new_project(user_id, pform)
        if project:
            summary["created_project"] = True
            log.info(f"创建默认项目成功 name={default_project_name}")
        else:
            log.error("创建默认项目失败，终止主线任务派生")
            return summary

    # 3) 主线任务派生（依据模板，按标题+category 幂等）
    try:
        from open_webui.routers.hsai_projects import PROJECT_MAIN_TASK_TEMPLATES  # 仅取模板常量
    except Exception:
        PROJECT_MAIN_TASK_TEMPLATES = {}

    existing_tasks = HSAITasks.get_tasks_by_user_id(user_id, project_id=project.id, limit=200, offset=0)
    existing_main_titles = {t.title for t in existing_tasks if (getattr(t, "task_category", None) == "main")}

    for key, tmpl in (PROJECT_MAIN_TASK_TEMPLATES or {}).items():
        title = tmpl.get("title")
        if not title or title in existing_main_titles:
            continue
        form = HSAITaskForm(
            title=title,
            description=tmpl.get("description"),
            task_type=str(tmpl.get("task_type") or "workflow_execution"),
            task_category="main",
            assignee_id=None,
            chat_id=None,
            project_id=project.id,
            config={"workflow_type": tmpl.get("workflow_type")},
            prompt_config=tmpl.get("prompt_config") or {},
            workflow_id=None,
            parent_task_id=None,
            priority=int(tmpl.get("priority") or 0),
        )
        created = HSAITasks.insert_new_task(user_id, form)
        if created:
            summary["seeded_main_tasks"].append(title)

    return summary

