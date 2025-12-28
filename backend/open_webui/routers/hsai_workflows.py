"""
HSAI工作流管理路由
提供工作流触发和管理接口
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from open_webui.utils.auth import get_verified_user
from open_webui.services.workflow_orchestration_center import workflow_orchestration_center
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)

router = APIRouter(
    # 统一由 main.py 以 prefix="/api/v1" 挂载，避免出现 /api/v1/api/v1 的重复前缀
    prefix="/workflows",
    tags=["工作流管理"],
)

class WorkflowTriggerRequest(BaseModel):
    """工作流触发请求"""
    workflow_id: str = Field(description="工作流ID")
    user_input: str = Field(description="用户输入内容")
    entry_type: str = Field(default="chat", description="入口类型")
    session_id: Optional[str] = Field(default=None, description="会话ID")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="附加元数据")

class WorkflowTriggerResponse(BaseModel):
    """工作流触发响应"""
    success: bool = Field(description="是否成功")
    execution_id: Optional[str] = Field(description="执行ID")
    message: str = Field(description="响应消息")

@router.post("/trigger", response_model=WorkflowTriggerResponse, summary="触发工作流")
async def trigger_workflow(
    request: WorkflowTriggerRequest,
    user=Depends(get_verified_user)
):
    """
    触发指定的工作流执行
    """
    try:
        # 生成会话ID（如果未提供）
        session_id = request.session_id or f"session_{user.id}_{__import__('uuid').uuid4().hex[:8]}"
        
        # 构建上下文信息
        context = {
            "entry_type": request.entry_type,
            "business_name": "HSAI",
            "additional_data": request.metadata or {},
            "user_id": user.id
        }
        
        # 通过工作流编排中心处理请求
        execution_id = await workflow_orchestration_center.process_request(
            user_input=request.user_input,
            user_id=user.id,
            session_id=session_id,
            context=context
        )
        
        if execution_id:
            return WorkflowTriggerResponse(
                success=True,
                execution_id=execution_id,
                message="工作流已成功触发"
            )
        else:
            return WorkflowTriggerResponse(
                success=False,
                execution_id=None,
                message="工作流触发失败"
            )
            
    except Exception as e:
        log.error(f"触发工作流失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )
