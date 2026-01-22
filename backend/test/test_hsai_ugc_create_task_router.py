import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from open_webui.routers import hsai_ugc  # noqa: E402
from open_webui.models.hsai_ugc import VideoTaskData  # noqa: E402
from open_webui.utils.auth import get_verified_user  # noqa: E402


def _build_app(*, user_id: str) -> FastAPI:
    app = FastAPI()
    app.include_router(hsai_ugc.router, prefix="/api/v1")
    app.dependency_overrides[get_verified_user] = lambda: SimpleNamespace(id=user_id)
    return app


def _task_from_form(*, task_id: str, user_id: str, form) -> VideoTaskData:
    # Keep task payload minimal for router assertions.
    return VideoTaskData(
        id=task_id,
        user_id=user_id,
        status=1,
        step=1,
        model_id=form.model_id,
        base_inputs={
            "product_url": form.product_url,
            "product_name": form.product_name,
            "language": form.language,
            "product_country": getattr(form, "product_country", None) or "",
            "subtitle": getattr(form, "subtitle", None) or "",
            "shot_script": getattr(form, "shot_script", None) or "",
        },
        result_video_url=None,
        progress_percent=0,
        last_progress_at=None,
        closed_at=None,
        closed_reason=None,
        created_at=0,
        updated_at=0,
    )


def _mock_model(*, model_id: int, user_id: str):
    return type(
        "M",
        (),
        {
            "id": model_id,
            "user_id": user_id,
            "model_name": "m1",
            "model_img_url": "https://example.com/model.png",
            "voice_provider_id": "voice-1",
            "minimax_account_id": None,
        },
    )()


def test_create_task_product_id_fills_product_url_and_sends_both_fields(monkeypatch):
    client = TestClient(_build_app(user_id="user-1"))

    monkeypatch.setattr(hsai_ugc, "_require_env", lambda name: "k")
    monkeypatch.setattr(hsai_ugc, "_get_sharded_api_key", lambda idx: "jarvis-k")
    monkeypatch.setattr(hsai_ugc, "_resolve_minimax_credentials", lambda *_a, **_k: {"api_key": "mm-k", "group_id": "mm-g"})
    monkeypatch.setattr(hsai_ugc.MaterialModels, "get_model_by_id_and_user_id", lambda model_id, user_id: _mock_model(model_id=model_id, user_id=user_id))

    monkeypatch.setattr(
        hsai_ugc.Products,
        "get_product",
        lambda product_id: type("P", (), {"id": product_id, "user_id": "user-1", "name": "prod-1", "cover_img": "https://example.com/p.png"})(),
    )

    observed = {"form": None, "payload": None}

    def fake_create_task(user_id: str, form):
        observed["form"] = form
        return _task_from_form(task_id="task-1", user_id=user_id, form=form)

    async def ok_post_json(url, payload):
        observed["payload"] = payload
        return 200, {}, ""

    monkeypatch.setattr(hsai_ugc.VideoTasks, "create_task", fake_create_task)
    monkeypatch.setattr(hsai_ugc, "post_json", ok_post_json)

    resp = client.post("/api/v1/ugc/tasks", json={"model_id": 1, "product_id": 123, "language": "zh-CN"})
    assert resp.status_code == 200

    # Form should be patched for traceability (base_inputs).
    assert observed["form"].product_name == "prod-1"
    assert observed["form"].product_url == "https://example.com/p.png"

    # Payload should be compatible with both n8n old/new consumers.
    assert observed["payload"]["product_url"] == "https://example.com/p.png"
    assert observed["payload"]["product_img"] == "https://example.com/p.png"


def test_create_task_product_id_requires_cover_img(monkeypatch):
    client = TestClient(_build_app(user_id="user-1"))

    monkeypatch.setattr(hsai_ugc.MaterialModels, "get_model_by_id_and_user_id", lambda model_id, user_id: _mock_model(model_id=model_id, user_id=user_id))
    monkeypatch.setattr(hsai_ugc.Products, "get_product", lambda product_id: type("P", (), {"id": product_id, "user_id": "user-1", "name": "prod-1", "cover_img": ""})())

    resp = client.post("/api/v1/ugc/tasks", json={"model_id": 1, "product_id": 123, "language": "zh-CN"})
    assert resp.status_code == 400
    assert "cover image" in resp.text.lower()


def test_create_task_legacy_requires_product_url(monkeypatch):
    client = TestClient(_build_app(user_id="user-1"))

    monkeypatch.setattr(hsai_ugc.MaterialModels, "get_model_by_id_and_user_id", lambda model_id, user_id: _mock_model(model_id=model_id, user_id=user_id))
    resp = client.post("/api/v1/ugc/tasks", json={"model_id": 1, "product_name": "p1", "language": "zh-CN"})
    assert resp.status_code == 400
    assert "product_url" in resp.text


def test_create_task_marks_failed_and_returns_502_when_n8n_raises(monkeypatch):
    client = TestClient(_build_app(user_id="user-1"))

    monkeypatch.setattr(hsai_ugc, "_require_env", lambda name: "k")
    monkeypatch.setattr(hsai_ugc, "_get_sharded_api_key", lambda idx: "jarvis-k")
    monkeypatch.setattr(hsai_ugc, "_resolve_minimax_credentials", lambda *_a, **_k: {"api_key": "mm-k", "group_id": "mm-g"})
    monkeypatch.setattr(hsai_ugc.MaterialModels, "get_model_by_id_and_user_id", lambda model_id, user_id: _mock_model(model_id=model_id, user_id=user_id))

    monkeypatch.setattr(
        hsai_ugc.Products,
        "get_product",
        lambda product_id: type("P", (), {"id": product_id, "user_id": "user-1", "name": "prod-1", "cover_img": "https://example.com/p.png"})(),
    )

    def fake_create_task(user_id: str, form):
        return _task_from_form(task_id="task-1", user_id=user_id, form=form)

    updates = []
    monkeypatch.setattr(hsai_ugc.VideoTasks, "create_task", fake_create_task)
    monkeypatch.setattr(hsai_ugc.VideoTasks, "update_task_status", lambda task_id, status, step=None, result_url=None: updates.append((task_id, status, step)))

    async def boom_post_json(url, payload):
        raise Exception('HTTP 500: {"error":"product_url [line 55]"}')

    monkeypatch.setattr(hsai_ugc, "post_json", boom_post_json)

    resp = client.post("/api/v1/ugc/tasks", json={"model_id": 1, "product_id": 123, "language": "zh-CN"})
    assert resp.status_code == 502
    assert any(u[0] == "task-1" and u[1] == -1 for u in updates)

