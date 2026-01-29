"""
UGC 视频生成任务 Watchdog（按设计文档 V3.2）

- 每 5 分钟扫描一次处理中任务（默认 status=1/3/5，可配置）
- 若 last_progress_at（回退到 updated_at）距离当前时间超过阈值（默认 60 分钟），则自动关闭（status=-2）
"""

import asyncio
import logging
import os
from typing import Optional

from open_webui.models.hsai_ugc import VideoTasks, TaskScenes, MaterialModels
from open_webui.services.workflow_meta_update_service import post_json
from open_webui.routers.hsai_ugc import URL_HS003_SHOT_VIDEO, _get_sharded_api_key, _require_env, _resolve_minimax_credentials

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
        timeout_minutes = int(os.getenv("UGC_TASK_STALE_TIMEOUT_MINUTES", os.getenv("UGC_WATCHDOG_TIMEOUT_MINUTES", "60")))
        pending_merge_timeout_minutes = int(os.getenv("UGC_TASK_PENDING_MERGE_TIMEOUT_MINUTES", str(3 * 24 * 60)))

        statuses_raw = os.getenv("UGC_TASK_STALE_STATUSES", "1,3,5").strip()
        statuses = []
        for part in statuses_raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                statuses.append(int(part))
            except ValueError:
                continue

        interval_seconds = max(interval_minutes, 1) * 60

        while self.is_running:
            try:
                # Phase 3: Auto-Retry for Stale Rendering Tasks (status=3)
                # Before we close stale tasks, we give them a chance to retry.
                retryable_timeout = max(int(timeout_minutes / 2), 5) # Retry sooner than close
                
                try:
                    stale_rendering_tasks = VideoTasks.get_stale_retryable_tasks(timeout_minutes=retryable_timeout)
                    for task in stale_rendering_tasks:
                        log.info(f"Watchdog: Checking stale task {task.id} (status={task.status}) for retry...")
                        
                        # Identify missing scenes
                        scenes = TaskScenes.get_scenes_by_task_id(task.id)
                        missing_scenes = [s for s in scenes if not s.fragment_video_url]
                        
                        if not missing_scenes:
                            continue # Weird, status=3 but all done? Handler should have advanced it.
                            
                        # Trigger retries
                        retry_triggered = False
                        
                        # Load context
                        # Optim: we are in a loop, avoid resolving per scene if possible, but keep it simple first
                        try:
                            model_ctx = MaterialModels.get_model_by_id_and_user_id(int(task.model_id), task.user_id)
                            if not model_ctx: continue
                            
                            minimax_creds = _resolve_minimax_credentials(
                                getattr(model_ctx, "minimax_account_id", None),
                                require_group=True,
                                allow_env_fallback=True,
                            )
                            run_hub_key = _require_env("RUNNINGHUB_API_KEY")
                            run_hub_wid = _require_env("RUNNINGHUB_WORKFLOW_ID")
                            jarvis_key = _get_sharded_api_key(1)
                            
                            for s in missing_scenes:
                                current_retries = int(s.retry_count or 0) # Schema updated
                                if current_retries < 3: # Max retries
                                    log.info(f"Watchdog: Triggering auto-retry for task {task.id} scene {s.scene_index}")
                                    TaskScenes.increment_retry_count(task.id, s.scene_index, error_msg="Watchdog auto-retry")
                                    
                                    payload = {
                                        "task_id": task.id,
                                        "shot_id": s.scene_index,
                                        "shot_script": s.script_desc or "",
                                        "shot_script_img": s.reference_img_url or "",
                                        "subtitle": s.subtitle or "",
                                        "jarvis_api_key": jarvis_key,
                                        "minimax_key": minimax_creds["api_key"],
                                        "minimax_group": minimax_creds["group_id"],
                                        "runninghub_api_key": run_hub_key,
                                        "runninghub_workflow_id": run_hub_wid,
                                    }
                                    await post_json(URL_HS003_SHOT_VIDEO, payload)
                                    retry_triggered = True
                        
                        except Exception as e:
                            log.error(f"Watchdog: Failed to retry task {task.id}: {e}")
                        
                        if retry_triggered:
                            # Bump last_progress_at so we don't retry immediately or close it
                            VideoTasks.update_task_status(task.id, status=3)
                            
                except Exception as e:
                    # Use stack traces to surface the first failing SQL/exception in nested calls.
                    log.error("Watchdog: Error in retry loop: %s", e, exc_info=True)

                # Close tasks whose free-retry window has expired.
                try:
                    expired = VideoTasks.close_expired_free_retry_tasks()
                    if expired:
                        log.warning(
                            "UGC watchdog closed %s tasks due to free-retry window expired",
                            expired,
                        )
                except Exception as e:
                    log.error("Watchdog: Error when closing free-retry expired tasks: %s", e, exc_info=True)

                # ... Proceed to Cleanup Logic ...
                # status=4（PENDING_MERGE）需要更长的保留期：默认 3 天，
                # 避免用户离开页面后无法返回确认合成。
                statuses_no_pending_merge = [s for s in statuses if s != 4]

                marked = VideoTasks.mark_stale_tasks_closed(
                    timeout_minutes=timeout_minutes,
                    statuses=statuses_no_pending_merge or None,
                )
                if marked:
                    log.warning(
                        "UGC watchdog closed %s stale tasks (timeout=%s minutes)",
                        marked,
                        timeout_minutes,
                    )

                marked_pending_merge = VideoTasks.mark_stale_tasks_closed(
                    timeout_minutes=pending_merge_timeout_minutes,
                    statuses=[4],
                )
                if marked_pending_merge:
                    log.warning(
                        "UGC watchdog closed %s pending-merge tasks (timeout=%s minutes)",
                        marked_pending_merge,
                        pending_merge_timeout_minutes,
                    )

                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                log.error("UGC watchdog loop error: %s", exc, exc_info=True)
                await asyncio.sleep(60)
