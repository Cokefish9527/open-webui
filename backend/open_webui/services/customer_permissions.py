import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from open_webui.models.users import Users, UserModel, UserListResponse
from open_webui.models.hsai_companies import Companies, CompanyModel
from open_webui.config import (
    CUSTOMER_PERMISSION_TEMPLATE,
    DEFAULT_CUSTOMER_ROLE,
)

log = logging.getLogger(__name__)


def _parse_permission_template(raw_template: Any) -> Optional[dict]:
    """
    Normalize template stored in PersistentConfig (string / dict / None).
    """
    template = raw_template
    if template is None:
        return None

    if isinstance(template, str):
        template = template.strip()
        if not template:
            return None
        try:
            template = json.loads(template)
        except json.JSONDecodeError as exc:
            log.warning("invalid CUSTOMER_PERMISSION_TEMPLATE: %s", exc)
            return None

    if isinstance(template, dict):
        return template

    log.warning("Unsupported template payload type: %s", type(template))
    return None


class CustomerPermissionsService:
    def __init__(
        self,
        users_repository=Users,
        companies_repository=Companies,
    ):
        self.users = users_repository
        self.companies = companies_repository

    def get_user_permissions(self, user_id: str) -> Tuple[UserModel, Optional[dict]]:
        user = self.users.get_user_by_id(user_id)
        if not user:
            return None, None
        permissions = (user.settings or {}).get("permissions") if user.settings else None
        return user, permissions

    def update_user_permissions(
        self,
        user_id: str,
        *,
        role: Optional[str] = None,
        explicit_permissions: Optional[dict] = None,
        use_template: bool = False,
    ) -> Optional[Tuple[UserModel, Optional[dict]]]:
        user = self.users.get_user_by_id(user_id)
        if not user:
            return None

        if role:
            normalized_role = role if role in {"pending", "user", "admin"} else None
            if not normalized_role:
                raise ValueError("invalid role provided")
            self.users.update_user_role_by_id(user_id, normalized_role)

        if explicit_permissions is not None or use_template:
            permissions_payload = explicit_permissions
            if permissions_payload is None and use_template:
                permissions_payload = _parse_permission_template(
                    CUSTOMER_PERMISSION_TEMPLATE.value
                )

            if permissions_payload is not None:
                self.users.update_user_settings_by_id(
                    user_id, {"permissions": permissions_payload}
                )

        return self.get_user_permissions(user_id)

    def list_company_permissions(
        self,
        company_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[Optional[CompanyModel], UserListResponse, int, int]:
        normalized_page = max(page, 1)
        limit = max(1, min(page_size, 200))
        skip = (normalized_page - 1) * limit
        users = self.users.get_users(skip=skip, limit=limit, company_id=company_id)
        company = self.companies.get_company_by_id(company_id)
        return company, users, normalized_page, limit

    def bulk_update_company_permissions(
        self,
        company_id: str,
        updates: List[Dict[str, Any]],
        *,
        fallback_to_template: bool = False,
    ) -> List[Tuple[UserModel, Optional[dict]]]:
        results: List[Tuple[UserModel, Optional[dict]]] = []
        for item in updates:
            user_id = item.get("user_id")
            if not user_id:
                raise ValueError("user_id is required in bulk payload")

            target_user = self.users.get_user_by_id(user_id)
            if not target_user:
                raise ValueError(f"user {user_id} not found")
            if target_user.company_id and target_user.company_id != company_id:
                raise ValueError(
                    f"user {user_id} does not belong to company {company_id}"
                )

            role = item.get("role")
            permissions = item.get("permissions")
            use_template = bool(item.get("use_template"))
            if permissions is None and fallback_to_template:
                use_template = True

            updated = self.update_user_permissions(
                user_id,
                role=role,
                explicit_permissions=permissions,
                use_template=use_template,
            )
            if updated:
                results.append(updated)
        return results


customer_permissions_service = CustomerPermissionsService()
