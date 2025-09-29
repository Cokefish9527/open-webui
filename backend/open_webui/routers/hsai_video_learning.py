import logging
import aiohttp
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from open_webui.models.hsai_business_good_video_v1 import HSAIBusinessGoodVideos, HSAIBusinessGoodVideoV1Model
from open_webui.models.hsai_video_learning_status import HSAIVideoLearningStatuses, HSAIVideoLearningStatusModel, HSAIVideoLearningStatusEnum
from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/video-learning", tags=["HSAI 视频学习"])

class VideoWithStatus(BaseModel):
    """包含学习状态的视频模型"""
    video: HSAIBusinessGoodVideoV1Model = Field(description="Video information")
    status: str = Field(description="Learning status: pending, learning, learned, abandoned", default="pending")

class PaginatedVideosResponse(BaseModel):
    """分页视频响应模型"""
    videos: List[VideoWithStatus] = Field(description="视频列表")
    total: int = Field(description="视频总数")
    page: int = Field(description="当前页码")
    limit: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")

class GetVideosRequest(BaseModel):
    """获取视频请求模型"""
    page: int = Field(default=1, description="页码", ge=1)
    limit: int = Field(default=50, description="每页数量", ge=1, le=100)
    status_filter: Optional[str] = Field(default="all", description="状态筛选: all(全部), pending(待学习), learning(学习中), learned(已学习), abandoned(已放弃)")

class StartLearningRequest(BaseModel):
    """开始学习请求模型"""
    video_id: int = Field(description="视频ID")

class StartLearningResponse(BaseModel):
    """开始学习响应模型"""
    success: bool = Field(description="是否成功")
    message: str = Field(description="响应消息")
    status_id: Optional[int] = Field(default=None, description="学习状态记录ID")

@router.get("/videos", response_model=PaginatedVideosResponse, summary="获取视频库数据")
async def get_pending_videos(
    page: int = Query(default=1, ge=1, description="页码"),
    limit: int = Query(default=50, ge=1, le=100, description="每页数量"),
    status_filter: Optional[str] = Query(default="all", description="状态筛选: all(全部), pending(待学习), learning(学习中), learned(已学习), abandoned(已放弃)")
):
    """
    分页获取视频库数据，支持按学习状态筛选
    默认获取全部视频数据
    """
    try:
        log.info(f"获取待学习视频: page={page}, limit={limit}, status_filter={status_filter}")
        
        # 计算偏移量
        skip = (page - 1) * limit
        
        # 获取视频总数
        total_videos = HSAIBusinessGoodVideos.get_total_count()
        
        # 获取视频列表
        videos = HSAIBusinessGoodVideos.get_videos(skip=skip, limit=limit)
        
        # 为每个视频添加学习状态
        videos_with_status = []
        for video in videos:
            # 获取视频的学习状态
            learning_status = HSAIVideoLearningStatuses.get_status_by_video_id(str(video.id))
            
            # 确定最终状态
            final_status = "pending"  # 默认状态（待学习）
            if learning_status:
                final_status = learning_status.status
            
            # 如果有筛选条件，检查是否匹配
            if status_filter != "all":
                if status_filter == "pending" and final_status != "pending":
                    continue
                elif status_filter != "pending" and final_status != status_filter:
                    continue
            
            videos_with_status.append(VideoWithStatus(
                video=video,
                status=final_status
            ))
        
        # 如果有筛选，需要重新计算总数
        if status_filter != "all":
            total_videos = len(videos_with_status)
        
        return PaginatedVideosResponse(
            videos=videos_with_status,
            total=total_videos,
            page=page,
            limit=limit,
            total_pages=(total_videos + limit - 1) // limit
        )
        
    except Exception as e:
        log.exception(f"获取待学习视频时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/start-learning", response_model=StartLearningResponse, summary="开始视频学习")
async def start_video_learning(request: StartLearningRequest, user=Depends(get_verified_user)):
    """开始视频学习，调用n8n工作流进行视频分析"""
    try:
        # 从用户信息中获取business_name
        business_name = 'HSAI'
        if hasattr(user, 'info') and user.info and isinstance(user.info, dict):
            business_name = user.info.get('business_name', 'HSAI')
        log.info(f"从用户信息中获取business_name: {business_name}")
        log.info(f"开始视频学习: video_id={request.video_id}, business_name={business_name}")
        
        # 1. 获取视频数据
        video = HSAIBusinessGoodVideos.get_video_by_id(request.video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="视频不存在"
            )
        
        # 2. 检查是否已存在相同business_name和video_id的学习状态记录
        existing_status = HSAIVideoLearningStatuses.get_status_by_business_and_video(
            business_name, str(request.video_id)
        )
        
        if existing_status:
            # 如果已存在记录，检查状态是否为学习中
            if existing_status.status == HSAIVideoLearningStatusEnum.LEARNING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="视频已在学习中"
                )
            
            # 如果状态不是学习中，可以更新状态
            # 这里我们选择不更新，而是返回已存在的记录
            return StartLearningResponse(
                success=True,
                message="已存在学习记录",
                status_id=existing_status.id
            )
        
        # 3. 调用n8n工作流
        webhook_url = "https://webhook-n8n.hsai.cc/webhook/video2new_tts_text"
        # 将视频数据转换为字典，并处理datetime对象使其可JSON序列化
        video_dict = video.model_dump()
        # 处理所有datetime字段，转换为ISO格式字符串
        datetime_fields = ['publishedtime', 'createdat', 'updatedat']
        for field in datetime_fields:
            if field in video_dict and video_dict[field]:
                if hasattr(video_dict[field], 'isoformat'):
                    video_dict[field] = video_dict[field].isoformat()
        
        # 使用businessname字段填充用户的公司名称
        video_dict['businessname'] = business_name
        video_dict['user_id'] = user.id
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=video_dict,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "OpenWebUI-HSAI/1.0"
                }
            ) as response:
                if response.status == 200:
                    # 4. 只有在webhook请求成功时，才向学习状态表新增一条学习中状态的数据
                    status_form = {
                        "business_name": business_name,
                        "video_id": str(request.video_id),
                        "status": HSAIVideoLearningStatusEnum.LEARNING
                    }
                    
                    new_status = HSAIVideoLearningStatuses.insert_new_status(status_form)
                    
                    return StartLearningResponse(
                        success=True,
                        message="已成功启动视频学习",
                        status_id=new_status.id if new_status else None
                    )
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"调用n8n工作流失败: {error_text}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"开始视频学习时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/test", summary="测试接口")
async def test_endpoint():
    """测试接口"""
    return {"message": "视频学习接口正常工作"}