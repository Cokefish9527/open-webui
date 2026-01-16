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
    # Override Depends(get_verified_user) without touching production auth implementation.
    app.dependency_overrides[get_verified_user] = lambda: SimpleNamespace(id=user_id)
    return app


def _sample_task(*, task_id: str, user_id: str) -> VideoTaskData:
    return VideoTaskData(
        id=task_id,
        user_id=user_id,
        status=1,
        step=1,
        model_id=1,
        base_inputs={"product_url": "", "product_name": "", "language": "zh"},
        result_video_url=None,
        progress_percent=0,
        last_progress_at=None,
        closed_at=None,
        closed_reason=None,
        created_at=0,
        updated_at=0,
    )


def test_get_task_detail_ok(monkeypatch):
    def fake_get_task_by_id(task_id: str):
        return _sample_task(task_id=task_id, user_id="user-1")

    monkeypatch.setattr(hsai_ugc.VideoTasks, "get_task_by_id", fake_get_task_by_id)

    client = TestClient(_build_app(user_id="user-1"))
    resp = client.get("/api/v1/ugc/tasks/task-1")
    assert resp.status_code == 200
    assert resp.json()["id"] == "task-1"


def test_get_task_detail_not_owner_returns_404(monkeypatch):
    monkeypatch.setattr(
        hsai_ugc.VideoTasks,
        "get_task_by_id",
        lambda task_id: _sample_task(task_id=task_id, user_id="user-1"),
    )

    client = TestClient(_build_app(user_id="user-2"))
    resp = client.get("/api/v1/ugc/tasks/task-1")
    assert resp.status_code == 404


def test_get_task_detail_not_found_returns_404(monkeypatch):
    monkeypatch.setattr(hsai_ugc.VideoTasks, "get_task_by_id", lambda task_id: None)

    client = TestClient(_build_app(user_id="user-1"))
    resp = client.get("/api/v1/ugc/tasks/task-404")
    assert resp.status_code == 404

