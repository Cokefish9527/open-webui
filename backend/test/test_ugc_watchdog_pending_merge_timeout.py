import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_watchdog_uses_longer_timeout_for_pending_merge(monkeypatch):
    from open_webui.utils import ugc_watchdog_scheduler

    # Include 4 in the normal list to ensure scheduler removes it from the short-timeout pass.
    monkeypatch.setenv("UGC_TASK_STALE_STATUSES", "1,3,4,5")
    monkeypatch.setenv("UGC_TASK_STALE_TIMEOUT_MINUTES", "60")
    monkeypatch.delenv("UGC_TASK_PENDING_MERGE_TIMEOUT_MINUTES", raising=False)  # default 3 days

    calls = []

    def fake_mark_stale_tasks_closed(*, timeout_minutes: int, statuses=None):
        calls.append((timeout_minutes, list(statuses) if statuses is not None else None))
        return 0

    monkeypatch.setattr(ugc_watchdog_scheduler.VideoTasks, "mark_stale_tasks_closed", fake_mark_stale_tasks_closed)

    async def cancel_sleep(_):
        raise asyncio.CancelledError()

    monkeypatch.setattr(ugc_watchdog_scheduler.asyncio, "sleep", cancel_sleep)

    sched = ugc_watchdog_scheduler.UGCWatchdogScheduler()
    sched.is_running = True

    asyncio.run(sched._schedule_loop())

    # First pass: short timeout, statuses should NOT contain 4.
    assert calls[0][0] == 60
    assert calls[0][1] == [1, 3, 5]

    # Second pass: pending-merge timeout, only status=4.
    assert calls[1][0] == 3 * 24 * 60
    assert calls[1][1] == [4]
