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
    轻量封装 FFmpeg OSS 服务 (`/oss/*`)，统一处理请求与错误日志。
    """

    def __init__(
        self,
        base_url: str,
        api_prefix: str = "/api/v1",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix if api_prefix.startswith("/") else f"/{api_prefix}"
        self.api_prefix = self.api_prefix.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _ensure_client(self) -> httpx.Client:
        if not self._client:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
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

# 控制是否生成签名下载链接：
# - true：通过 `/oss/download-url` 生成签名 URL（默认）
# - false：直接返回对象 URL（要求 OSS 对象/桶已配置公网可读），不再请求 `/oss/download-url`
FFMPEG_OSS_SIGNED_URL_ENABLED = os.environ.get("FFMPEG_OSS_SIGNED_URL_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


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
    if not FFMPEG_OSS_SIGNED_URL_ENABLED:
        # 开关关闭时：优先返回可直接访问的 URL（通常由 upload 返回），否则回退 fallback。
        if isinstance(object_name, str) and object_name.startswith(("http://", "https://")):
            return object_name
        return fallback_url

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
