"""Ensure enterprise membership + default项目/任务编排 for external admin flows."""

import logging
from typing import Dict, Any, Optional

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.users import Users
from open_webui.models.hsai_companies import Companies, CompanyForm, CompanyModel
from open_webui.services.onboarding_orchestrator import (
    ensure_company_project_and_main_tasks,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("SERVICES", "INFO"))


def _normalize_company_name(name: str) -> str:
    normalized = (name or "").strip()
    if not normalized:
        raise ValueError("business_name is required")
    return normalized


def _update_user_company(user_id: str, company_id: str, business_name: str, *, set_admin_role: bool) -> None:
    updates: Dict[str, Any] = {
        "company_id": company_id,
        "business_name": business_name,
    }
    if set_admin_role:
        user = Users.get_user_by_id(user_id)
        if user and (user.role in (None, "", "pending")):
            updates["role"] = "admin"
    Users.update_user_by_id(user_id, updates)


def provision_enterprise_membership(
    *,
    user_id: str,
    business_name: str,
    promote_as_admin: bool = True,
) -> Dict[str, Any]:
    """
    Ensure the specified user belongs to the enterprise identified by business_name.
    If the company does not exist, create it, set the user as owner/admin, and
    trigger default project + task provisioning.
    """
    normalized_name = _normalize_company_name(business_name)
    summary: Dict[str, Any] = {
        "business_name": normalized_name,
        "company_created": False,
        "default_project_created": False,
        "tasks_seeded": [],
    }

    company: Optional[CompanyModel] = Companies.get_company_by_name(normalized_name)
    if not company:
        form = CompanyForm(
            name=normalized_name,
            description=f"{normalized_name} 由外部管理端自动创建",
        )
        company = Companies.insert_new_company(owner_user_id=user_id, form_data=form)
        if not company:
            raise RuntimeError("failed to create company record")
        summary["company_created"] = True
        summary["company_id"] = company.id
    else:
        summary["company_id"] = company.id

    _update_user_company(
        user_id,
        company.id,
        normalized_name,
        set_admin_role=summary["company_created"] and promote_as_admin,
    )

    if summary["company_created"]:
        # 触发幂等编排：默认项目 + 主线任务
        orchestration = ensure_company_project_and_main_tasks(user_id)
        summary["default_project_created"] = orchestration.get("created_project", False)
        summary["tasks_seeded"] = orchestration.get("seeded_main_tasks", [])

    return summary
