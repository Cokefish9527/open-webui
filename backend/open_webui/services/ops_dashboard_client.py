import asyncio
import json
import logging
from typing import Any, Dict, Optional

import aiohttp

from open_webui.env import (
    OPS_DASHBOARD_API_KEY,
    OPS_DASHBOARD_BASE_URL,
    OPS_DASHBOARD_ENABLED,
    OPS_DASHBOARD_MAX_RETRY,
    OPS_DASHBOARD_TIMEOUT,
)

log = logging.getLogger(__name__)


class OpsDashboardClient:
    """Async HTTP client for Ops Dashboard ingestion endpoints."""

    def __init__(self) -> None:
        self._enabled = OPS_DASHBOARD_ENABLED
        self._base_url = OPS_DASHBOARD_BASE_URL.rstrip("/") if OPS_DASHBOARD_BASE_URL else ""
        self._api_key = OPS_DASHBOARD_API_KEY.strip()
        self._timeout = OPS_DASHBOARD_TIMEOUT or 5
        self._max_retries = max(1, OPS_DASHBOARD_MAX_RETRY or 3)
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        self._base_url_warning_emitted = False

    async def _ensure_session(self) -> aiohttp.ClientSession:
        async with self._session_lock:
            if self._session is None:
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                self._session = aiohttp.ClientSession(
                    timeout=timeout,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "OpenWebUI-OpsDashboard/1.0",
                    },
                )
        return self._session

    def _build_url(self, endpoint: str) -> Optional[str]:
        if not self._enabled:
            return None
        if not self._base_url:
            if not self._base_url_warning_emitted:
                log.warning("OPS_DASHBOARD_BASE_URL is empty; skip ingestion.")
                self._base_url_warning_emitted = True
            return None
        return f"{self._base_url}{endpoint}"

    def _headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    async def _post(
        self,
        endpoint: str,
        payload: Any,
        *,
        idempotency_key: Optional[str] = None,
    ) -> bool:
        url = self._build_url(endpoint)
        if not url:
            return False

        session = await self._ensure_session()
        attempt = 0
        backoff = 1

        while attempt < self._max_retries:
            attempt += 1
            try:
                async with session.post(
                    url,
                    json=payload,
                    headers=self._headers(idempotency_key=idempotency_key),
                ) as resp:
                    if 200 <= resp.status < 300:
                        return True
                    body = await resp.text()
                    if 400 <= resp.status < 500:
                        # 对于4xx认为是可预期的配置/权限问题，降级为 WARNING，并截断响应体
                        log.warning(
                            "OpsDashboard request failed (status=%s, endpoint=%s, body=%s)",
                            resp.status,
                            endpoint,
                            _shorten_text(body),
                        )
                        return False
                    log.warning(
                        "OpsDashboard server error (status=%s, endpoint=%s, body=%s)",
                        resp.status,
                        endpoint,
                        _shorten_text(body),
                    )
            except Exception as exc:
                log.warning(
                    "OpsDashboard request exception (endpoint=%s, attempt=%s): %s",
                    endpoint,
                    attempt,
                    exc,
                )

            await asyncio.sleep(min(backoff, 30))
            backoff *= 2

        # 重试用尽同样降级为 WARNING，避免在启动阶段污染错误日志
        log.warning(
            "OpsDashboard request exhausted retries (endpoint=%s, payload=%s)",
            endpoint,
            _safe_json(payload),
        )
        return False

    async def send_conversations(self, payload: Any, *, idempotency_key: Optional[str] = None) -> bool:
        return await self._post(
            "/system/index/ops_dashboard/conversations",
            payload,
            idempotency_key=idempotency_key,
        )

    async def send_user_activity(self, payload: Any, *, idempotency_key: Optional[str] = None) -> bool:
        return await self._post(
            "/system/index/ops_dashboard/user-activity",
            payload,
            idempotency_key=idempotency_key,
        )

    async def send_system_metrics(self, payload: Any, *, idempotency_key: Optional[str] = None) -> bool:
        return await self._post(
            "/system/index/ops_dashboard/system-metrics",
            payload,
            idempotency_key=idempotency_key,
        )

    async def close(self) -> None:
        async with self._session_lock:
            if self._session is None:
                return
            session = self._session
            self._session = None
        await session.close()


def _safe_json(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False)[:500]
    except Exception:
        return str(payload)[:500]


def _shorten_text(text: str, max_len: int = 500) -> str:
    try:
        if not text:
            return ""
        text = str(text).strip()
        if len(text) <= max_len:
            return text
        return text[:max_len] + "…[truncated]"
    except Exception:
        return str(text)[:max_len]


ops_dashboard_client = OpsDashboardClient()
