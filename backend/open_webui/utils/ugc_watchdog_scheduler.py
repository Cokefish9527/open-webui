"""
UGC 视频生成任务 Watchdog（按设计文档 V3.2）

- 每 5 分钟扫描一次处理中任务（status=1/3/5）
- 若 updated_at 距离当前时间超过 30 分钟，则强制标记为失败（status=-1）
"""

import asyncio
import logging
import os
from typing import Optional

from open_webui.models.hsai_ugc import VideoTasks

log = logging.getLogger(__name__)


class UGCWatchdogScheduler:
    def __init__(self):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        if self.is_running:
            return

        enabled = os.getenv("UGC_WATCHDOG_ENABLED", "true").lower() in ("1", "true", "yes", "on")
        if not enabled:
            log.info("UGC watchdog scheduler is disabled (UGC_WATCHDOG_ENABLED=false)")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._schedule_loop())
        log.info("UGC watchdog scheduler started")

    async def stop(self):
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        log.info("UGC watchdog scheduler stopped")

    async def _schedule_loop(self):
        interval_minutes = int(os.getenv("UGC_WATCHDOG_INTERVAL_MINUTES", "5"))
        timeout_minutes = int(os.getenv("UGC_WATCHDOG_TIMEOUT_MINUTES", "30"))

        interval_seconds = max(interval_minutes, 1) * 60

        while self.is_running:
            try:
                marked = VideoTasks.mark_stale_tasks_failed(timeout_minutes=timeout_minutes)
                if marked:
                    log.warning(
                        "UGC watchdog marked %s stale tasks as failed (timeout=%s minutes)",
                        marked,
                        timeout_minutes,
                    )
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                log.error("UGC watchdog loop error: %s", exc, exc_info=True)
                await asyncio.sleep(60)
