import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.hsai_tasks import (
    HSAITasks,
    HSAITaskForm,
    HSAITaskUpdateForm,
    HSAITaskModel,
    HSAITaskStateLogs,
    HSAIRecurringState,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


def _resolve_interval_seconds(task: HSAITaskModel) -> int:
    meta: Dict[str, float] = task.recurring_meta or {}
    if "interval_seconds" in meta:
        try:
            interval = int(meta["interval_seconds"])
            return max(interval, 300)
        except (ValueError, TypeError):
            pass
    if "interval_hours" in meta:
        try:
            interval = int(float(meta["interval_hours"]) * 3600)
            return max(interval, 300)
        except (ValueError, TypeError):
            pass
    return 24 * 3600


def _format_schedule_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


class RecurringTaskScheduler:
    """循环任务调度器"""

    def __init__(self, interval_seconds: int = 60, batch_size: int = 50):
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        log.info("Recurring task scheduler started")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("Recurring task scheduler stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._dispatch_batch()
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Recurring scheduler loop error: %s", exc, exc_info=True)
            await asyncio.sleep(self.interval_seconds)

    async def _dispatch_batch(self) -> None:
        tasks = HSAITasks.list_active_recurring_tasks(limit=self.batch_size)
        now_ts = int(time.time())
        for task in tasks:
            if task.next_run_at and task.next_run_at > now_ts:
                continue
            await self._handle_task(task, now_ts)

    async def _handle_task(self, task: HSAITaskModel, reference_ts: int) -> None:
        interval_seconds = _resolve_interval_seconds(task)
        next_run_at = reference_ts + interval_seconds

        scheduled_key = _format_schedule_date(reference_ts)
        existing_subtasks = HSAITasks.get_tasks_by_user_id(
            user_id=task.user_id,
            project_id=task.project_id,
            limit=200,
        )

        for sub in existing_subtasks:
            if (
                sub.parent_task_id == task.id
                and (sub.config or {}).get("scheduled_for") == scheduled_key
            ):
                # 已存在同日子任务，只更新 parent 的下一次调度
                HSAITasks.update_task_by_id(
                    task.id,
                    HSAITaskUpdateForm(
                        last_run_at=reference_ts,
                        next_run_at=next_run_at,
                    ),
                )
                return

        subtask_form = HSAITaskForm(
            title=f"{scheduled_key} 循环任务执行",
            description="由系统调度自动生成的循环任务子任务。",
            task_type=task.task_type or "workflow_execution",
            task_category="recurring_subtask",
            project_id=task.project_id,
            parent_task_id=task.id,
            priority=max((task.priority or 0) - 10, 0),
            config={
                "scheduled_for": scheduled_key,
                "generated_by": "recurring_scheduler",
            },
        )

        created_subtask = HSAITasks.insert_new_task(task.user_id, subtask_form)
        if created_subtask:
            log.info(
                "Generated recurring subtask task_id=%s parent=%s schedule=%s",
                created_subtask.id,
                task.id,
                scheduled_key,
            )

        HSAITasks.update_task_by_id(
            task.id,
            HSAITaskUpdateForm(
                last_run_at=reference_ts,
                next_run_at=next_run_at,
            ),
        )

        try:
            HSAITaskStateLogs.append_log(
                task_id=task.id,
                from_state=task.recurring_state,
                to_state=task.recurring_state or HSAIRecurringState.ACTIVE.value,
                operator_id=None,
                operator_name=None,
                source="recurring_scheduler",
                message=f"自动生成子任务 {created_subtask.id if created_subtask else 'N/A'}",
                snapshot_json={
                    "last_run_at": reference_ts,
                    "next_run_at": next_run_at,
                    "scheduled_for": scheduled_key,
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            log.warning("Failed to append state log for recurring task %s: %s", task.id, exc)


recurring_task_scheduler = RecurringTaskScheduler()
