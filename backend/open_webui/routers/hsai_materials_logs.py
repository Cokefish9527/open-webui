import logging
import time
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from open_webui.models.hsai_materials import (
    HSAIFileOperationLogForm,
    HSAIFileOperationLogResponse,
    HSAIFileOperationLogs,
    PaginationData,
    PaginatedHSAIFileOperationLogResponse
)

from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/materials", tags=["HSAI 素材管理 - 日志"])

# Pydantic模型定义
class FileOperationLogForm(BaseModel):
    """文件操作日志表单模型"""
    material_id: str = Field(description="素材唯一标识符")
    operation_type: str = Field(description="操作类型")
    source_path: str = Field(description="源文件路径")
    target_path: Optional[str] = Field(default=None, description="目标文件路径")
    operation_time: int = Field(description="操作时间")
    details: Optional[dict] = Field(default=None, description="操作详情")


############################
# 文件操作日志接口
############################

@router.post("/logs", response_model=HSAIFileOperationLogResponse, summary="记录文件操作日志")
async def log_file_operation(
    form_data: FileOperationLogForm,
    user=Depends(get_verified_user)
):
    """
    记录文件操作日志
    
    Args:
        form_data (FileOperationLogForm): 日志表单数据
        user: 已认证的用户对象
        
    Returns:
        HSAIFileOperationLogResponse: 创建的日志信息
    """
    try:
        # 转换表单数据为数据库模型，并添加当前用户ID
        form_data_dict = form_data.model_dump()
        form_data_dict["operator_id"] = user.id  # 使用当前登录用户ID
        hsai_form_data = HSAIFileOperationLogForm(**form_data_dict)
        
        # 创建日志记录
        log_entry = HSAIFileOperationLogs.insert_new_log(hsai_form_data)
        if not log_entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create log entry"
            )
        
        return HSAIFileOperationLogResponse(**log_entry.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error logging file operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/logs", response_model=PaginatedHSAIFileOperationLogResponse, summary="查询文件操作日志")
async def get_file_operation_logs(
    material_id: Optional[str] = Query(None, description="素材唯一标识符"),
    enterprise_id: Optional[str] = Query(None, description="企业ID"),
    operation_type: Optional[str] = Query(None, description="操作类型"),
    operator_id: Optional[str] = Query(None, description="操作人ID"),
    start_time: Optional[int] = Query(None, description="查询起始时间"),
    end_time: Optional[int] = Query(None, description="查询结束时间"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    查询文件操作日志（分页）
    
    Args:
        material_id (str, optional): 素材唯一标识符
        enterprise_id (str, optional): 企业ID
        operation_type (str, optional): 操作类型
        operator_id (str, optional): 操作人ID
        start_time (int, optional): 查询起始时间
        end_time (int, optional): 查询结束时间
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAIFileOperationLogResponse: 分页的文件操作日志列表
        - data: 日志列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        # 获取日志列表
        logs = HSAIFileOperationLogs.get_logs(
            material_id=material_id,
            enterprise_id=enterprise_id,
            operation_type=operation_type,
            operator_id=operator_id,
            start_time=start_time,
            end_time=end_time,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = HSAIFileOperationLogs.get_logs_count(
            material_id=material_id,
            enterprise_id=enterprise_id,
            operation_type=operation_type,
            operator_id=operator_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # 转换为响应模型
        responses = [HSAIFileOperationLogResponse(**log.model_dump()) for log in logs]
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIFileOperationLogResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting file operation logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/{material_id}/history", response_model=PaginatedHSAIFileOperationLogResponse, summary="获取文件操作历史")
async def get_material_history(
    material_id: str,
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取指定文件的所有操作历史记录（分页）
    
    Args:
        material_id (str): 素材唯一标识符
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAIFileOperationLogResponse: 分页的文件操作历史记录列表
        - data: 历史记录列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        # 获取指定素材的日志列表
        logs = HSAIFileOperationLogs.get_logs(
            material_id=material_id,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = HSAIFileOperationLogs.get_logs_count(material_id=material_id)
        
        # 转换为响应模型
        responses = [HSAIFileOperationLogResponse(**log.model_dump()) for log in logs]
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIFileOperationLogResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting material history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )
