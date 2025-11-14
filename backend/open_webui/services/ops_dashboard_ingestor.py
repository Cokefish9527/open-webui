import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, Optional, Coroutine

from open_webui.env import (
    OPS_DASHBOARD_ALLOW_CONTENT,
    OPS_DASHBOARD_ENABLED,
    OPS_DASHBOARD_MAX_ATTEMPTS,
    OPS_DASHBOARD_QUEUE_MAXSIZE,
)
from open_webui.models.users import Users, UserModel
from open_webui.services.ops_dashboard_client import ops_dashboard_client

log = logging.getLogger(__name__)


class _ConversationEventDispatcher:
    def __init__(self) -> None:
        self._queue: Optional[asyncio.Queue[Optional[Dict[str, Any]]]] = None
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._lock = asyncio.Lock()
        self._running = False

    async def start(self) -> None:
        if not OPS_DASHBOARD_ENABLED:
            return
        async with self._lock:
            if self._running:
                return
            self._queue = asyncio.Queue(maxsize=OPS_DASHBOARD_QUEUE_MAXSIZE)
            self._running = True
            self._worker_task = asyncio.create_task(self._worker())
            log.info(
                "Ops dashboard dispatcher started (queue_max=%s)", OPS_DASHBOARD_QUEUE_MAXSIZE
            )

    async def stop(self, timeout: float = 5.0) -> None:
        task: Optional[asyncio.Task[None]] = None
        async with self._lock:
            if not self._running:
                return
            self._running = False
            queue = self._queue
            if queue is not None:
                try:
                    queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass
            task = self._worker_task
            self._worker_task = None
        if task:
            try:
                await asyncio.wait_for(task, timeout=timeout)
            except asyncio.TimeoutError:
                log.warning("Ops dashboard dispatcher stop timeout; cancelling worker")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        async with self._lock:
            self._queue = None
        await ops_dashboard_client.close()
        log.info("Ops dashboard dispatcher stopped")

    def enqueue(self, message: Dict[str, Any]) -> bool:
        queue = self._queue
        if not self._running or queue is None:
            return False
        try:
            queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            log.warning(
                "Ops dashboard dispatcher queue full (max=%s); dropped session_id=%s",
                OPS_DASHBOARD_QUEUE_MAXSIZE,
                message.get("session_id"),
            )
            return True

    async def _worker(self) -> None:
        queue = self._queue
        if queue is None:
            return
        try:
            while True:
                message = await queue.get()
                if message is None:
                    break
                try:
                    await self._process_message(message)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    log.error(
                        "Unexpected error while processing ops dashboard event: %s",
                        exc,
                        exc_info=True,
                    )
        except asyncio.CancelledError:
            log.info("Ops dashboard dispatcher worker cancelled")

    async def _process_message(self, message: Dict[str, Any]) -> None:
        attempt = 0
        delay = 0.5
        while True:
            attempt += 1
            try:
                success = await _record_conversation_event(message)
            except Exception as exc:  # pylint: disable=broad-except
                log.warning(
                    "Ops dashboard ingestion raised error attempt=%s: %s",
                    attempt,
                    exc,
                    exc_info=True,
                )
                success = False
            if success:
                return
            if attempt >= OPS_DASHBOARD_MAX_ATTEMPTS:
                log.error(
                    "Ops dashboard ingestion failed after %s attempts (session_id=%s); dropping event",
                    attempt,
                    message.get("session_id"),
                )
                return
            await asyncio.sleep(delay)
            delay = min(delay * 2, 5)


_conversation_dispatcher = _ConversationEventDispatcher()


async def start_conversation_ingestion() -> None:
    await _conversation_dispatcher.start()


async def stop_conversation_ingestion(timeout: float = 5.0) -> None:
    await _conversation_dispatcher.stop(timeout=timeout)


def _fire_and_forget(coro: Coroutine[Any, Any, Any]) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


def enqueue_conversation_event(message: Dict[str, Any]) -> None:
    if not OPS_DASHBOARD_ENABLED:
        return
    if _conversation_dispatcher.enqueue(message):
        return
    _fire_and_forget(_record_conversation_event(message))


