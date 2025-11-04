import asyncio
import logging
from typing import Awaitable, Callable, Dict, Optional

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.hsai_outbox import (
    HSAIOutboxEvents,
    HSAIOutboxEventModel,
    OutboxEventStatus,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

OutboxHandler = Callable[[HSAIOutboxEventModel], Awaitable[None]]
_HANDLERS: Dict[str, OutboxHandler] = {}


def register_outbox_handler(event_type: str, handler: OutboxHandler) -> None:
    """注册 Outbox 事件处理器"""
    _HANDLERS[event_type] = handler


class OutboxDispatcher:
    """简单的 Outbox 分发器"""

    def __init__(self, interval_seconds: int = 5, batch_size: int = 50):
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        log.info("Outbox dispatcher started")

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
        log.info("Outbox dispatcher stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._process_batch()
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Outbox dispatcher loop error: %s", exc, exc_info=True)
            await asyncio.sleep(self.interval_seconds)

    async def _process_batch(self) -> None:
        events = HSAIOutboxEvents.acquire_pending(batch_size=self.batch_size)
        if not events:
            return

        for event in events:
            await self._dispatch_event(event)

    async def _dispatch_event(self, event: HSAIOutboxEventModel) -> None:
        handler = _HANDLERS.get(event.event_type)
        if not handler:
            log.warning("No handler registered for event_type=%s; marking dispatched", event.event_type)
            HSAIOutboxEvents.mark_dispatched(event.id)
            return

        try:
            await handler(event)
        except Exception as exc:  # pylint: disable=broad-except
            log.error(
                "Outbox event %s handling failed: %s",
                event.id,
                exc,
                exc_info=True,
            )
            HSAIOutboxEvents.reschedule(event.id, delay_seconds=30, error_message=str(exc))
            return

        HSAIOutboxEvents.mark_dispatched(event.id)


outbox_dispatcher = OutboxDispatcher()

