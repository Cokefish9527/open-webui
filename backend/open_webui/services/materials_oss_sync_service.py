import logging
import mimetypes
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import NAMESPACE_URL, uuid4, uuid5

from open_webui.env import (
    DATABASE_SCHEMA,
    HSAI_MATERIALS_OSS_BUCKET,
    HSAI_MATERIALS_OSS_MAX_KEYS,
    HSAI_MATERIALS_OSS_SYNC_ENABLED,
    SRC_LOG_LEVELS,
)
from open_webui.integrations.ffmpeg_oss import get_client as get_ffmpeg_oss_client
from open_webui.internal.db import get_db
from open_webui.internal.migrations import ensure_materials_storage_schema
from open_webui.models.hsai_materials import HSAIMaterial, HSAIMaterialFolder

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


_OSS_FOLDER_TYPE = "oss_virtual"


@dataclass(frozen=True)
class OssObject:
    key: str
    size: int
    last_modified_epoch: Optional[int]
    url: Optional[str]


def _parse_last_modified(value: Any) -> Optional[int]:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    raw = str(value).strip()
    if not raw:
        return None
    try:
        # RFC3339 "2025-12-12T06:05:12Z"
        normalized = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


def _determine_material_type(mime_type: Optional[str]) -> str:
    if not mime_type:
        return "document"
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    if mime_type.startswith("audio/"):
        return "audio"
    if mime_type.startswith("text/"):
        return "text"
    if mime_type in {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        return "document"
    return "document"


def _parse_filename_for_codes(filename: str) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    stem = Path(filename).stem
    # strip md5 hash suffix if present (32 hex chars at tail)
    hash_pattern = re.compile(r"([a-fA-F0-9]{32})$")
    match = hash_pattern.search(stem)
    base_name = stem[: match.start()] if match else stem
    base_name = base_name.rstrip("_")

    parts = [p for p in base_name.split("_") if p]
    if len(parts) < 2:
        return base_name, None, None, None

    material_name = parts[0]
    scene_code = parts[1] if len(parts) > 1 else None
    technique_code = parts[2] if len(parts) > 2 else None
    properties_code = "_".join(parts[3:]) if len(parts) > 3 else None
    return material_name, scene_code, technique_code, properties_code


def _virtual_folder_id(company_id: str, relative_prefix: str) -> str:
    normalized = (relative_prefix or "").strip("/")
    seed = f"oss-folder:{company_id}:{normalized}"
    return str(uuid5(NAMESPACE_URL, seed))


def _normalize_relative_prefix(materials_root_prefix: str, object_key: str) -> str:
    prefix = materials_root_prefix.strip("/")
    key = str(object_key).strip("/")
    if key.startswith(prefix + "/"):
        key = key[len(prefix) + 1 :]
    dirname = os.path.dirname(key)
    if dirname in (".", "/"):
        return ""
    return dirname.strip("/")


def _normalize_objects(payload: Any) -> List[OssObject]:
    if not isinstance(payload, list):
        return []
    results: List[OssObject] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        key = str(item.get("name") or item.get("key") or "").strip()
        if not key or key.endswith("/"):
            continue
        results.append(
            OssObject(
                key=key,
                size=int(item.get("size") or 0),
                last_modified_epoch=_parse_last_modified(item.get("lastModified")),
                url=item.get("url"),
            )
        )
    return results


class MaterialsOssSyncService:
    """
    以 company_id 为 scope 从 OSS 拉取对象清单，并将目录与素材元数据回填到 DB。

    - OSS 前缀规则：enterprises/{company_id}/materials（与后台一致）
    - 目录映射：OSS 子目录 -> 虚拟文件夹（hsai_material_folders, user_id=company_id）
    - 素材归属：user_id 使用触发同步的 actor_user_id（企业内共享通过 company_id 过滤实现）
    """

    def __init__(self) -> None:
        self.bucket = HSAI_MATERIALS_OSS_BUCKET
        self.max_keys = HSAI_MATERIALS_OSS_MAX_KEYS

    def sync_company(self, *, company_id: str, actor_user_id: str) -> Dict[str, int]:
        if not HSAI_MATERIALS_OSS_SYNC_ENABLED:
            return {"folders_upserted": 0, "materials_upserted": 0}

        client = get_ffmpeg_oss_client()
        if client is None:
            log.warning("FFmpeg OSS client unavailable; skip materials oss sync")
            return {"folders_upserted": 0, "materials_upserted": 0}

        # 约定：使用企业名称（business_name）作为 OSS 顶层前缀。
        # 这里通过 actor_user_id 反查用户信息时已经在上层完成，当前实现直接假定
        # OSS 中的对象 key 已经以企业名称段作为前缀，例如 HSAI_TEST/人物口播/....
        # 因此，这里不再对前缀做额外拼接，交由调用方控制。
        materials_prefix = ""
        try:
            payload = client.list_objects(
                prefix=materials_prefix,
                bucket=self.bucket,
                max_keys=self.max_keys,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to list OSS objects for materials prefix=%s err=%s", materials_prefix, exc)
            return {"folders_upserted": 0, "materials_upserted": 0}

        objects = _normalize_objects(payload)
        if not objects:
            return {"folders_upserted": 0, "materials_upserted": 0}

        required_prefixes = sorted(
            {
                prefix
                for prefix in (
                    _normalize_relative_prefix(materials_prefix, obj.key) for obj in objects
                )
                if prefix
            },
            key=lambda v: (v.count("/"), v),
        )

        with get_db() as db:
            ensure_materials_storage_schema(
                db.get_bind(),
                schema=DATABASE_SCHEMA,
                logger=log.debug,
            )

            # 预加载已有虚拟目录映射：oss_prefix -> (id, parent_id)
            existing_folders = (
                db.query(HSAIMaterialFolder).filter_by(user_id=company_id).all()
            )
            folder_by_prefix: Dict[str, HSAIMaterialFolder] = {}
            folder_by_id: Dict[str, HSAIMaterialFolder] = {}
            for folder in existing_folders:
                folder_by_id[folder.id] = folder
                settings = folder.settings or {}
                if isinstance(settings, dict) and settings.get("folder_type") == _OSS_FOLDER_TYPE:
                    prefix = str(settings.get("oss_prefix") or "").strip("/")
                    if prefix:
                        folder_by_prefix[prefix] = folder

            folders_upserted = 0
            now_ts = int(time.time())

            # 按层级创建目录，保证 parent 先于 child 存在
            for prefix in required_prefixes:
                if prefix in folder_by_prefix:
                    continue
                folder_id = _virtual_folder_id(company_id, prefix)
                parent_prefix = prefix.rsplit("/", 1)[0] if "/" in prefix else ""
                parent_folder = folder_by_prefix.get(parent_prefix) if parent_prefix else None
                parent_id = parent_folder.id if parent_folder else None

                folder = HSAIMaterialFolder(
                    id=folder_id,
                    name=prefix.rsplit("/", 1)[-1],
                    description=None,
                    parent_id=parent_id,
                    user_id=company_id,
                    settings={"folder_type": _OSS_FOLDER_TYPE, "oss_prefix": prefix},
                    sort_order=0,
                    created_at=now_ts,
                    updated_at=now_ts,
                )
                db.add(folder)
                folder_by_prefix[prefix] = folder
                folder_by_id[folder_id] = folder
                folders_upserted += 1

            # upsert materials by oss_key
            materials_upserted = 0
            for obj in objects:
                relative_prefix = _normalize_relative_prefix(materials_prefix, obj.key)
                folder_id = folder_by_prefix.get(relative_prefix).id if relative_prefix else None
                filename = Path(obj.key).name
                mime_type, _ = mimetypes.guess_type(filename)
                material_type = _determine_material_type(mime_type)
                name, scene_code, technique_code, properties_code = _parse_filename_for_codes(filename)

                existing = db.query(HSAIMaterial).filter_by(oss_key=obj.key).first()
                updated_at = obj.last_modified_epoch or now_ts
                if existing:
                    changed = False
                    if getattr(existing, "enterprise_id", None) != company_id:
                        existing.enterprise_id = company_id
                        changed = True
                    if existing.status != "active":
                        existing.status = "active"
                        changed = True
                    if existing.is_deleted:
                        existing.is_deleted = False
                        existing.deleted_at = None
                        existing.deleted_by = None
                        changed = True
                    if folder_id is not None and existing.folder_id != folder_id:
                        existing.folder_id = folder_id
                        changed = True
                    if obj.size and existing.file_size != obj.size:
                        existing.file_size = obj.size
                        changed = True
                    if obj.url and existing.file_path != obj.url:
                        existing.file_path = obj.url
                        changed = True
                    if mime_type and existing.mime_type != mime_type:
                        existing.mime_type = mime_type
                        changed = True
                    if existing.material_type != material_type:
                        existing.material_type = material_type
                        changed = True
                    if existing.scene_code != scene_code:
                        existing.scene_code = scene_code
                        changed = True
                    if existing.technique_code != technique_code:
                        existing.technique_code = technique_code
                        changed = True
                    if existing.properties_code != properties_code:
                        existing.properties_code = properties_code
                        changed = True
                    if existing.updated_at != updated_at:
                        existing.updated_at = updated_at
                        changed = True
                    if self.bucket and existing.oss_bucket != self.bucket:
                        existing.oss_bucket = self.bucket
                        changed = True
                    if existing.oss_object_path != obj.key:
                        existing.oss_object_path = obj.key
                        changed = True
                    if changed:
                        materials_upserted += 1
                    continue

                material = HSAIMaterial(
                    id=str(uuid4()),
                    name=name or Path(filename).stem,
                    description=None,
                    material_type=material_type,
                    folder_id=folder_id,
                    user_id=actor_user_id,
                    enterprise_id=company_id,
                    file_path=obj.url,
                    file_size=obj.size or None,
                    file_hash=None,
                    mime_type=mime_type,
                    material_metadata=None,
                    tags=None,
                    ai_analysis=None,
                    usage_count=0,
                    last_used_at=None,
                    status="active",
                    access_control=None,
                    scene_code=scene_code,
                    technique_code=technique_code,
                    properties_code=properties_code,
                    duration=None,
                    resolution=None,
                    oss_bucket=self.bucket,
                    oss_key=obj.key,
                    oss_object_path=obj.key,
                    is_deleted=False,
                    original_directory=None,
                    deleted_at=None,
                    deleted_by=None,
                    created_at=now_ts,
                    updated_at=updated_at,
                )
                db.add(material)
                materials_upserted += 1

            try:
                db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                log.warning("Materials oss sync commit failed: %s", exc)
                return {"folders_upserted": 0, "materials_upserted": 0}

            return {
                "folders_upserted": folders_upserted,
                "materials_upserted": materials_upserted,
            }
