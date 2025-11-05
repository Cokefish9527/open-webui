import os
from pathlib import Path
from typing import Dict, Optional

from fastapi import HTTPException, status

from open_webui.config import UPLOAD_DIR
from open_webui.config.materials import MATERIAL_STORAGE_BACKEND, USE_FFMPEG_BACKEND
from open_webui.integrations.ffmpeg_oss import ensure_download_url, upload_via_ffmpeg

LOCAL_STORAGE_ROOT = Path(UPLOAD_DIR) / "materials"
LOCAL_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def _local_save_file(
    content: bytes,
    storage_filename: str,
    business_segment: str,
    user_segment: str,
) -> Dict[str, Optional[str]]:
    target_dir = LOCAL_STORAGE_ROOT / business_segment / user_segment
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / storage_filename
    try:
        target_path.write_bytes(content)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist material locally: {exc}",
        ) from exc

    public_url = (
        f"http://localhost:8080/uploads/materials/"
        f"{business_segment}/{user_segment}/{storage_filename}"
    )

    return {
        "storage_provider": "local",
        "file_url": public_url,
        "file_path": str(target_path),
        "oss_bucket": None,
        "oss_key": None,
    }


def _ffmpeg_save_file(
    content: bytes,
    storage_key: str,
    original_filename: str,
) -> Dict[str, Optional[str]]:
    result = upload_via_ffmpeg(
        content,
        storage_key,
        Path(original_filename).suffix or "application/octet-stream",
    )
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="FFmpeg OSS upload failed",
        )
    file_url = (
        result.get("url") or result.get("downloadUrl") or result.get("ossUrl")
    )
    if not file_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="FFmpeg OSS returned no download URL",
        )

    return {
        "storage_provider": "ffmpeg",
        "file_url": file_url,
        "file_path": file_url,
        "oss_bucket": result.get("bucket") or result.get("bucketName"),
        "oss_key": result.get("objectName") or storage_key,
    }


def save_material_file(
    content: bytes,
    storage_filename: str,
    storage_key: str,
    business_segment: str,
    user_segment: str,
    original_filename: str,
) -> Dict[str, Optional[str]]:
    if USE_FFMPEG_BACKEND:
        return _ffmpeg_save_file(content, storage_key, original_filename)

    return _local_save_file(
        content,
        storage_filename,
        business_segment,
        user_segment,
    )


def generate_download_payload(material, expires: int = 900) -> Dict[str, str]:
    backend = MATERIAL_STORAGE_BACKEND
    if backend == "ffmpeg":
        if not material.oss_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Material missing oss_key for FFmpeg backend",
            )
        signed_url = ensure_download_url(material.oss_key, expires=expires)
        return {
            "download_url": signed_url,
            "filename": material.name,
            "file_size": material.file_size,
            "mime_type": material.mime_type,
        }

    # local backend
    file_path = material.file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material file not found on local storage",
        )
    return {
        "download_url": file_path,
        "filename": material.name,
        "file_size": material.file_size,
        "mime_type": material.mime_type,
    }

