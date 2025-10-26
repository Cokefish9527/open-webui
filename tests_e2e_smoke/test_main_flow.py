import os
from dataclasses import dataclass, field
from typing import List
import pytest


pytestmark = pytest.mark.e2e_smoke


def _enabled() -> bool:
    return os.getenv("E2E_SMOKE", "1") == "1"


@dataclass
class VideoTask:
    company: str
    account: str
    materials: List[str] = field(default_factory=list)
    script: str = ""
    audio_tts: str = ""
    status: str = "created"  # created -> collected -> bound -> composed -> published


def collect_info(task: VideoTask) -> VideoTask:
    task.status = "collected"
    return task


def submit_materials(task: VideoTask) -> VideoTask:
    assert task.status == "collected"
    task.materials = ["img001.png", "bgm001.mp3"]
    return task


def bind_account(task: VideoTask) -> VideoTask:
    assert task.materials
    task.status = "bound"
    return task


def compose_video(task: VideoTask) -> VideoTask:
    assert task.status == "bound"
    task.script = "auto-generated script"
    task.audio_tts = "tts-bytes"
    task.status = "composed"
    return task


def publish_video(task: VideoTask) -> VideoTask:
    assert task.status == "composed"
    # 这里不做外部调用，仅模拟成功发布
    task.status = "published"
    return task


def test_e2e_main_flow_simulated():
    if not _enabled():
        pytest.skip("E2E_SMOKE disabled; skipping")

    task = VideoTask(company="acme", account="tiktok-demo")
    task = collect_info(task)
    task = submit_materials(task)
    task = bind_account(task)
    task = compose_video(task)
    task = publish_video(task)

    assert task.status == "published"
    assert task.script and task.audio_tts

