import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import aiohttp


@dataclass
class MinimaxAPIError(Exception):
    status: int
    message: str
    payload: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:  # pragma: no cover
        return f"MinimaxAPIError(status={self.status}, message={self.message})"


def _shorten(text: str, max_len: int = 800) -> str:
    try:
        s = (text or "").strip()
        if len(s) <= max_len:
            return s
        return s[:max_len] + "...[truncated]"
    except Exception:  # pragma: no cover
        return str(text)[:max_len]


class MinimaxSpeechClient:
    """
    Minimal async client for MiniMax Speech APIs (voice management, file, T2A).

    Upstream base URL: https://api.minimax.io
    Auth: Authorization: Bearer <API_KEY>
    """

    def __init__(self, *, base_url: str = "https://api.minimax.io", timeout_seconds: int = 30) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=max(5, int(timeout_seconds or 30)))

    def _url(self, path: str) -> str:
        path = "/" + str(path or "").lstrip("/")
        return f"{self._base_url}{path}"

    def _headers(self, api_key: str, *, content_type: Optional[str] = None) -> Dict[str, str]:
        headers = {"Authorization": f"Bearer {api_key}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        api_key: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        data: Any = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = self._url(path)
        async with aiohttp.ClientSession(timeout=self._timeout, trust_env=True) as session:
            async with session.request(
                method=method,
                url=url,
                headers=self._headers(api_key, content_type=content_type),
                params=params,
                json=json_body,
                data=data,
            ) as resp:
                text = await resp.text()
                try:
                    payload = await resp.json()
                except Exception:
                    payload = None

                if resp.status >= 400:
                    raise MinimaxAPIError(
                        status=resp.status,
                        message=_shorten(text),
                        payload=payload if isinstance(payload, dict) else None,
                    )

                if isinstance(payload, dict):
                    base_resp = payload.get("base_resp")
                    if isinstance(base_resp, dict):
                        status_code = base_resp.get("status_code")
                        if isinstance(status_code, int) and status_code != 0:
                            raise MinimaxAPIError(
                                status=resp.status,
                                message=str(base_resp.get("status_msg") or "minimax base_resp error"),
                                payload=payload,
                            )
                    return payload

                raise MinimaxAPIError(status=resp.status, message="invalid minimax json response", payload=None)

    async def _request_bytes(
        self,
        method: str,
        path: str,
        *,
        api_key: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, bytes, Dict[str, str]]:
        url = self._url(path)
        async with aiohttp.ClientSession(timeout=self._timeout, trust_env=True) as session:
            async with session.request(
                method=method,
                url=url,
                headers=self._headers(api_key),
                params=params,
            ) as resp:
                body = await resp.read()
                if resp.status >= 400:
                    raise MinimaxAPIError(status=resp.status, message=_shorten(body.decode("utf-8", "ignore")))
                return resp.status, body, {k: v for k, v in resp.headers.items()}

    # ---- Voice Management ----

    async def get_voice(self, *, api_key: str, voice_type: str) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/get_voice",
            api_key=api_key,
            json_body={"voice_type": voice_type},
            content_type="application/json",
        )

    async def delete_voice(self, *, api_key: str, voice_type: str, voice_id: str) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/delete_voice",
            api_key=api_key,
            json_body={"voice_type": voice_type, "voice_id": voice_id},
            content_type="application/json",
        )

    # ---- File Management ----

    async def upload_file(
        self,
        *,
        api_key: str,
        purpose: str,
        filename: str,
        content: bytes,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        form = aiohttp.FormData()
        form.add_field("purpose", str(purpose))
        form.add_field(
            "file",
            content,
            filename=filename,
            content_type=content_type or "application/octet-stream",
        )
        return await self._request_json("POST", "/v1/files/upload", api_key=api_key, data=form)

    async def retrieve_file(self, *, api_key: str, file_id: int) -> Dict[str, Any]:
        return await self._request_json(
            "GET",
            "/v1/files/retrieve",
            api_key=api_key,
            params={"file_id": int(file_id)},
        )

    async def retrieve_file_content(self, *, api_key: str, file_id: int) -> Tuple[int, bytes, Dict[str, str]]:
        return await self._request_bytes(
            "GET",
            "/v1/files/retrieve_content",
            api_key=api_key,
            params={"file_id": int(file_id)},
        )

    async def list_files(self, *, api_key: str, purpose: str) -> Dict[str, Any]:
        return await self._request_json(
            "GET",
            "/v1/files/list",
            api_key=api_key,
            params={"purpose": str(purpose)},
        )

    async def delete_file(self, *, api_key: str, file_id: int, purpose: str) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/files/delete",
            api_key=api_key,
            json_body={"file_id": int(file_id), "purpose": str(purpose)},
            content_type="application/json",
        )

    # ---- Voice Cloning / Design ----

    async def voice_clone(self, *, api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Payload is passed through (file_id/voice_id/clone_prompt/text/model/...)
        return await self._request_json(
            "POST",
            "/v1/voice_clone",
            api_key=api_key,
            json_body=payload,
            content_type="application/json",
        )

    async def voice_design(self, *, api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/voice_design",
            api_key=api_key,
            json_body=payload,
            content_type="application/json",
        )

    # ---- Speech T2A ----

    async def t2a_v2(self, *, api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/t2a_v2",
            api_key=api_key,
            json_body=payload,
            content_type="application/json",
        )

    async def t2a_async_v2_create(self, *, api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/t2a_async_v2",
            api_key=api_key,
            json_body=payload,
            content_type="application/json",
        )

    async def t2a_async_v2_query(self, *, api_key: str, task_id: int) -> Dict[str, Any]:
        return await self._request_json(
            "GET",
            "/v1/query/t2a_async_query_v2",
            api_key=api_key,
            params={"task_id": int(task_id)},
        )


minimax_speech_client = MinimaxSpeechClient()

