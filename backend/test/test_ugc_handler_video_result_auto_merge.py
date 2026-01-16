import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_video_result_does_not_auto_merge_by_default(monkeypatch):
    """
    期望：默认不自动触发 hs004（合成），让前端有机会展示分镜视频并让用户确认。
    """
    from open_webui.utils import ugc_handler

    # Avoid socket side effects.
    monkeypatch.setattr(ugc_handler, "sio", None)
    monkeypatch.delenv("UGC_AUTO_MERGE_ENABLED", raising=False)

    # post_json should NOT be called when auto-merge is disabled by default.
    async def fail_post_json(*args, **kwargs):
        raise AssertionError("post_json should not be called when UGC_AUTO_MERGE_ENABLED is not set")

    monkeypatch.setattr(ugc_handler, "post_json", fail_post_json)

    # Stub DB access layer methods.
    updates = []

    monkeypatch.setattr(
        ugc_handler.VideoTasks,
        "get_task_by_id",
        lambda task_id: type("T", (), {"id": task_id, "status": 3})(),
    )
    monkeypatch.setattr(ugc_handler.TaskScenes, "get_scenes_by_task_id", lambda task_id: [object(), object()])
    monkeypatch.setattr(ugc_handler.TaskScenes, "update_fragment_video_url", lambda task_id, idx, url: None)
    monkeypatch.setattr(
        ugc_handler.VideoTasks,
        "update_task_status",
        lambda task_id, status, step=None, result_url=None: updates.append((status, step)),
    )

    msg = {
        "task_id": "task-1",
        "type": "VIDEO_RESULT",
        "data": {"shot_video_list": ["v1", "v2"]},
    }
    asyncio.run(ugc_handler.handle_ugc_callback(msg))

    assert (4, 2) in updates
    assert (5, 3) not in updates


def test_video_result_auto_merge_when_enabled(monkeypatch):
    """
    兼容：显式启用 UGC_AUTO_MERGE_ENABLED=true 时，仍会自动触发 hs004。
    """
    from open_webui.utils import ugc_handler

    monkeypatch.setattr(ugc_handler, "sio", None)
    monkeypatch.setenv("UGC_AUTO_MERGE_ENABLED", "true")
    monkeypatch.setenv("JARVIS_API_KEY", "k")

    calls = {"post_json": 0}

    async def ok_post_json(url, payload):
        calls["post_json"] += 1
        return 200, {}, ""

    monkeypatch.setattr(ugc_handler, "post_json", ok_post_json)

    updates = []
    monkeypatch.setattr(
        ugc_handler.VideoTasks,
        "get_task_by_id",
        lambda task_id: type("T", (), {"id": task_id, "status": 3})(),
    )
    monkeypatch.setattr(ugc_handler.TaskScenes, "get_scenes_by_task_id", lambda task_id: [object(), object()])
    monkeypatch.setattr(ugc_handler.TaskScenes, "update_fragment_video_url", lambda task_id, idx, url: None)
    monkeypatch.setattr(
        ugc_handler.VideoTasks,
        "update_task_status",
        lambda task_id, status, step=None, result_url=None: updates.append((status, step)),
    )

    msg = {
        "task_id": "task-1",
        "type": "VIDEO_RESULT",
        "data": {"shot_video_list": ["v1", "v2"]},
    }
    asyncio.run(ugc_handler.handle_ugc_callback(msg))

    assert calls["post_json"] == 1
    assert (4, 2) in updates
    assert (5, 3) in updates
