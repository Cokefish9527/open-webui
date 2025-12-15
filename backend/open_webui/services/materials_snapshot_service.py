import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import get_db
from open_webui.models.hsai_materials import (
    HSAIMaterial,
    HSAIMaterialFolder,
    HSAIMaterialFolderResponse,
    HSAIMaterialResponse,
)
from open_webui.models.users import User

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


def list_company_materials(
    *,
    company_id: str,
    include_deleted: bool,
) -> List[HSAIMaterial]:
    with get_db() as db:
        query = (
            db.query(HSAIMaterial)
            .join(User, HSAIMaterial.user_id == User.id)
            .filter(User.company_id == company_id)
        )
        if include_deleted:
            query = query.filter(HSAIMaterial.is_deleted.is_(True))
        else:
            query = query.filter(HSAIMaterial.status == "active")
        return query.order_by(HSAIMaterial.updated_at.desc()).all()


def company_has_any_materials(*, company_id: str) -> bool:
    with get_db() as db:
        row = (
            db.query(HSAIMaterial.id)
            .join(User, HSAIMaterial.user_id == User.id)
            .filter(User.company_id == company_id)
            .limit(1)
            .first()
        )
        return bool(row and row[0])


def company_has_any_folders(*, company_id: str) -> bool:
    with get_db() as db:
        row = (
            db.query(HSAIMaterialFolder.id)
            .filter(HSAIMaterialFolder.user_id == company_id)
            .limit(1)
            .first()
        )
        return bool(row and row[0])


def build_company_material_index_snapshot(
    *,
    company_id: str,
    include_deleted: bool = False,
) -> List[Dict[str, Any]]:
    materials = list_company_materials(company_id=company_id, include_deleted=include_deleted)
    results: List[Dict[str, Any]] = []
    for material in materials:
        # 统一返回服务端下载入口（302 到真实 URL），便于前端 video/img 直接使用
        download_url = f"/api/v1/hsai/materials/{material.id}/download"

        properties_list: Optional[List[str]] = None
        if material.properties_code:
            if isinstance(material.properties_code, str):
                properties_list = [p for p in material.properties_code.split("_") if p]
            elif isinstance(material.properties_code, list):
                properties_list = material.properties_code

        payload = HSAIMaterialResponse(
            id=material.id,
            name=material.name,
            description=material.description,
            material_type=material.material_type,
            folder_id=material.folder_id,
            file_path=material.file_path,
            file_size=material.file_size,
            mime_type=material.mime_type,
            material_metadata=material.material_metadata,
            tags=material.tags,
            ai_analysis=material.ai_analysis,
            usage_count=int(material.usage_count or 0),
            last_used_at=material.last_used_at,
            status=material.status,
            thumbnail_url=f"/hsai/materials/{material.id}/thumbnail"
            if material.material_type in {"image", "video"}
            else None,
            download_url=download_url,
            scene_code=material.scene_code,
            technique_code=material.technique_code,
            properties_code=properties_list,
            duration=material.duration,
            resolution=material.resolution,
            oss_bucket=material.oss_bucket,
            oss_key=material.oss_key,
            oss_object_path=material.oss_object_path,
            is_deleted=bool(material.is_deleted),
            original_directory=material.original_directory,
            deleted_at=material.deleted_at,
            deleted_by=material.deleted_by,
            created_at=int(material.created_at or 0),
            updated_at=int(material.updated_at or 0),
        ).model_dump()
        results.append(payload)
    return results


def build_company_folders_snapshot(*, company_id: str) -> List[Dict[str, Any]]:
    with get_db() as db:
        folders = db.query(HSAIMaterialFolder).filter_by(user_id=company_id).all()

        material_counts = dict(
            db.query(HSAIMaterial.folder_id, func.count(HSAIMaterial.id))
            .join(User, HSAIMaterial.user_id == User.id)
            .filter(User.company_id == company_id)
            .filter(HSAIMaterial.status == "active")
            .group_by(HSAIMaterial.folder_id)
            .all()
        )

    response_by_id: Dict[str, HSAIMaterialFolderResponse] = {}
    roots: List[HSAIMaterialFolderResponse] = []

    for folder in folders:
        response_by_id[folder.id] = HSAIMaterialFolderResponse(
            id=folder.id,
            name=folder.name,
            label=folder.name,
            description=folder.description,
            parent_id=folder.parent_id,
            parent_name=None,
            settings=folder.settings,
            sort_order=int(folder.sort_order or 0),
            children=[],
            material_count=int(material_counts.get(folder.id) or 0),
            node_type=None,
            template_id=None,
            template_code=None,
            scene_id=None,
            scene_code=None,
            scene_name=None,
            item_id=None,
            item_code=None,
            is_required=None,
            shot_sizes=None,
            camera_movements=None,
            duration_min=None,
            duration_max=None,
            min_resolution=None,
            priority=None,
            shooting_tips=None,
            quality_standards=None,
            reference_video=None,
            reference_image=None,
            oss_object_path=None,
            oss_last_modified=None,
            sync_status=None,
            created_at=int(folder.created_at or 0),
            updated_at=int(folder.updated_at or 0),
        )

    for folder in folders:
        node = response_by_id[folder.id]
        if folder.parent_id and folder.parent_id in response_by_id:
            parent = response_by_id[folder.parent_id]
            node.parent_name = parent.name
            parent.children = parent.children or []
            parent.children.append(node)
        else:
            roots.append(node)

    # Sort for stable UI
    def sort_children(items: List[HSAIMaterialFolderResponse]) -> None:
        items.sort(key=lambda x: (x.sort_order or 0, x.name))
        for item in items:
            if item.children:
                sort_children(item.children)

    sort_children(roots)
    return [node.model_dump() for node in roots]


def paginate_items(items: List[Dict[str, Any]], *, page: int, size: int) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    total = len(items)
    page = max(int(page), 1)
    size = max(int(size), 1)
    total_pages = max(int(math.ceil(total / size)), 1) if total else 0
    start = (page - 1) * size
    end = start + size
    return (
        items[start:end],
        {"total": total, "page": page, "size": size, "total_pages": total_pages},
    )


def pick_any_user_id_for_company(company_id: str) -> Optional[str]:
    with get_db() as db:
        row = (
            db.query(User.id)
            .filter(User.company_id == company_id)
            .order_by(User.created_at.asc())
            .first()
        )
        return str(row[0]) if row and row[0] else None
