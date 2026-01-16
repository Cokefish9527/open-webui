import asyncio
import logging
import random
from typing import Awaitable, Callable, Dict, Optional

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.hsai_outbox import (
    HSAIOutboxEvents,
    HSAIOutboxEventModel,
    OutboxEventStatus,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

# 告警服务
try:
    from open_webui.services.alert_service import send_alert_to_admin
    ALERT_SERVICE_AVAILABLE = True
except ImportError:
    ALERT_SERVICE_AVAILABLE = False

OutboxHandler = Callable[[HSAIOutboxEventModel], Awaitable[None]]
_HANDLERS: Dict[str, OutboxHandler] = {}


def _calc_backoff_seconds(
    attempt: int,
    *,
    base_seconds: float = 1.0,
    cap_seconds: float = 60.0,
    jitter_ratio: float = 0.1,
) -> float:
    attempt = max(int(attempt), 1)
    delay = min(float(cap_seconds), float(base_seconds) * (2 ** (attempt - 1)))
    if jitter_ratio and jitter_ratio > 0:
        delay = delay * (1 + random.uniform(-float(jitter_ratio), float(jitter_ratio)))
    return max(delay, 0.0)


def _format_loop_error(exc: Exception) -> str:
    if isinstance(exc, UnicodeDecodeError) and isinstance(getattr(exc, "object", None), (bytes, bytearray)):
        raw = bytes(exc.object)
        for enc in ("utf-8", "gbk", "cp936", "latin-1"):
            try:
                decoded = raw.decode(enc, errors="replace")
                return f"{exc} | decoded({enc})={decoded}"
            except Exception:
                continue
        return f"{exc} | raw={raw!r}"
    return str(exc)


def _is_db_decode_or_network_error(exc: Exception) -> bool:
    # 该类错误通常来自 DB 连接阶段（例如 DNS/网络异常导致 libpq 返回非 UTF-8 消息）
    if isinstance(exc, UnicodeDecodeError):
        return True
    msg = str(exc).lower()
    return "could not translate host name" in msg or "name or service not known" in msg


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
        error_attempt = 0
        while self._running:
            sleep_seconds = self.interval_seconds
            try:
                await self._process_batch()
                error_attempt = 0
            except Exception as exc:  # pylint: disable=broad-except
                error_attempt += 1
                sleep_seconds = max(sleep_seconds, _calc_backoff_seconds(error_attempt, base_seconds=1.0, cap_seconds=60.0))
                log.error("Outbox dispatcher loop error: %s", _format_loop_error(exc), exc_info=True)
                # 发送告警到后台
                # DB/网络不可用时优先降噪（避免重复告警刷屏），等待恢复后再继续。
                if ALERT_SERVICE_AVAILABLE and not _is_db_decode_or_network_error(exc):
                    try:
                        await send_alert_to_admin(
                            title="Outbox分发器错误",
                            content=f"Outbox分发器循环处理时发生错误: {str(exc)}",
                            level="ERROR",
                            source="outbox_dispatcher",
                            category="system_error"
                        )
                    except Exception as alert_exc:
                        log.error("发送告警失败: %s", alert_exc)
            await asyncio.sleep(sleep_seconds)

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
            # 发送告警到后台
            if ALERT_SERVICE_AVAILABLE:
                try:
                    await send_alert_to_admin(
                        title=f"Outbox事件处理失败: {event.event_type}",
                        content=f"处理Outbox事件 {event.id} 时发生错误: {str(exc)}\n事件载荷: {event.payload}",
                        level="ERROR",
                        source="outbox_dispatcher",
                        category="event_handling_error"
                    )
                except Exception as alert_exc:
                    log.error("发送告警失败: %s", alert_exc)
            return

        HSAIOutboxEvents.mark_dispatched(event.id)


outbox_dispatcher = OutboxDispatcher()
