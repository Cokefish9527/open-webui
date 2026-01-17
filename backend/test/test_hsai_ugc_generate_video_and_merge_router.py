import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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


def _task(*, task_id: str, user_id: str, status: int) -> VideoTaskData:
    return VideoTaskData(
        id=task_id,
        user_id=user_id,
        status=status,
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


def _scene(*, scene_id: int, task_id: str, scene_index: int) -> TaskSceneData:
    return TaskSceneData(
        id=scene_id,
        task_id=task_id,
        scene_index=scene_index,
        subtitle=f"s{scene_index}",
        script_desc=f"d{scene_index}",
        reference_img_url=f"img{scene_index}",
        fragment_video_url=None,
        fragment_video_urls=None,
    )


def test_generate_video_triggers_hs003_and_returns_scenes(monkeypatch):
    client = TestClient(_build_app(user_id="user-1"))

    monkeypatch.setattr(hsai_ugc, "_require_env", lambda name: "k")
    monkeypatch.setattr(hsai_ugc.VideoTasks, "get_task_by_id", lambda task_id: _task(task_id=task_id, user_id="user-1", status=2))
    monkeypatch.setattr(
        hsai_ugc.MaterialModels,
        "get_model_by_id_and_user_id",
        lambda model_id, user_id: type("M", (), {"id": model_id, "user_id": user_id, "voice_provider_id": "voice-1"})(),
    )

    # Mutable scene store to simulate updates.
    store = {0: _scene(scene_id=1, task_id="task-1", scene_index=0), 1: _scene(scene_id=2, task_id="task-1", scene_index=1)}

    def fake_get_scenes(task_id: str):
        return [store[0], store[1]]

    def fake_update_scene(scene_id: int, form):
        # Find by id and apply updates.
        for idx, s in store.items():
            if s.id == scene_id:
                data = form.model_dump(exclude_unset=True)
                store[idx] = TaskSceneData(**{**s.model_dump(), **data})
                return True
        return False

    monkeypatch.setattr(hsai_ugc.TaskScenes, "get_scenes_by_task_id", fake_get_scenes)
    monkeypatch.setattr(hsai_ugc.TaskScenes, "update_scene", fake_update_scene)

    calls = {"post_json": 0, "status_updates": []}

    async def ok_post_json(url, payload):
        calls["post_json"] += 1
        assert url == hsai_ugc.URL_HS003
        assert payload["task_id"] == "task-1"
        assert payload["voice_id"] == "voice-1"
        return 200, {}, ""

    monkeypatch.setattr(hsai_ugc, "post_json", ok_post_json)
    monkeypatch.setattr(
        hsai_ugc.VideoTasks,
        "update_task_status",
        lambda task_id, status, step=None, result_url=None: calls["status_updates"].append((status, step)),
    )

    resp = client.post(
        "/api/v1/ugc/tasks/task-1/generate_video",
        json=[
            {"scene_index": 0, "subtitle": "s0-new", "script_desc": "d0-new", "reference_img_url": "img0-new"},
            {"scene_index": 1, "subtitle": "s1-new", "script_desc": "d1-new", "reference_img_url": "img1-new"},
        ],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 2
    assert data[0]["subtitle"] == "s0-new"
    assert (3, 2) in calls["status_updates"]
    assert calls["post_json"] == 1


def test_merge_uses_selections_and_triggers_hs004(monkeypatch):
    client = TestClient(_build_app(user_id="user-1"))

    monkeypatch.setattr(hsai_ugc, "_require_env", lambda name: "k")
    monkeypatch.setattr(hsai_ugc.VideoTasks, "get_task_by_id", lambda task_id: _task(task_id=task_id, user_id="user-1", status=4))

    scenes = [
        TaskSceneData(
            id=1,
            task_id="task-1",
            scene_index=0,
            subtitle="s0",
            script_desc="d0",
            reference_img_url="img0",
            fragment_video_url="v0a",
            fragment_video_urls=["v0a", "v0b"],
        ),
        TaskSceneData(
            id=2,
            task_id="task-1",
            scene_index=1,
            subtitle="s1",
            script_desc="d1",
            reference_img_url="img1",
            fragment_video_url="v1a",
            fragment_video_urls=["v1a", "v1b"],
        ),
    ]
    monkeypatch.setattr(hsai_ugc.TaskScenes, "get_scenes_by_task_id", lambda task_id: scenes)

    selected_updates = []
    monkeypatch.setattr(
        hsai_ugc.TaskScenes,
        "update_fragment_video_url",
        lambda task_id, scene_index, video_url: selected_updates.append((scene_index, video_url)) or True,
    )

    calls = {"post_json": 0, "status_updates": []}

    async def ok_post_json(url, payload):
        calls["post_json"] += 1
        assert url == hsai_ugc.URL_HS004
        assert payload["shot_video_list"] == ["v0b", "v1a"]
        return 200, {}, ""

    monkeypatch.setattr(hsai_ugc, "post_json", ok_post_json)
    monkeypatch.setattr(
        hsai_ugc.VideoTasks,
        "update_task_status",
        lambda task_id, status, step=None, result_url=None: calls["status_updates"].append((status, step)),
    )

    resp = client.post(
        "/api/v1/ugc/tasks/task-1/merge",
        json={"selections": [{"scene_index": 0, "video_url": "v0b"}]},
    )
    assert resp.status_code == 200
    assert (5, 3) in calls["status_updates"]
    assert calls["post_json"] == 1
    assert (0, "v0b") in selected_updates
