import logging
import time
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from open_webui.models.hsai_materials import (
    HSAIMaterials,
    HSAIMaterialForm,
    HSAIMaterialResponse,
    PaginationData,
    PaginatedHSAIMaterialResponse
)

from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.storage.provider import Storage

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/materials", tags=["HSAI 素材管理 - 回收站"])

# Pydantic模型定义
class MoveToRecoveryRequest(BaseModel):
    """移入回收站请求模型"""
    reason: Optional[str] = Field(default=None, description="操作原因")


class RestoreRequest(BaseModel):
    """还原文件请求模型"""
    # 为了向后兼容，保留target_directory参数，但不使用它
    # 还原操作将自动使用original_directory字段记录的原始目录
    target_directory: Optional[str] = Field(default=None, description="目标目录（已弃用，保留兼容性）")


class PermanentDeleteRequest(BaseModel):
    """永久删除请求模型"""
    reason: Optional[str] = Field(default=None, description="删除原因")


class BatchOperationRequest(BaseModel):
    """批量操作请求模型"""
    operation: str = Field(description="操作类型 (restore 或 delete)")
    material_ids: List[str] = Field(description="素材ID列表")
    # 移除target_directory参数，还原操作将自动还原到原始目录


# 辅助函数
async def _log_file_operation(
    material_id: str,
    operation_type: str,
    source_path: str,
    operator_id: str,
    target_path: Optional[str] = None,
    details: Optional[dict] = None
):
    """
    记录文件操作日志
    
    Args:
        material_id: 素材ID
        operation_type: 操作类型
        source_path: 源路径
        operator_id: 操作人ID
        target_path: 目标路径（可选）
        details: 操作详情（可选）
    """
    # 这里应该将日志保存到数据库
    # 为简化实现，我们只记录到日志中
    log.info(f"File operation logged: material_id={material_id}, operation_type={operation_type}, "
             f"source_path={source_path}, target_path={target_path}, operator_id={operator_id}, details={details}")


############################
# 回收站管理接口
############################

