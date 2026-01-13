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
        api_prefix: str = "/api/v1",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_prefix = api_prefix if api_prefix.startswith("/") else f"/{api_prefix}"
        self.api_prefix = self.api_prefix.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            token = self.api_key.strip()
            if token:
                headers["Authorization"] = (
                    token if token.lower().startswith("bearer ") else f"Bearer {token}"
                )
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
        bucket: Optional[str] = None,
    ) -> str:
        """
        调用 `/oss/download-url` 生成签名链接。
        """
        if not object_name:
            raise ValueError("object_name is required")
        client = self._ensure_client()
        params: Dict[str, Any] = {"objectName": object_name, "expires": expires}
        if bucket:
            params["bucket"] = bucket
        response = client.get(
            f"{self.api_prefix}/oss/download-url",
            params=params,
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
        filename: str = "upload.bin",
    ) -> Dict[str, Any]:
        """
        调用 `/oss/upload` 将文件推送到 OSS。
        FFmpeg API 预期接收 multipart/form-data。
        """
        if not target_path:
            raise ValueError("target_path is required")
        client = self._ensure_client()
        safe_filename = filename or "upload.bin"
        files = {"file": (safe_filename, file_content, content_type or "application/octet-stream")}
        data = {"path": target_path}
        response = client.post(f"{self.api_prefix}/oss/upload", files=files, data=data)
        response.raise_for_status()
        return response.json()

    def list_objects(
        self,
        prefix: str = "",
        *,
        bucket: Optional[str] = None,
        max_keys: int = 1000,
    ) -> Any:
        client = self._ensure_client()
        params: Dict[str, Any] = {"prefix": prefix, "maxKeys": max_keys}
        if bucket:
            params["bucket"] = bucket
        response = client.get(f"{self.api_prefix}/oss/objects", params=params)
        response.raise_for_status()
        return response.json()

    def list_tree(
        self,
        prefix: str = "",
        *,
        bucket: Optional[str] = None,
        depth: int = 2,
    ) -> Any:
        client = self._ensure_client()
        params: Dict[str, Any] = {"prefix": prefix, "depth": depth}
        if bucket:
            params["bucket"] = bucket
        response = client.get(f"{self.api_prefix}/oss/tree", params=params)
        response.raise_for_status()
        return response.json()

    def delete_object(
        self,
        object_name: str,
        *,
        bucket: Optional[str] = None,
    ) -> None:
        """
        调用 `/oss/object` 删除对象。
        """
        if not object_name:
            raise ValueError("object_name is required")
        client = self._ensure_client()
        params: Dict[str, Any] = {"objectName": object_name}
        if bucket:
            params["bucket"] = bucket
        response = client.delete(f"{self.api_prefix}/oss/object", params=params)
        response.raise_for_status()


_FFMPEG_API_BASE_URL = os.environ.get("FFMPEG_API_BASE_URL", "").strip()
_FFMPEG_API_TIMEOUT = float(os.environ.get("FFMPEG_API_TIMEOUT", "30"))
_FFMPEG_OSS_API_PREFIX = os.environ.get("FFMPEG_OSS_API_PREFIX", "/api/v1").strip() or "/api/v1"

# OSS 管理接口（ffmpeg-go `/oss/*`）默认不需要鉴权。
# 若未来需要鉴权，显式配置 FFMPEG_OSS_API_KEY 才会发送 Authorization 头。
_FFMPEG_OSS_API_KEY = os.environ.get("FFMPEG_OSS_API_KEY", "").strip()


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
            api_key=_FFMPEG_OSS_API_KEY or None,
            api_prefix=_FFMPEG_OSS_API_PREFIX,
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
    bucket: Optional[str] = None,
) -> Optional[str]:
    """
    若启用 FFmpeg OSS 且可用，则生成签名链接；否则返回 fallback。
    """
    client = get_client()
    if client:
        try:
            return client.generate_download_url(object_name, expires=expires, bucket=bucket)
        except Exception as exc:  # noqa: BLE001
            log.warning("generate_download_url via FFmpeg API failed: %s", exc)
    return fallback_url


def upload_via_ffmpeg(
    file_content: bytes,
    target_path: str,
    content_type: Optional[str] = None,
    filename: str = "upload.bin",
) -> Optional[Dict[str, Any]]:
    client = get_client()
    if not client:
        return None
    try:
        return client.upload_stream(
            file_content,
            target_path,
            content_type=content_type,
            filename=filename,
        )
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
