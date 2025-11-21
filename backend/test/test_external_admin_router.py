import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from open_webui.routers import external_admin  # noqa: E402
from open_webui.models.users import UserListResponse, UserModel  # noqa: E402


def _build_app():
    app = FastAPI()
    app.include_router(external_admin.router, prefix="")
    return app


@pytest.fixture()
def client(monkeypatch):
    def fake_verify(request):
        return "external-admin-test"

    monkeypatch.setattr(external_admin, "verify_external_request", fake_verify)
    return TestClient(_build_app())


def _sample_user():
    return UserModel(
        id="user-1",
        name="Test User",
        email="user@example.com",
        role="admin",
        profile_image_url="/avatar.png",
        last_active_at=0,
        updated_at=0,
        created_at=0,
        api_key=None,
        settings=None,
        info=None,
        info_collection_completed=False,
        business_name=None,
        company_id=None,
        is_super_admin=False,
        oauth_sub=None,
    )


def test_get_users_supports_filters(monkeypatch, client):
    captured = {}

    def fake_get_users(filter=None, skip=None, limit=None, company_id=None):
        captured["filter"] = filter
        captured["skip"] = skip
        captured["limit"] = limit
        captured["company_id"] = company_id
        return UserListResponse(users=[], total=0)

    monkeypatch.setattr(external_admin.Users, "get_users", fake_get_users)

    response = client.get(
        "/external/admin/users",
        params={
            "query": "foo",
            "order_by": "name",
            "direction": "asc",
            "company_id": "comp-1",
            "page": 2,
            "size": 5,
        },
    )
    assert response.status_code == 200
    assert captured["filter"] == {"query": "foo", "order_by": "name", "direction": "asc"}
    assert captured["skip"] == 5
    assert captured["limit"] == 5
    assert captured["company_id"] == "comp-1"


def test_get_users_with_user_id_returns_single(monkeypatch, client):
    sample = _sample_user()

    def fake_get_user_by_id(user_id):
        assert user_id == "user-1"
        return sample

    def fail_get_users(*args, **kwargs):
        raise AssertionError("get_users should not be called when user_id指定")

    monkeypatch.setattr(external_admin.Users, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(external_admin.Users, "get_users", fail_get_users)

    response = client.get("/external/admin/users", params={"user_id": "user-1"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["users"][0]["id"] == "user-1"


def test_get_user_detail_endpoint(monkeypatch, client):
    sample = _sample_user()
    monkeypatch.setattr(external_admin.Users, "get_user_by_id", lambda _: sample)

    response = client.get("/external/admin/users/user-1")
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
