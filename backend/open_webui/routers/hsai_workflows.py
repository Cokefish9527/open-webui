"""
HSAI工作流管理路由
提供工作流触发和管理接口
"""

import logging
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from open_webui.utils.auth import get_verified_user
from open_webui.services.workflow_orchestration_center import workflow_orchestration_center
from open_webui.services.workflow_meta_update_service import (
    DEFAULT_N8N_UPDATE_HOT_VIDEO_META_URL,
    DEFAULT_N8N_UPDATE_VIDEO_META_URL,
    post_json,
)
from open_webui.models.hsai_compose_traces import HSAIComposeTraces
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


class UpdateHotVideoMetaRequest(BaseModel):
    """对话过程中：用户修正主推广文案/脚本"""

    session_id: str = Field(description="n8n_workflow 会话 session_id（uuid）")
    hot_video_meta: Dict[str, Any] = Field(description="hot_video_meta（text/hashtags/videoscript 等）")


class UpdateVideoMetaRequest(BaseModel):
    """对话过程中：用户替换/确认候选素材"""

    session_id: str = Field(description="n8n_workflow 会话 session_id（uuid）")
    video_meta: Dict[str, Any] = Field(description="video_meta（bgm/tts/text/video 等）")


class WorkflowMetaUpdateResponse(BaseModel):
    success: bool = Field(description="是否成功")
    forwarded_status_code: Optional[int] = Field(default=None, description="转发到 n8n 的 HTTP 状态码")
    trace_id: Optional[str] = Field(default=None, description="若能映射到 compose trace，则返回 trace_id")


@router.post(
    "/update_hot_video_meta",
    response_model=WorkflowMetaUpdateResponse,
    summary="脚本文案修正",
)
async def update_hot_video_meta(
    request: UpdateHotVideoMetaRequest,
    user=Depends(get_verified_user),
):
    """
    对应 PDF 示例：`POST /webhook/update_hot_video_meta`（此处由 open-webui 接收并转发到 n8n webhook）。
    """
    try:
        trace_id = HSAIComposeTraces.find_trace_id_by_n8n_session_id(request.session_id)
        now = int(time.time())
        if trace_id:
            HSAIComposeTraces.upsert_step(
                trace_id,
                step_key="user_override_hot_video_meta",
                stage_name="user_override",
                status="updated",
                raw_stage_json={"session_id": request.session_id, "hot_video_meta": request.hot_video_meta},
                extracted_json=request.hot_video_meta,
                updated_at=now,
            )

        forwarded_status, _, _ = await post_json(
            DEFAULT_N8N_UPDATE_HOT_VIDEO_META_URL,
            {"session_id": request.session_id, "hot_video_meta": request.hot_video_meta},
        )

        if forwarded_status >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"n8n webhook forward failed: {forwarded_status}",
            )

        return WorkflowMetaUpdateResponse(
            success=True,
            forwarded_status_code=forwarded_status,
            trace_id=trace_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.error("update_hot_video_meta failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES.DEFAULT())


@router.post(
    "/update_video_meta",
    response_model=WorkflowMetaUpdateResponse,
    summary="素材候选替换",
)
async def update_video_meta(
    request: UpdateVideoMetaRequest,
    user=Depends(get_verified_user),
):
    """
    对应 PDF 示例：`POST /webhook/update_video_meta`（此处由 open-webui 接收并转发到 n8n webhook）。
    """
    try:
        trace_id = HSAIComposeTraces.find_trace_id_by_n8n_session_id(request.session_id)
        now = int(time.time())
        if trace_id:
            HSAIComposeTraces.upsert_step(
                trace_id,
                step_key="user_override_video_meta",
                stage_name="user_override",
                status="updated",
                raw_stage_json={"session_id": request.session_id, "video_meta": request.video_meta},
                extracted_json=request.video_meta,
                updated_at=now,
            )

        forwarded_status, _, _ = await post_json(
            DEFAULT_N8N_UPDATE_VIDEO_META_URL,
            {"session_id": request.session_id, "video_meta": request.video_meta},
        )

        if forwarded_status >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"n8n webhook forward failed: {forwarded_status}",
            )

        return WorkflowMetaUpdateResponse(
            success=True,
            forwarded_status_code=forwarded_status,
            trace_id=trace_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.error("update_video_meta failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES.DEFAULT())
