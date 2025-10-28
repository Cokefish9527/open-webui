"""
Playwright MCP 客户端封装
用于与 Playwright MCP Runner 通讯、执行自动化任务并回传执行日志
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiohttp

log = logging.getLogger(__name__)


class PlaywrightMCPError(Exception):
    """Playwright MCP 通用异常"""


@dataclass
class PlaywrightMCPResult:
    request_id: str
    status: str
    message: Optional[str]
    artifacts: Dict[str, Any]
    raw: Dict[str, Any]


class PlaywrightMCPClient:
    """Playwright MCP 通讯客户端"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 240,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.base_url = (base_url or os.getenv("PLAYWRIGHT_MCP_ENDPOINT", "")).rstrip("/")
        if not self.base_url:
            raise ValueError("PLAYWRIGHT_MCP_ENDPOINT 未配置，无法初始化 Playwright MCP 客户端")

        self.timeout = timeout
        self._session = session
        self._session_owner = session is None

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session_owner:
            await self.close()

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取 MCP Runner 暴露的可用工具列表"""
        await self._ensure_session()
        url = f"{self.base_url}/tools"
        async with self._session.get(url) as resp:
            if resp.status != 200:
                raise PlaywrightMCPError(f"获取工具列表失败: {resp.status}")
            payload = await resp.json()
            return payload.get("data", [])

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlaywrightMCPResult:
        """执行 MCP 工具任务"""
        await self._ensure_session()
        request_id = str(uuid4())
        body = {
            "request_id": request_id,
            "tool": tool_name,
            "arguments": arguments,
            "metadata": metadata or {},
        }

        url = f"{self.base_url}/execute"
        log.debug("Playwright MCP request %s -> %s", request_id, tool_name)

        async with self._session.post(url, json=body) as resp:
            raw = await self._parse_response(resp, tool_name)
            status = raw.get("status", "error")
            if status != "ok":
                detail = (
                    raw.get("message")
                    or raw.get("error")
                    or json.dumps(raw, ensure_ascii=False)
                    or "Unknown MCP error"
                )
                raise PlaywrightMCPError(
                    f"MCP 执行失败 [{tool_name}]: {detail}"
                )

            result = PlaywrightMCPResult(
                request_id=request_id,
                status=status,
                message=raw.get("message"),
                artifacts=raw.get("artifacts", {}),
                raw=raw,
            )
            log.debug("Playwright MCP response %s <- %s", request_id, tool_name)
            return result

    async def _parse_response(
        self, resp: aiohttp.ClientResponse, tool_name: str
    ) -> Dict[str, Any]:
        try:
            text = await resp.text()

            if resp.status >= 400:
                body_preview = text if text else "<empty>"
                raise PlaywrightMCPError(
                    f"MCP 请求失败 (HTTP {resp.status}) [{tool_name}]: {body_preview}"
                )

            if not text:
                raise PlaywrightMCPError(f"MCP 返回空响应 (HTTP {resp.status})")
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise PlaywrightMCPError(f"MCP 返回非 JSON 数据: {text}") from exc
        finally:
            if resp.closed is False:
                resp.release()


async def execute_tool(
    tool: str,
    arguments: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    timeout: int = 240,
) -> PlaywrightMCPResult:
    """便捷方法：一次性执行 MCP 任务"""
    async with PlaywrightMCPClient(timeout=timeout) as client:
        return await client.execute(tool, arguments, metadata)
