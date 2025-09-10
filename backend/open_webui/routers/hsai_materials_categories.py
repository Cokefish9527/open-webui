import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from open_webui.models.hsai_materials import (
    HSAIMaterialCategories,
    HSAIMaterialCategoryForm,
    HSAIMaterialCategoryResponse,
    PaginatedHSAIMaterialCategoryResponse,
    PaginationData
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/materials", tags=["HSAI 素材管理 - 分类"])

############################
# 素材分类管理
############################

@router.get("/categories", response_model=PaginatedHSAIMaterialCategoryResponse, summary="获取素材分类列表")
async def get_material_categories(
    category_type: Optional[str] = Query(None, description="分类类型过滤：scene(场景)、technique(手法)、property(属性)"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1)
):
    """
    获取素材分类列表（分页），可按分类类型过滤。
    
    Args:
        category_type (str, optional): 分类类型过滤
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        
    Returns:
        PaginatedHSAIMaterialCategoryResponse: 分页的分类列表
        - data: 分类列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        # 获取分类列表
        if category_type:
            categories = HSAIMaterialCategories.get_categories_by_type(category_type)
        else:
            categories = HSAIMaterialCategories.get_all_categories()
        
        # 应用分页（在内存中分页）
        total = len(categories)
        start_idx = offset
        end_idx = offset + ps
        paginated_categories = categories[start_idx:end_idx]
        
        # 转换为响应模型
        responses = []
        for category in paginated_categories:
            response = HSAIMaterialCategoryResponse(
                id=category.id,
                name=category.name,
                display_name=category.display_name,
                category_type=category.category_type,
                description=category.description,
                is_active=category.is_active,
                created_at=category.created_at,
                updated_at=category.updated_at
            )
            responses.append(response)
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIMaterialCategoryResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting material categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/categories", response_model=HSAIMaterialCategoryResponse, summary="创建素材分类")
async def create_material_category(
    form_data: HSAIMaterialCategoryForm
):
    """
    创建新的素材分类。
    
    Args:
        form_data (HSAIMaterialCategoryForm): 分类表单数据
        
    Returns:
        HSAIMaterialCategoryResponse: 创建的分类信息
    """
    try:
        # 验证分类类型
        valid_types = ["scene", "technique", "property"]
        if form_data.category_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category type. Must be one of: {', '.join(valid_types)}"
            )
        
        # 验证分类名称长度（控制在10个字符以内）
        if len(form_data.name) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name must be 10 characters or less"
            )
        
        category = HSAIMaterialCategories.insert_new_category(form_data)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create category"
            )
        
        # 转换为响应模型
        response = HSAIMaterialCategoryResponse(
            id=category.id,
            name=category.name,
            display_name=category.display_name,
            category_type=category.category_type,
            description=category.description,
            is_active=category.is_active,
            created_at=category.created_at,
            updated_at=category.updated_at
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating material category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.put("/categories/{category_id}", response_model=HSAIMaterialCategoryResponse, summary="更新素材分类")
async def update_material_category(
    category_id: str,
    form_data: HSAIMaterialCategoryForm
):
    """
    更新指定的素材分类。
    
    Args:
        category_id (str): 分类ID
        form_data (HSAIMaterialCategoryForm): 分类表单数据
        
    Returns:
        HSAIMaterialCategoryResponse: 更新的分类信息
    """
    try:
        # 验证分类名称长度（控制在10个字符以内）
        if form_data.name and len(form_data.name) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name must be 10 characters or less"
            )
        
        category = HSAIMaterialCategories.get_category_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        updated_category = HSAIMaterialCategories.update_category_by_id(category_id, form_data)
        if not updated_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update category"
            )
        
        # 转换为响应模型
        response = HSAIMaterialCategoryResponse(
            id=updated_category.id,
            name=updated_category.name,
            display_name=updated_category.display_name,
            category_type=updated_category.category_type,
            description=updated_category.description,
            is_active=updated_category.is_active,
            created_at=updated_category.created_at,
            updated_at=updated_category.updated_at
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating material category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.delete("/categories/{category_id}", response_model=bool, summary="删除素材分类")
async def delete_material_category(
    category_id: str
):
    """
    删除指定的素材分类（软删除）。
    
    Args:
        category_id (str): 分类ID
        
    Returns:
        bool: 删除成功返回True
    """
    try:
        category = HSAIMaterialCategories.get_category_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        result = HSAIMaterialCategories.delete_category_by_id(category_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error deleting material category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )