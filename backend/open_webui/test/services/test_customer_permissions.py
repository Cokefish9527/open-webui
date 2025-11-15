from typing import Dict, List

import pytest

from open_webui.models.users import UserModel, UserListResponse
from open_webui.models.hsai_companies import CompanyModel
from open_webui.services import customer_permissions as cp


def _seed_user(**overrides):
    base = {
        "id": overrides.get("id", "user-1"),
        "name": overrides.get("name", "测试用户"),
        "email": overrides.get("email", "user@example.com"),
        "role": overrides.get("role", "pending"),
        "profile_image_url": "/user.png",
        "last_active_at": 0,
        "updated_at": 0,
        "created_at": 0,
        "api_key": None,
        "settings": overrides.get("settings", {}),
        "info": None,
        "info_collection_completed": False,
        "business_name": overrides.get("business_name"),
        "company_id": overrides.get("company_id"),
        "is_super_admin": False,
        "oauth_sub": None,
    }
    return dict(base)


class FakeUsersRepo:
    def __init__(self, users: List[Dict]):
        self._store = {user["id"]: dict(user) for user in users}

    def _as_model(self, payload: Dict) -> UserModel:
        return UserModel(**payload)

    def get_user_by_id(self, user_id: str):
        payload = self._store.get(user_id)
        return self._as_model(payload) if payload else None

    def update_user_role_by_id(self, user_id: str, role: str):
        if user_id in self._store:
            self._store[user_id]["role"] = role
            return self.get_user_by_id(user_id)
        return None

    def update_user_settings_by_id(self, user_id: str, updated: dict):
        if user_id not in self._store:
            return None
        settings = self._store[user_id].setdefault("settings", {})
        settings.update(updated)
        return self.get_user_by_id(user_id)

    def get_users(self, skip=None, limit=None, company_id=None):
        filtered = [
            self._as_model(payload)
            for payload in self._store.values()
            if company_id is None or payload.get("company_id") == company_id
        ]
        start = skip or 0
        end = start + limit if limit else None
        return UserListResponse(users=filtered[start:end], total=len(filtered))


class FakeCompaniesRepo:
    def __init__(self):
        self._store = {
            "co-1": CompanyModel(
                id="co-1",
                name="示例企业",
                description=None,
                owner_user_id="owner-1",
                company_info=None,
                status="active",
                config=None,
                created_at=0,
                updated_at=0,
            )
        }

    def get_company_by_id(self, company_id: str):
        return self._store.get(company_id)


def test_get_user_permissions_returns_data():
    users = FakeUsersRepo(
        [
            _seed_user(
                id="u-1",
                role="user",
                settings={"permissions": {"chat": {"controls": True}}},
                company_id="co-1",
            )
        ]
    )
    service = cp.CustomerPermissionsService(users_repository=users, companies_repository=FakeCompaniesRepo())
    user, perms = service.get_user_permissions("u-1")
    assert user.role == "user"
    assert perms == {"chat": {"controls": True}}


def test_update_user_permissions_applies_template(monkeypatch):
    users = FakeUsersRepo([_seed_user(id="u-2", role="pending", company_id="co-1")])
    service = cp.CustomerPermissionsService(users_repository=users, companies_repository=FakeCompaniesRepo())

    dummy_template = {"chat": {"controls": False}}
    monkeypatch.setattr(cp, "CUSTOMER_PERMISSION_TEMPLATE", type("Cfg", (), {"value": dummy_template}))

    user, perms = service.update_user_permissions("u-2", role="user", use_template=True)
    assert user.role == "user"
    assert perms == dummy_template


def test_list_company_permissions_respects_pagination():
    user_payloads = [
        _seed_user(id=f"user-{i}", company_id="co-1", role="user")
        for i in range(1, 6)
    ]
    users = FakeUsersRepo(user_payloads)
    service = cp.CustomerPermissionsService(users_repository=users, companies_repository=FakeCompaniesRepo())

    company, response, page, size = service.list_company_permissions("co-1", page=2, page_size=2)
    assert company.name == "示例企业"
    assert page == 2
    assert size == 2
    assert len(response.users) == 2
    assert response.total == 5
