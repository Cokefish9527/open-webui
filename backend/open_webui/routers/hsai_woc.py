"""
工作流编排中心管理路由
提供WOC的状态查询和管理接口
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from open_webui.utils.auth import get_verified_user
from open_webui.services.workflow_orchestration_center import workflow_orchestration_center
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/woc", tags=["工作流编排中心"])

class WOCStatusResponse(BaseModel):
    """WOC状态响应"""
    status: str = Field(description="WOC状态")
    active_executions: int = Field(description="活跃执行数")
    total_executions: int = Field(description="总执行数")
    success_rate: float = Field(description="成功率")
    average_duration: float = Field(description="平均执行时间")
    workflow_distribution: Dict[str, int] = Field(description="工作流分布")

class ExecutionStatusResponse(BaseModel):
    """执行状态响应"""
    execution_id: str = Field(description="执行ID")
    workflow_id: str = Field(description="工作流ID")
    user_id: str = Field(description="用户ID")
    session_id: str = Field(description="会话ID")
    status: str = Field(description="执行状态")
    progress: int = Field(description="执行进度")
    start_time: str = Field(description="开始时间")
    current_step: Optional[str] = Field(description="当前步骤")
    error_message: Optional[str] = Field(description="错误信息")

@router.get("/status", response_model=WOCStatusResponse, summary="获取WOC状态")
async def get_woc_status(user=Depends(get_verified_user)):
    """
    获取工作流编排中心的整体状态和统计信息
    """
    try:
        stats = workflow_orchestration_center.get_workflow_stats()
        
        return WOCStatusResponse(
            status="healthy",
            active_executions=stats.get("active_executions", 0),
            total_executions=stats.get("total_executions", 0),
            success_rate=stats.get("success_rate", 0.0),
            average_duration=stats.get("average_duration", 0.0),
            workflow_distribution=stats.get("workflow_distribution", {})
        )
        
    except Exception as e:
        log.error(f"获取WOC状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/execution/{execution_id}", response_model=ExecutionStatusResponse, summary="获取执行状态")
async def get_execution_status(
    execution_id: str,
    user=Depends(get_verified_user)
):
    """
    获取特定执行的详细状态信息
    """
    try:
        execution_data = await workflow_orchestration_center.get_execution_status(execution_id)
        
        if not execution_data:
            raise HTTPException(
                status_code=404,
                detail="执行记录不存在"
            )
            
        # 检查用户权限
        if execution_data.get("user_id") != user.id:
            raise HTTPException(
                status_code=403,
                detail="无权限访问此执行记录"
            )
            
        return ExecutionStatusResponse(
            execution_id=execution_data["execution_id"],
            workflow_id=execution_data["workflow_id"],
            user_id=execution_data["user_id"],
            session_id=execution_data["session_id"],
            status=execution_data["status"].value if hasattr(execution_data["status"], "value") else execution_data["status"],
            progress=execution_data.get("progress", 0),
            start_time=execution_data["start_time"].isoformat(),
            current_step=execution_data.get("current_step"),
            error_message=execution_data.get("error_message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"获取执行状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/execution/{execution_id}/cancel", summary="取消执行")
async def cancel_execution(
    execution_id: str,
    user=Depends(get_verified_user)
):
    """
    取消指定的工作流执行
    """
    try:
        # 首先检查执行是否存在以及用户权限
        execution_data = await workflow_orchestration_center.get_execution_status(execution_id)
        
        if not execution_data:
            raise HTTPException(
                status_code=404,
                detail="执行记录不存在"
            )
            
        if execution_data.get("user_id") != user.id:
            raise HTTPException(
                status_code=403,
                detail="无权限取消此执行"
            )
            
        # 取消执行
        success = await workflow_orchestration_center.cancel_execution(execution_id)
        
        if success:
            return {
                "success": True,
                "message": "执行已成功取消",
                "execution_id": execution_id
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="无法取消该执行，可能已完成或已失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"取消执行失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/executions/user", summary="获取用户执行列表")
async def get_user_executions(
    limit: int = Query(10, ge=1, le=100, description="返回记录数限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    status: Optional[str] = Query(None, description="状态过滤"),
    user=Depends(get_verified_user)
):
    """
    获取当前用户的工作流执行列表
    """
    try:
        all_executions = workflow_orchestration_center.state_manager.get_user_executions(user.id)
        
        # 状态过滤
        if status:
            filtered_executions = []
            for exec_data in all_executions:
                exec_status = exec_data["status"].value if hasattr(exec_data["status"], "value") else exec_data["status"]
                if exec_status == status:
                    filtered_executions.append(exec_data)
            all_executions = filtered_executions
        
        # 排序（最新的在前）
        all_executions.sort(key=lambda x: x["start_time"], reverse=True)
        
        # 分页
        total = len(all_executions)
        executions = all_executions[offset:offset + limit]
        
        # 格式化响应
        formatted_executions = []
        for execution in executions:
            exec_status = execution["status"].value if hasattr(execution["status"], "value") else execution["status"]
            formatted_executions.append({
                "execution_id": execution["execution_id"],
                "workflow_id": execution["workflow_id"],
                "status": exec_status,
                "progress": execution.get("progress", 0),
                "start_time": execution["start_time"].isoformat(),
                "end_time": execution.get("end_time").isoformat() if execution.get("end_time") else None,
                "current_step": execution.get("current_step"),
                "error_message": execution.get("error_message")
            })
        
        return {
            "total": total,
            "executions": formatted_executions,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
        
    except Exception as e:
        log.error(f"获取用户执行列表失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/cleanup", summary="清理旧执行记录")
async def cleanup_old_executions(
    max_age_hours: int = Query(24, ge=1, le=168, description="最大保留时间（小时）"),
    user=Depends(get_verified_user)
):
    """
    清理超过指定时间的执行记录
    仅管理员可用
    """
    try:
        # 检查管理员权限
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="仅管理员可执行清理操作"
            )
            
        # 执行清理
        initial_count = len(workflow_orchestration_center.state_manager.executions)
        workflow_orchestration_center.state_manager.cleanup_old_executions(max_age_hours)
        final_count = len(workflow_orchestration_center.state_manager.executions)
        
        cleaned_count = initial_count - final_count
        
        return {
            "success": True,
            "message": f"已清理 {cleaned_count} 个旧执行记录",
            "cleaned_count": cleaned_count,
            "remaining_count": final_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"清理旧执行记录失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/health", summary="WOC健康检查")
async def woc_health_check():
    """
    工作流编排中心健康检查
    """
    try:
        # 检查各组件状态
        router_status = "healthy" if workflow_orchestration_center.router_manager else "unhealthy"
        state_status = "healthy" if workflow_orchestration_center.state_manager else "unhealthy"
        comm_status = "healthy" if workflow_orchestration_center.communication_manager else "unhealthy"
        
        overall_status = "healthy" if all(status == "healthy" for status in [router_status, state_status, comm_status]) else "unhealthy"
        
        return {
            "status": overall_status,
            "components": {
                "router_manager": router_status,
                "state_manager": state_status,
                "communication_manager": comm_status
            },
            "timestamp": workflow_orchestration_center.state_manager.executions.__len__() if workflow_orchestration_center.state_manager else 0
        }
        
    except Exception as e:
        log.error(f"WOC健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }