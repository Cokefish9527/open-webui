import logging
import time
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from open_webui.models.hsai_materials import HSAIMaterials, HSAIMaterialForm
from open_webui.models.hsai_tasks import HSAITasks, HSAITaskForm, HSAITaskType, HSAITaskStatus
from open_webui.models.hsai_viral_videos import HSAIViralVideos, HSAIViralVideoStatus
from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

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

@router.get("/test", summary="测试接口")
async def test_endpoint():
    """测试接口"""
    return {"message": "爆款视频回调接口正常工作"}

# 其他相关接口可以在这里添加