@router.post("/{material_id}/move-to-recovery", response_model=HSAIMaterialResponse, summary="移入回收站（软删除）")
async def move_material_to_recovery(
    material_id: str,
    request: MoveToRecoveryRequest,
    user=Depends(get_verified_user)
):
    """
    将指定素材从原目录移动到回收站目录，在数据库中更新删除标志位和原目录信息，记录操作日志
    
    Args:
        material_id (str): 素材唯一标识符
        request (MoveToRecoveryRequest): 请求参数
        user: 已认证的用户对象
        
    Returns:
        HSAIMaterialResponse: 更新后的素材信息
    """
    try:
        # 获取素材信息
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        # 更新素材信息 - 修复软删除逻辑
        update_data = {
            "name": material.name,  # 保持原有名称
            "material_type": material.material_type,  # 保持原有类型
            "folder_id": None,  # 移入回收站时清空folder_id
            "file_path": material.file_path,  # 保持原有文件路径
            "file_size": material.file_size,  # 保持原有文件大小
            "file_hash": material.file_hash,  # 保持原有文件哈希
            "mime_type": material.mime_type,  # 保持原有MIME类型
            "is_deleted": True,
            "original_directory": material.folder_id,  # 记录原始folder_id用于还原
            "deleted_at": int(time.time()),
            "deleted_by": user.id  # 使用当前登录用户ID
        }
        
        updated_material = HSAIMaterials.update_material_by_id(material_id, HSAIMaterialForm(**update_data))
        if not updated_material:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to move material to recovery"
            )
        
        # 记录操作日志
        await _log_file_operation(
            material_id=material_id,
            operation_type="delete",
            source_path=material.file_path,
            target_path=f"recovery/{material_id}",
            operator_id=user.id,  # 使用当前登录用户ID
            details={"reason": request.reason} if request.reason else None
        )
        
        # 返回更新后的素材信息
        return HSAIMaterialResponse(
            **updated_material.model_dump(),
            thumbnail_url=f"/hsai/materials/{material_id}/thumbnail" if updated_material.material_type in ["image", "video"] else None,
            download_url=updated_material.file_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error moving material to recovery: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/recovery/{material_id}/restore", response_model=HSAIMaterialResponse, summary="还原文件")
async def restore_material(
    material_id: str,
    request: RestoreRequest = None,  # 保持兼容性，但不使用参数
    user=Depends(get_verified_user)
):
    """
    将回收站中的文件还原到原始目录，更新数据库记录，记录操作日志
    
    Args:
        material_id (str): 素材唯一标识符
        user: 已认证的用户对象
        
    Returns:
        HSAIMaterialResponse: 更新后的素材信息
    
    Note:
        还原操作将自动将素材还原到其原始目录（original_directory字段记录的位置）
    """
    try:
        # 获取素材信息
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        if not material.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Material is not in recovery"
            )
        
        if not material.original_directory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Original directory information is missing, cannot restore"
            )
        
        # 更新素材信息 - 修复还原逻辑
        update_data = {
            "name": material.name,  # 保持原有名称
            "material_type": material.material_type,  # 保持原有类型
            "folder_id": material.original_directory,  # 还原到原始目录
            "file_path": material.file_path,  # 保持文件路径不变
            "file_size": material.file_size,  # 保持原有文件大小
            "file_hash": material.file_hash,  # 保持原有文件哈希
            "mime_type": material.mime_type,  # 保持原有MIME类型
            "is_deleted": False,
            "original_directory": None,
            "deleted_at": None,
            "deleted_by": None
        }
        
        updated_material = HSAIMaterials.update_material_by_id(material_id, HSAIMaterialForm(**update_data))
        if not updated_material:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to restore material"
            )
        
        # 记录操作日志
        await _log_file_operation(
            material_id=material_id,
            operation_type="restore",
            source_path=f"recovery/{material_id}",
            target_path=updated_material.file_path,
            operator_id=user.id  # 使用当前登录用户ID
        )
        
        # 返回更新后的素材信息
        return HSAIMaterialResponse(
            **updated_material.model_dump(),
            thumbnail_url=f"/hsai/materials/{material_id}/thumbnail" if updated_material.material_type in ["image", "video"] else None,
            download_url=updated_material.file_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error restoring material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.delete("/{material_id}/permanent-delete", response_model=bool, summary="永久删除文件")
async def permanent_delete_material(
    material_id: str,
    request: PermanentDeleteRequest,
    user=Depends(get_verified_user)
):
    """
    根据素材ID在素材表中找到对应的记录，通过素材文件的位置信息确定需要删除的OSS文件
    （企业目录或回收站目录中的文件），彻底删除OSS文件和数据库记录，记录操作日志。
    此接口统一处理所有永久删除操作，客户端无需关心文件具体位置。
    
    Args:
        material_id (str): 素材唯一标识符
        request (PermanentDeleteRequest): 请求参数
        user: 已认证的用户对象
        
    Returns:
        bool: 删除成功返回True
    """
    try:
        # 获取素材信息
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        # 删除OSS文件
        try:
            Storage.delete_file(material.file_path)
        except Exception as e:
            log.warning(f"Failed to delete OSS file {material.file_path}: {e}")
        
        # 删除数据库记录
        result = HSAIMaterials.delete_material_by_id(material_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete material record"
            )
        
        # 记录操作日志
        await _log_file_operation(
            material_id=material_id,
            operation_type="permanent_delete",
            source_path=material.file_path,
            operator_id=user.id,  # 使用当前登录用户ID
            details={"reason": request.reason} if request.reason else None
        )
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error permanently deleting material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/recovery/list", response_model=PaginatedHSAIMaterialResponse, summary="获取回收站文件列表")
async def get_recovery_materials(
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    sort_by: str = Query("delete_time", description="排序字段（delete_time/name/size）"),
    order: str = Query("desc", description="排序方式（asc/desc）"),
    user=Depends(get_verified_user)
):
    """
    获取当前用户回收站中的文件列表
    
    Args:
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        sort_by (str): 排序字段（delete_time/name/size），默认delete_time
        order (str): 排序方式（asc/desc），默认desc
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAIMaterialResponse: 分页的回收站文件列表
        - data: 回收站文件列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        # 获取当前用户已删除的素材
        materials = HSAIMaterials.get_deleted_materials_by_user_id(
            user.id, 
            limit=ps, 
            offset=offset
        )
        
        # 获取总数
        total = HSAIMaterials.count_deleted_materials_by_user_id(user.id)
        
        # 转换为响应模型
        responses = []
        for material in materials:
            response = HSAIMaterialResponse(
                **material.model_dump(),
                upload_url=material.file_path,
                thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
                download_url=material.file_path
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
        
        return PaginatedHSAIMaterialResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting recovery materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/recovery/batch-operation", response_model=bool, summary="批量操作回收站文件")
async def batch_operation_recovery_materials(
    request: BatchOperationRequest,
    user=Depends(get_verified_user)
):
    """
    对回收站中的多个文件进行批量还原或删除操作
    
    Args:
        request (BatchOperationRequest): 请求参数
        user: 已认证的用户对象
        
    Returns:
        bool: 操作成功返回True
    """
    try:
        success_count = 0
        
        for material_id in request.material_ids:
            try:
                if request.operation == "restore":
                    # 还原操作 - 获取素材信息以检查original_directory
                    material = HSAIMaterials.get_material_by_id(material_id)
                    if not material or material.user_id != user.id:
                        log.warning(f"Material {material_id} not found or access denied")
                        continue
                    
                    if not material.is_deleted:
                        log.warning(f"Material {material_id} is not in recovery")
                        continue
                    
                    if not material.original_directory:
                        log.warning(f"Material {material_id} missing original directory information")
                        continue
                    
                    # 还原操作
                    update_data = {
                        "name": material.name,  # 保持原有名称
                        "material_type": material.material_type,  # 保持原有类型
                        "folder_id": material.folder_id,  # 保持原有folder_id
                        "file_size": material.file_size,  # 保持原有文件大小
                        "file_hash": material.file_hash,  # 保持原有文件哈希
                        "mime_type": material.mime_type,  # 保持原有MIME类型
                        "is_deleted": False,
                        "file_path": material.original_directory,  # 还原到原始目录
                        "original_directory": None,
                        "deleted_at": None,
                        "deleted_by": None
                    }
                    
                    result = HSAIMaterials.update_material_by_id(material_id, HSAIMaterialForm(**update_data))
                    if result:
                        success_count += 1
                        
                        # 记录操作日志
                        await _log_file_operation(
                            material_id=material_id,
                            operation_type="restore",
                            source_path=f"recovery/{material_id}",
                            target_path=material.original_directory,  # 使用原始目录
                            operator_id=user.id  # 使用当前登录用户ID
                        )
                        
                elif request.operation == "delete":
                    # 永久删除操作
                    material = HSAIMaterials.get_material_by_id(material_id)
                    if material and material.user_id == user.id:
                        # 删除OSS文件
                        try:
                            Storage.delete_file(material.file_path)
                        except Exception as e:
                            log.warning(f"Failed to delete OSS file {material.file_path}: {e}")
                        
                        # 删除数据库记录
                        if HSAIMaterials.delete_material_by_id(material_id):
                            success_count += 1
                            
                            # 记录操作日志
                            await _log_file_operation(
                                material_id=material_id,
                                operation_type="permanent_delete",
                                source_path=material.file_path,
                                operator_id=user.id  # 使用当前登录用户ID
                            )
                
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid operation: {request.operation}"
                    )
                    
            except Exception as e:
                log.warning(f"Error processing material {material_id}: {e}")
                continue
        
        return success_count == len(request.material_ids)
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error in batch operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )