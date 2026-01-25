import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from open_webui.routers import hsai_ugc  # noqa: E402
from open_webui.models.hsai_ugc import TaskSceneData, VideoTaskData  # noqa: E402
from open_webui.utils.auth import get_verified_user  # noqa: E402


def _build_app(*, user_id: str) -> FastAPI:
    app = FastAPI()
    app.include_router(hsai_ugc.router, prefix="/api/v1")
    app.dependency_overrides[get_verified_user] = lambda: SimpleNamespace(id=user_id)
    return app


def _task(*, task_id: str, user_id: str, status: int, step: int, base_inputs=None) -> VideoTaskData:
    return VideoTaskData(
        id=task_id,
        user_id=user_id,
        status=status,
        step=step,
        model_id=1,
        base_inputs=base_inputs or {"product_url": "", "product_name": "", "language": "zh"},
        result_video_url=None,
        progress_percent=0,
        last_progress_at=None,
        closed_at=None,
        closed_reason=None,
        created_at=0,
        updated_at=0,
    )


def _scene(*, scene_id: int, task_id: str, scene_index: int, fragment_video_url: Optional[str]) -> TaskSceneData:
    return TaskSceneData(
        id=scene_id,
        task_id=task_id,
        scene_index=scene_index,
        subtitle=f"s{scene_index}",
        script_desc=f"d{scene_index}",
        reference_img_url=f"img{scene_index}",
        fragment_video_url=fragment_video_url,
        fragment_video_urls=None,
        image_prompt=None,
    )


def test_retry_step3_sends_hs004_shot_list(monkeypatch):
    client = TestClient(_build_app(user_id="user-1"))

    monkeypatch.setattr(hsai_ugc, "_require_env", lambda name: "k")
    monkeypatch.setattr(hsai_ugc, "_get_sharded_api_key", lambda idx: "k")
    monkeypatch.setattr(hsai_ugc, "_resolve_minimax_credentials", lambda *a, **k: {"api_key": "m", "group_id": "g"})

    monkeypatch.setattr(
        hsai_ugc.VideoTasks,
        "get_task_by_id",
        lambda task_id: _task(task_id=task_id, user_id="user-1", status=-1, step=3),
    )
    monkeypatch.setattr(
        hsai_ugc.MaterialModels,
        "get_model_by_id_and_user_id",
        lambda model_id, user_id: type("M", (), {"id": model_id, "user_id": user_id, "voice_provider_id": "voice-1"})(),
    )
    monkeypatch.setattr(
        hsai_ugc.TaskScenes,
        "get_scenes_by_task_id",
        lambda task_id: [
            _scene(scene_id=1, task_id=task_id, scene_index=0, fragment_video_url="v0"),
            _scene(scene_id=2, task_id=task_id, scene_index=1, fragment_video_url="v1"),
        ],
    )

    calls = {"post_json": 0, "payload": None}

    async def ok_post_json(url, payload):
        calls["post_json"] += 1
        calls["payload"] = payload
        assert url == hsai_ugc.URL_HS004
        assert payload["task_id"] == "task-1"
        assert "shot_list" in payload
        assert payload["shot_list"] == [{"shot_id": 0, "shot_video_url": "v0"}, {"shot_id": 1, "shot_video_url": "v1"}]
        assert "shot_video_list" not in payload
        return 200, {}, ""

    monkeypatch.setattr(hsai_ugc, "post_json", ok_post_json)
    monkeypatch.setattr(hsai_ugc.VideoTasks, "update_task_status", lambda *a, **k: None)

    resp = client.post("/api/v1/ugc/tasks/task-1/retry")
    assert resp.status_code == 200
    assert calls["post_json"] == 1


def test_retry_step3_maps_n8n_5xx_to_502(monkeypatch):
    client = TestClient(_build_app(user_id="user-1"))

    monkeypatch.setattr(hsai_ugc, "_require_env", lambda name: "k")
    monkeypatch.setattr(hsai_ugc, "_get_sharded_api_key", lambda idx: "k")
    monkeypatch.setattr(hsai_ugc, "_resolve_minimax_credentials", lambda *a, **k: {"api_key": "m", "group_id": "g"})

    monkeypatch.setattr(
        hsai_ugc.VideoTasks,
        "get_task_by_id",
        lambda task_id: _task(task_id=task_id, user_id="user-1", status=-1, step=3),
    )
    monkeypatch.setattr(
        hsai_ugc.MaterialModels,
        "get_model_by_id_and_user_id",
        lambda model_id, user_id: type("M", (), {"id": model_id, "user_id": user_id, "voice_provider_id": "voice-1"})(),
    )
    monkeypatch.setattr(
        hsai_ugc.TaskScenes,
        "get_scenes_by_task_id",
        lambda task_id: [_scene(scene_id=1, task_id=task_id, scene_index=0, fragment_video_url="v0")],
    )

    async def boom_post_json(url, payload):
        raise Exception('HTTP 500: {"error":"shot_list must be a non-empty array"}')

    monkeypatch.setattr(hsai_ugc, "post_json", boom_post_json)

    status_updates = []
    monkeypatch.setattr(
        hsai_ugc.VideoTasks,
        "update_task_status",
        lambda task_id, status, step=None, result_url=None: status_updates.append(status),
    )

    resp = client.post("/api/v1/ugc/tasks/task-1/retry")
    assert resp.status_code == 502
    # Ensure we mark failed
    assert -1 in status_updates


def test_retry_step2_sends_hs003_shot_list(monkeypatch):
    client = TestClient(_build_app(user_id="user-1"))

    monkeypatch.setattr(hsai_ugc, "_require_env", lambda name: "k")
    monkeypatch.setattr(hsai_ugc, "_get_sharded_api_key", lambda idx: "k")
    monkeypatch.setattr(hsai_ugc, "_resolve_minimax_credentials", lambda *a, **k: {"api_key": "m", "group_id": "g"})

    monkeypatch.setattr(
        hsai_ugc.VideoTasks,
        "get_task_by_id",
        lambda task_id: _task(task_id=task_id, user_id="user-1", status=-1, step=2, base_inputs={"hs003_scene_index_list": [0, 1]}),
    )
    monkeypatch.setattr(
        hsai_ugc.MaterialModels,
        "get_model_by_id_and_user_id",
        lambda model_id, user_id: type("M", (), {"id": model_id, "user_id": user_id, "voice_provider_id": "voice-1"})(),
    )
    monkeypatch.setattr(
        hsai_ugc.TaskScenes,
        "get_scenes_by_task_id",
        lambda task_id: [
            _scene(scene_id=1, task_id=task_id, scene_index=0, fragment_video_url=None),
            _scene(scene_id=2, task_id=task_id, scene_index=1, fragment_video_url=None),
        ],
    )

    calls = {"post_json": 0}

    async def ok_post_json(url, payload):
        calls["post_json"] += 1
        assert url == hsai_ugc.URL_HS003
        assert payload["task_id"] == "task-1"
        assert payload["voice_id"] == "voice-1"
        assert isinstance(payload.get("shot_list"), list) and len(payload["shot_list"]) == 2
        assert payload["shot_list"][0]["shot_id"] == 0
        return 200, {}, ""

    monkeypatch.setattr(hsai_ugc, "post_json", ok_post_json)

    status_updates = []
    monkeypatch.setattr(
        hsai_ugc.VideoTasks,
        "update_task_status",
        lambda task_id, status, step=None, result_url=None: status_updates.append((status, step)),
    )
    monkeypatch.setattr(hsai_ugc.VideoTasks, "patch_base_inputs", lambda *a, **k: None)

    resp = client.post("/api/v1/ugc/tasks/task-1/retry")
    assert resp.status_code == 200
    assert calls["post_json"] == 1
    assert (3, 2) in status_updates


def test_retry_step1_includes_product_img(monkeypatch):
    client = TestClient(_build_app(user_id="user-1"))

    monkeypatch.setattr(hsai_ugc, "_require_env", lambda name: "k")
    monkeypatch.setattr(hsai_ugc, "_get_sharded_api_key", lambda idx: "k")
    monkeypatch.setattr(hsai_ugc, "_resolve_minimax_credentials", lambda *a, **k: {"api_key": "m", "group_id": "g"})

    monkeypatch.setattr(
        hsai_ugc.VideoTasks,
        "get_task_by_id",
        lambda task_id: _task(
            task_id=task_id,
            user_id="user-1",
            status=-1,
            step=1,
            base_inputs={"product_url": "u", "product_img": "img", "product_name": "p", "language": "zh"},
        ),
    )
    monkeypatch.setattr(
        hsai_ugc.MaterialModels,
        "get_model_by_id_and_user_id",
        lambda model_id, user_id: type(
            "M", (), {"id": model_id, "user_id": user_id, "model_name": "n", "model_img_url": "mimg", "voice_provider_id": "voice-1"}
        )(),
    )

    calls = {"post_json": 0}

    async def ok_post_json(url, payload):
        calls["post_json"] += 1
        assert url == hsai_ugc.URL_HS002
        assert payload["product_url"] == "u"
        assert payload["product_img"] == "img"
        return 200, {}, ""

    monkeypatch.setattr(hsai_ugc, "post_json", ok_post_json)
    monkeypatch.setattr(hsai_ugc.VideoTasks, "update_task_status", lambda *a, **k: None)

    resp = client.post("/api/v1/ugc/tasks/task-1/retry")
    assert resp.status_code == 200
    assert calls["post_json"] == 1