def enqueue_user_activity_event(
    event_type: str,
    user_id: Optional[str],
    *,
    company_id: Optional[str] = None,
    count: int = 1,
    metadata: Optional[Dict[str, Any]] = None,
    stat_ts: Optional[float] = None,
) -> None:
    if not OPS_DASHBOARD_ENABLED:
        return
    _fire_and_forget(
        _record_user_activity_event(
            event_type=event_type,
            user_id=user_id,
            company_id=company_id,
            count=count,
            metadata=metadata,
            stat_ts=stat_ts,
        )
    )


def enqueue_system_metric(
    metric: str,
    value: float,
    *,
    dimension: Optional[Dict[str, Any]] = None,
    stat_hour_ts: Optional[float] = None,
) -> None:
    if not OPS_DASHBOARD_ENABLED:
        return
    _fire_and_forget(
        _record_system_metric(metric=metric, value=value, dimension=dimension, stat_hour_ts=stat_hour_ts)
    )


async def _record_conversation_event(message: Dict[str, Any]) -> bool:
    payload = _build_conversation_payload(message)
    if not payload:
        return False
    return await ops_dashboard_client.send_conversations(
        payload,
        idempotency_key=_build_idempotency_key("conv", payload),
    )


async def _record_user_activity_event(
    event_type: str,
    user_id: Optional[str],
    *,
    company_id: Optional[str] = None,
    count: int = 1,
    metadata: Optional[Dict[str, Any]] = None,
    stat_ts: Optional[float] = None,
) -> bool:
    if not user_id:
        return False
    payload = _build_user_activity_payload(
        event_type=event_type,
        user_id=user_id,
        company_id=company_id,
        count=count,
        metadata=metadata,
        stat_ts=stat_ts,
    )
    if not payload:
        return False
    return await ops_dashboard_client.send_user_activity(
        payload,
        idempotency_key=_build_idempotency_key("user-activity", payload),
    )


async def _record_system_metric(
    metric: str,
    value: float,
    *,
    dimension: Optional[Dict[str, Any]] = None,
    stat_hour_ts: Optional[float] = None,
) -> bool:
    payload = _build_system_metric_payload(metric, value, dimension=dimension, stat_hour_ts=stat_hour_ts)
    return await ops_dashboard_client.send_system_metrics(
        payload,
        idempotency_key=_build_idempotency_key("system-metric", payload),
    )


