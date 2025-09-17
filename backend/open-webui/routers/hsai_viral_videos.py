import logging
import time
import uuid
import aiohttp
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from open_webui.models.hsai_materials import HSAIMaterials, HSAIMaterialForm
from open_webui.models.hsai_tasks import HSAITasks, HSAITaskForm, HSAITaskType, HSAITaskStatus, HSAITaskUpdateForm
from open_webui.models.hsai_viral_videos import HSAIViralVideos, HSAIViralVideoStatus
from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.config.n8n_workflows import N8NWorkflowType, N8N_WORKFLOW_WEBHOOKS, get_workflow_config

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/viral-videos", tags=["HSAI 爆款视频"])

class ViralVideoData(BaseModel):
    """爆款视频数据模型"""
    video_url: str = Field(description="视频链接")
    title: str = Field(description="视频标题")
    description: Optional[str] = Field(default=None, description="视频描述")
    thumbnail_url: Optional[str] = Field(default=None, description="缩略图链接")
    duration: Optional[int] = Field(default=None, description="视频时长（秒）")
    platform: str = Field(description="平台名称（如抖音、快手等）")
    tags: Optional[List[str]] = Field(default=None, description="视频标签")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="其他元数据")
    # 移除了user_ids字段，因为现在是n8n将视频写入数据表，而不是直接指定用户

class ViralVideoResponse(BaseModel):
    """爆款视频响应模型"""
    id: str = Field(description="视频ID")
    video_url: str = Field(description="视频链接")
    title: str = Field(description="视频标题")
    created_at: int = Field(description="创建时间")

class ConfirmLearningRequest(BaseModel):
    """确认学习请求模型"""
    video_id: str = Field(description="视频ID")
    task_id: str = Field(description="任务ID")
    user_id: str = Field(description="用户ID")

class ConfirmLearningResponse(BaseModel):
    """确认学习响应模型"""
    success: bool = Field(description="是否成功")
    message: str = Field(description="响应消息")
    workflow_execution_id: Optional[str] = Field(default=None, description="工作流执行ID")

@router.post("/webhook", response_model=ViralVideoResponse, summary="接收n8n爆款视频数据")
async def receive_viral_video_data(video_data: ViralVideoData):
    """
    接收n8n工作流回调的爆款视频数据，并保存到数据库中等待处理
    """
    try:
        log.info(f"接收到爆款视频数据: {video_data.title}")
        
        # 保存视频数据到新的数据表中
        video_form_data = {
            "video_url": video_data.video_url,
            "title": video_data.title,
            "description": video_data.description,
            "thumbnail_url": video_data.thumbnail_url,
            "duration": video_data.duration,
            "platform": video_data.platform,
            "tags": video_data.tags,
            "metadata": video_data.metadata,
            "status": HSAIViralVideoStatus.PENDING,
            "is_learned": False
        }
        
        video = HSAIViralVideos.insert_new_video(video_form_data)
        if video:
            log.info(f"成功保存爆款视频数据: {video.id}")
            return ViralVideoResponse(
                id=video.id,
                video_url=video.video_url,
                title=video.title,
                created_at=video.created_at
            )
        else:
            log.error("保存爆款视频数据失败")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MESSAGES.DEFAULT()
            )
        
    except Exception as e:
        log.exception(f"处理爆款视频数据时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/confirm-learning", response_model=ConfirmLearningResponse, summary="确认学习并触发视频分析工作流")
async def confirm_learning(request: ConfirmLearningRequest):
    """
    用户确认学习后，调用n8n工作流进行视频分析拆解入库
    """
    try:
        log.info(f"用户 {request.user_id} 确认学习视频 {request.video_id}")
        
        # 1. 验证视频和任务是否存在
        video = HSAIViralVideos.get_video_by_id(request.video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="视频不存在"
            )
        
        task = HSAITasks.get_task_by_id(request.task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在"
            )
        
        # 2. 验证用户是否有权限确认学习
        if task.user_id != request.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限确认学习"
            )
        
        # 3. 更新视频状态为已学习
        material_id = ""
        if task.config and "material_id" in task.config:
            material_id = task.config["material_id"]
        
        updated_video = HSAIViralVideos.mark_video_as_learned(
            request.video_id, 
            request.task_id, 
            material_id
        )
        if not updated_video:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新视频状态失败"
            )
        
        # 4. 更新任务状态为进行中
        updated_task = HSAITasks.update_task_by_id(
            request.task_id, 
            HSAITaskUpdateForm(status=HSAITaskStatus.IN_PROGRESS)
        )
        if not updated_task:
            log.warning(f"更新任务 {request.task_id} 状态失败")
        
        # 5. 调用n8n工作流进行视频分析
        workflow_result = await _call_video_analysis_workflow(video, task)
        
        # 6. 更新任务状态为已完成
        completed_task = HSAITasks.update_task_by_id(
            request.task_id, 
            HSAITaskUpdateForm(
                status=HSAITaskStatus.COMPLETED,
                outputs=workflow_result
            )
        )
        
        return ConfirmLearningResponse(
            success=True,
            message="学习确认成功，已触发视频分析工作流",
            workflow_execution_id=workflow_result.get("execution_id") if workflow_result else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"确认学习时出错: {e}")
        # 更新任务状态为失败
        HSAITasks.update_task_by_id(
            request.task_id, 
            HSAITaskUpdateForm(
                status=HSAITaskStatus.FAILED,
                error_message=str(e)
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

async def _call_video_analysis_workflow(video, task) -> Dict[str, Any]:
    """
    调用n8n视频分析工作流
    """
    try:
        # 获取视频分析工作流配置
        workflow_config = get_workflow_config(N8NWorkflowType.VIRAL_LEARNING)
        webhook_url = N8N_WORKFLOW_WEBHOOKS[N8NWorkflowType.VIRAL_LEARNING]
        timeout = workflow_config["timeout"]
        
        # 准备工作流参数
        payload = {
            "trigger_type": "user_confirmed_learning",
            "video_data": {
                "id": video.id,
                "video_url": video.video_url,
                "title": video.title,
                "description": video.description,
                "thumbnail_url": video.thumbnail_url,
                "duration": video.duration,
                "platform": video.platform,
                "tags": video.tags,
                "metadata": video.metadata
            },
            "task_data": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "config": task.config,
                "inputs": task.inputs
            },
            "execution_time": time.time()
        }
        
        # 调用n8n工作流
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "OpenWebUI-HSAI/1.0",
                    "X-Trigger-Source": "user_confirmed_learning"
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    log.info(f"视频分析工作流调用成功: {result}")
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"n8n工作流调用失败 (状态码: {response.status}): {error_text}")
                    
    except Exception as e:
        log.exception(f"调用视频分析工作流时出错: {e}")
        raise Exception(f"调用视频分析工作流失败: {str(e)}")

@router.get("/test", summary="测试接口")
async def test_endpoint():
    """测试接口"""
    return {"message": "爆款视频回调接口正常工作"}

# 其他相关接口可以在这里添加