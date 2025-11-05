import base64
import logging
import os
from typing import Any, Dict, Optional

import httpx

from open_webui.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("INTEGRATIONS", logging.INFO))


class FfmpegOssClient:
    """
    轻量封装 FFmpeg OSS 服务 (`/oss/*`)，统一处理鉴权、请求与错误日志。
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str],
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = self.api_key
        return headers

    def _ensure_client(self) -> httpx.Client:
        if not self._client:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._get_headers(),
            )
        return self._client

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def generate_download_url(
        self,
        object_name: str,
        expires: int = 900,
    ) -> str:
        """
        调用 `/oss/download-url` 生成签名链接。
        """
        if not object_name:
            raise ValueError("object_name is required")
        client = self._ensure_client()
        response = client.get(
            "/oss/download-url",
            params={"objectName": object_name, "expires": expires},
        )
        response.raise_for_status()
        payload = response.json()
        signed_url = payload.get("url") or payload.get("downloadUrl")
        if not signed_url:
            raise RuntimeError("FFmpeg OSS download-url response missing `url`")
        return signed_url

    def upload_stream(
        self,
        file_content: bytes,
        target_path: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        调用 `/oss/upload` 将文件推送到 OSS。
        FFmpeg API 预期接收 multipart/form-data。
        """
        if not target_path:
            raise ValueError("target_path is required")
        client = self._ensure_client()
        files = {"file": ("upload.bin", file_content, content_type or "application/octet-stream")}
        data = {"path": target_path}
        response = client.post("/oss/upload", files=files, data=data)
        response.raise_for_status()
        return response.json()

    def list_tree(self, directories: Optional[str] = None) -> Dict[str, Any]:
        client = self._ensure_client()
        response = client.get(
            "/oss/tree",
            params={"directories": directories} if directories else None,
        )
        response.raise_for_status()
        return response.json()


_FFMPEG_API_BASE_URL = os.environ.get("FFMPEG_API_BASE_URL", "").strip()
_FFMPEG_API_KEY = os.environ.get("FFMPEG_API_KEY", "").strip()
_FFMPEG_API_TIMEOUT = float(os.environ.get("FFMPEG_API_TIMEOUT", "30"))


USE_FFMPEG_OSS = os.environ.get("USE_FFMPEG_OSS", "false").lower() == "true"


_ffmpeg_client: Optional[FfmpegOssClient] = None


def get_client() -> Optional[FfmpegOssClient]:
    global _ffmpeg_client
    if not USE_FFMPEG_OSS:
        return None
    if not _FFMPEG_API_BASE_URL:
        log.warning("USE_FFMPEG_OSS enabled but FFMPEG_API_BASE_URL is empty")
        return None
    if _ffmpeg_client is None:
        _ffmpeg_client = FfmpegOssClient(
            base_url=_FFMPEG_API_BASE_URL,
            api_key=_FFMPEG_API_KEY,
            timeout=_FFMPEG_API_TIMEOUT,
        )
    return _ffmpeg_client


def close_client() -> None:
    global _ffmpeg_client
    if _ffmpeg_client:
        _ffmpeg_client.close()
        _ffmpeg_client = None


def ensure_download_url(
    object_name: str,
    expires: int = 900,
    fallback_url: Optional[str] = None,
) -> Optional[str]:
    """
    若启用 FFmpeg OSS 且可用，则生成签名链接；否则返回 fallback。
    """
    client = get_client()
    if client:
        try:
            return client.generate_download_url(object_name, expires=expires)
        except Exception as exc:  # noqa: BLE001
            log.warning("generate_download_url via FFmpeg API failed: %s", exc)
    return fallback_url


def upload_via_ffmpeg(
    file_content: bytes,
    target_path: str,
    content_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    client = get_client()
    if not client:
        return None
    try:
        return client.upload_stream(file_content, target_path, content_type)
    except Exception as exc:  # noqa: BLE001
        log.warning("upload_via_ffmpeg failed: %s", exc)
        return None


__all__ = [
    "FfmpegOssClient",
    "get_client",
    "close_client",
    "ensure_download_url",
    "upload_via_ffmpeg",
    "USE_FFMPEG_OSS",
]