def _build_conversation_payload(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    session_id = str(message.get("session_id") or "").strip()
    if not session_id:
        return None

    user_id = message.get("user_id")
    user_snapshot = _resolve_user_snapshot(user_id)
    company_id = user_snapshot.company_id if user_snapshot else None

    started_ts = _first_value(
        message.get("started_at"),
        message.get("start_ts"),
        message.get("create_ts"),
        message.get("timestamp"),
    )
    ended_ts = _first_value(
        message.get("ended_at"),
        message.get("end_ts"),
        message.get("update_ts"),
        message.get("finish_ts"),
        started_ts,
    )

    turn_count = _coerce_int(
        message.get("turn_count")
        or message.get("data", {}).get("turnCount")
        or message.get("metadata", {}).get("turn_count")
    )
    duration_seconds = _coerce_int(
        message.get("duration_seconds")
        or message.get("duration")
        or _infer_duration_seconds(started_ts, ended_ts)
    )
    max_latency_ms = _coerce_int(
        message.get("max_latency_ms")
        or message.get("latency_ms")
        or message.get("data", {}).get("maxLatencyMs")
    )
    last_event_ts = _coerce_epoch_ms(message.get("last_event_ts") or message.get("update_ts") or time.time())

    payload: Dict[str, Any] = {
        "session_id": session_id,
        "user_id": user_id,
        "company_id": company_id,
        "channel": message.get("channel") or message.get("source") or "web",
        "started_at": _isoformat(started_ts),
        "ended_at": _isoformat(ended_ts),
        "duration_seconds": duration_seconds,
        "turn_count": turn_count,
        "is_bounced": _infer_bounced(turn_count, message.get("status")),
        "max_latency_ms": max_latency_ms,
        "status": message.get("status"),
        "content_type": message.get("content_type"),
        "tags": _sanitize_list(message.get("tags") or message.get("data", {}).get("tags")),
        "last_event_ts": last_event_ts,
    }

    if OPS_DASHBOARD_ALLOW_CONTENT:
        payload["messages"] = _extract_messages(message)
    else:
        payload["messages"] = []

    return payload


def _build_user_activity_payload(
    *,
    event_type: str,
    user_id: str,
    company_id: Optional[str],
    count: int,
    metadata: Optional[Dict[str, Any]],
    stat_ts: Optional[float],
) -> Optional[Dict[str, Any]]:
    snapshot = company_id or _maybe_get_company_id(user_id)
    ts = _coerce_datetime(stat_ts) or datetime.now(timezone.utc)
    payload = {
        "stat_date": ts.strftime("%Y-%m-%d"),
        "company_id": snapshot,
        "user_id": user_id,
        "event_type": event_type,
        "count": max(1, count),
        "metadata": _sanitize_metadata(metadata),
    }
    return payload


def _build_system_metric_payload(
    metric: str,
    value: float,
    *,
    dimension: Optional[Dict[str, Any]],
    stat_hour_ts: Optional[float],
) -> Dict[str, Any]:
    ts = _coerce_datetime(stat_hour_ts) or datetime.now(timezone.utc)
    ts = ts.replace(minute=0, second=0, microsecond=0)
    return {
        "stat_hour": ts.isoformat(),
        "metric": metric,
        "value": float(value),
        "dimension": _sanitize_metadata(dimension),
    }


def _build_idempotency_key(prefix: str, payload: Dict[str, Any]) -> str:
    try:
        body = json.dumps(payload, sort_keys=True, default=str)
    except Exception:
        body = str(payload)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"{prefix}-{digest}"


def _sanitize_list(values: Any) -> Optional[list]:
    if not values:
        return None
    if isinstance(values, list):
        clean = [str(v) for v in values if v is not None]
        return clean or None
    return [str(values)]


def _sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not metadata:
        return {}
    clean: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            clean[key] = value
        else:
            clean[key] = str(value)
    return clean


def _infer_bounced(turn_count: Optional[int], status: Optional[str]) -> Optional[bool]:
    if turn_count is None:
        return None
    if turn_count <= 1:
        return True
    if status and status.upper() in {"FAILED", "ERROR"} and turn_count <= 2:
        return True
    return False


def _infer_duration_seconds(started_ts: Optional[Any], ended_ts: Optional[Any]) -> Optional[int]:
    start = _coerce_datetime(started_ts)
    end = _coerce_datetime(ended_ts)
    if not start or not end:
        return None
    delta = (end - start).total_seconds()
    return int(delta) if delta >= 0 else None


def _extract_messages(message: Dict[str, Any]) -> list:
    data = message.get("messages")
    if isinstance(data, list):
        return data
    content = message.get("content") or {}
    if isinstance(content, dict):
        maybe = content.get("messages")
        if isinstance(maybe, list):
            return maybe
    return []


def _first_value(*values: Any) -> Optional[Any]:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _coerce_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        ivalue = int(float(value))
        return ivalue
    except Exception:
        return None


def _coerce_epoch_ms(value: Any) -> int:
    if value is None:
        return int(time.time() * 1000)
    try:
        numeric = float(value)
        if numeric < 0:
            numeric = time.time() * 1000
    except Exception:
        numeric = time.time() * 1000
    if numeric < 1_000_000_000_000:  # seconds
        numeric *= 1000
    return int(numeric)


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    try:
        numeric = float(value)
        if numeric > 1_000_000_000_000:
            numeric /= 1000.0
        return datetime.fromtimestamp(numeric, tz=timezone.utc)
    except Exception:
        return None


def _isoformat(value: Any) -> Optional[str]:
    dt = _coerce_datetime(value)
    return dt.isoformat() if dt else None


@lru_cache(maxsize=512)
def _resolve_user_snapshot(user_id: Optional[str]) -> Optional[UserModel]:
    if not user_id:
        return None
    try:
        return Users.get_user_by_id(user_id)
    except Exception as exc:
        log.debug("Failed to resolve user %s for ops dashboard: %s", user_id, exc)
        return None


def _maybe_get_company_id(user_id: Optional[str]) -> Optional[str]:
    snapshot = _resolve_user_snapshot(user_id)
    if snapshot:
        return getattr(snapshot, "company_id", None)
    return None
