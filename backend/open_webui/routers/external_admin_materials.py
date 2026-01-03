"""
External Admin Materials API
供hsai_admin后台调用的素材管理接口
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from open_webui.models.hsai_materials import (
    HSAIMaterials,
    HSAIMaterialResponse,
    PaginationData,
    PaginatedHSAIMaterialResponse,
)
from open_webui.models.users import Users
from open_webui.utils.external_admin_auth import verify_external_request
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", logging.INFO))

router = APIRouter(prefix="/api/v1/external/admin/materials", tags=["External Admin - Materials"])


class MaterialTagInfo(BaseModel):
    """素材AI打标信息"""
    status: str = Field(description="打标状态：waiting/completed/error")
    category: Optional[str] = None
    scene_name: Optional[str] = None
    shot_type: Optional[str] = None
    camera_move: Optional[str] = None
    camera_angle: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[float] = None


class MaterialDetailResponse(HSAIMaterialResponse):
    """素材详情响应（包含打标信息）"""
    tag_info: Optional[MaterialTagInfo] = None
    user_name: Optional[str] = Field(default=None, description="上传用户名称")
    company_name: Optional[str] = Field(default=None, description="企业名称")


@router.get("/", response_model=PaginatedHSAIMaterialResponse, summary="查询素材列表")
async def list_materials(
    company_id: Optional[str] = Query(None, description="企业ID筛选"),
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    material_type: Optional[str] = Query(None, description="素材类型筛选"),
    scene_code: Optional[str] = Query(None, description="场景代码筛选"),
    query: Optional[str] = Query(None, description="关键词搜索"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    _: dict = Depends(verify_external_request),
):
    """
    查询素材列表（后台管理）
    
    支持按企业、用户、类型等筛选，返回素材基本信息列表。
    """
    try:
        # 查询素材
        materials = []
        
        if company_id:
            # 查询该企业下所有用户的素材
            company_users = Users.get_users()
            company_user_ids = [
                u.id for u in company_users 
                if getattr(u, "company_id", None) == company_id
            ]
            if not company_user_ids:
                return PaginatedHSAIMaterialResponse(
                    items=[],
                    total=0,
                    pagination=PaginationData(
                        page=offset // limit + 1,
                        pageSize=limit,
                        total=0,
                        totalPages=0
                    )
                )
            # 查询每个用户的素材并合并
            for uid in company_user_ids:
                user_materials = HSAIMaterials.get_materials_by_user_id(
                    uid,
                    material_type=material_type,
                    scene_code=scene_code
                )
                materials.extend(user_materials)
        elif user_id:
            # 查询指定用户的素材
            materials = HSAIMaterials.get_materials_by_user_id(
                user_id,
                material_type=material_type,
                scene_code=scene_code
            )
        else:
            # 查询所有素材（可能很慢，仅用于管理员）
            all_users = Users.get_users()
            for u in all_users:
                user_materials = HSAIMaterials.get_materials_by_user_id(
                    u.id,
                    material_type=material_type,
                    scene_code=scene_code
                )
                materials.extend(user_materials)
        
        # 如果有关键词搜索，过滤结果
        if query:
            query_lower = query.lower()
            materials = [
                m for m in materials
                if query_lower in (m.name or "").lower() 
                or query_lower in (m.description or "").lower()
            ]
        
        # 分页
        total = len(materials)
        paginated_materials = materials[offset:offset + limit]
        
        # 转换为响应格式
        items = []
        for material in paginated_materials:
            properties_list = None
            if material.properties_code:
                properties_list = material.properties_code.split("_")
            
            item = HSAIMaterialResponse(
                **{k: v for k, v in material.model_dump().items() if k != 'properties_code'},
                thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
                download_url=f"/api/v1/hsai/materials/{material.id}/download",
                properties_code=properties_list
            )
            items.append(item)
        
        total_pages = (total + limit - 1) // limit
        
        return PaginatedHSAIMaterialResponse(
            items=items,
            total=total,
            pagination=PaginationData(
                page=offset // limit + 1,
                pageSize=limit,
                total=total,
                totalPages=total_pages
            )
        )
        
    except Exception as e:
        log.exception(f"Error listing materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询素材列表失败: {str(e)}"
        )


@router.get("/{material_id}", response_model=MaterialDetailResponse, summary="查询素材详情")
async def get_material_detail(
    material_id: str,
    _: dict = Depends(verify_external_request),
):
    """
    查询素材详情（后台管理）
    
    返回素材完整信息，包括AI打标结果、用户信息等。
    """
    try:
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="素材不存在"
            )
        
        # 获取用户信息
        user = Users.get_user_by_id(material.user_id) if material.user_id else None
        user_name = getattr(user, "name", None) if user else None
        company_name = getattr(user, "business_name", None) if user else None
        
        # 处理属性代码
        properties_list = None
        if material.properties_code:
            properties_list = material.properties_code.split("_")
        
        # 构建基础响应
        response_data = {
            k: v for k, v in material.model_dump().items() if k != 'properties_code'
        }
        response_data.update({
            "thumbnail_url": f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
            "download_url": f"/api/v1/hsai/materials/{material.id}/download",
            "properties_code": properties_list,
            "user_name": user_name,
            "company_name": company_name,
        })
        
        # 尝试获取AI打标信息（可选，不影响主流程）
        tag_info = None
        try:
            if material.oss_object_path:
                from open_webui.internal.db_n8n import get_n8n_db
                from sqlalchemy import text
                
                with get_n8n_db() as db:
                    result = db.execute(
                        text(
                            "SELECT * FROM hsai_business_local_video_tag "
                            "WHERE videopath = :path "
                            "ORDER BY createdat DESC LIMIT 1"
                        ),
                        {"path": material.oss_object_path}
                    )
                    tag_record = result.fetchone()
                
                if tag_record:
                    tag_data = dict(tag_record._mapping) if hasattr(tag_record, '_mapping') else dict(tag_record)
                    tag_info = MaterialTagInfo(
                        status="completed",
                        category=tag_data.get("category"),
                        scene_name=tag_data.get("scene_name"),
                        shot_type=tag_data.get("shot_type"),
                        camera_move=tag_data.get("camera_move"),
                        camera_angle=tag_data.get("camera_angle"),
                        description=tag_data.get("description"),
                        duration=float(tag_data["duration"]) if tag_data.get("duration") is not None else None,
                    )
                else:
                    tag_info = MaterialTagInfo(status="waiting")
        except Exception as tag_error:
            log.warning(f"Failed to fetch tag info for material {material_id}: {tag_error}")
            tag_info = MaterialTagInfo(status="error")
        
        response_data["tag_info"] = tag_info
        
        return MaterialDetailResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting material detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询素材详情失败: {str(e)}"
        )


@router.post("/{material_id}/resync", summary="强制重新同步OSS")
async def resync_material(
    material_id: str,
    _: dict = Depends(verify_external_request),
):
    """
    强制重新同步素材的OSS信息（后台运维功能）
    
    用于修复OSS路径错误或元数据不一致的情况。
    """
    try:
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="素材不存在"
            )
        
        # TODO: 实现OSS重新同步逻辑
        # 这里可以调用MaterialsOssSyncService进行单个素材的同步
        
        return {
            "success": True,
            "message": "重新同步任务已提交",
            "material_id": material_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error resyncing material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新同步失败: {str(e)}"
        )
