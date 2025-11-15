import logging
import aiohttp
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from open_webui.models.hsai_business_good_video_v1 import (
    HSAIBusinessGoodVideos,
    HSAIBusinessGoodVideoV1Model,
)
from open_webui.models.hsai_video_learning_status import (
    HSAIVideoLearningStatuses,
    HSAIVideoLearningStatusEnum,
)
from open_webui.models.hsai_video_learning_log import HSAIVideoLearningLogs
from open_webui.models.hsai_business_video_content_learned import (
    HSAIBusinessVideoContentLearneds,
    UpdateVideoContentLearnedRequest,
    HSAIBusinessVideoContentLearnedModel,
)
from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/video-learning", tags=["HSAI Video Learning"])


def _resolve_business_name(user) -> str:
    """Extract the business name from the authenticated user."""
    if hasattr(user, "business_name") and user.business_name:
        return user.business_name
    if hasattr(user, "info") and isinstance(user.info, dict) and user.info.get("business_name"):
        return str(user.info.get("business_name"))
    return "HSAI"


class VideoWithStatus(BaseModel):
    """Video entry enriched with learning status."""

    video: HSAIBusinessGoodVideoV1Model = Field(description="Video information")
    status: str = Field(
        description="Learning status: pending, learning, learned, abandoned",
        default=HSAIVideoLearningStatusEnum.PENDING.value,
    )


class PaginatedVideosResponse(BaseModel):
    """Paginated response model for video listings."""

    videos: List[VideoWithStatus] = Field(description="Video list")
    total: int = Field(description="Total number of videos")
    page: int = Field(description="Current page number")
    limit: int = Field(description="Page size")
    total_pages: int = Field(description="Total page count")


class GetVideosRequest(BaseModel):
    """Request model for listing videos."""

    page: int = Field(default=1, description="Page number", ge=1)
    limit: int = Field(default=50, description="Page size", ge=1, le=100)
    status_filter: Optional[str] = Field(
        default="all",
        description="Status filter: all, pending, learning, learned, abandoned",
    )


class StartLearningRequest(BaseModel):
    """Request model for starting a learning task."""

    video_id: int = Field(description="Video identifier")


class StartLearningResponse(BaseModel):
    """Response model for start learning action."""

    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Response message")
    status_id: Optional[int] = Field(default=None, description="Learning status record id")


class UpdateVideoContentLearnedResponse(BaseModel):
    """Response model for update video content learned action."""
    
    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Response message")
    updated_content: Optional[HSAIBusinessVideoContentLearnedModel] = Field(default=None, description="Updated video content")


class RevokeLearningRequest(BaseModel):
    """Request model for revoking learned videos."""

    learned_id: int = Field(description="Identifier of hsai_business_video_content_learned entry")
    reason: Optional[str] = Field(
        default=None,
        description="Optional reason for revoking the learning result",
        max_length=500,
    )


class RevokeLearningResponse(BaseModel):
    """Response model for revoke learning action."""

    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Response message")
    restored_status: str = Field(description="Resulting learning status after revocation")


def _normalize_status_filter(value: Optional[str]) -> str:
    valid = {"all", *[status.value for status in HSAIVideoLearningStatusEnum]}
    result = (value or "all").lower()
    if result not in valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"status_filter must be one of {sorted(valid)}",
        )
    return result


@router.get("/videos", response_model=PaginatedVideosResponse, summary="List videos with learning status")
async def get_pending_videos(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=100, description="Page size"),
    status_filter: Optional[str] = Query(
        default="all",
        description="Status filter: all, pending, learning, learned, abandoned",
    ),
    user=Depends(get_verified_user),
):
    """列出视频并合并当前业务租户的学习状态。"""
    try:
        normalized_filter = _normalize_status_filter(status_filter)
        business_name = _resolve_business_name(user)
        log.info(
            "List video learning status: page=%s limit=%s filter=%s business=%s",
            page,
            limit,
            normalized_filter,
            business_name,
        )

        skip = (page - 1) * limit

        total_videos = HSAIBusinessGoodVideos.get_total_count_with_status_filter(
            status_filter=normalized_filter,
            business_name=business_name,
        )

        videos = HSAIBusinessGoodVideos.get_videos_with_status_filter(
            skip=skip,
            limit=limit,
            status_filter=normalized_filter,
            business_name=business_name,
        )

        video_ids = [str(video.id) for video in videos]
        status_map = HSAIVideoLearningStatuses.get_status_map_for_business(business_name, video_ids)

        videos_with_status = []
        for video in videos:
            status_entry = status_map.get(str(video.id))
            status_value = status_entry.status if status_entry is not None else "pending"
            videos_with_status.append(VideoWithStatus(video=video, status=status_value))

        return PaginatedVideosResponse(
            videos=videos_with_status,
            total=total_videos,
            page=page,
            limit=limit,
            total_pages=(total_videos + limit - 1) // limit if limit else 1,
        )

    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Failed to list video learning entries: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        ) from exc


@router.post("/start-learning", response_model=StartLearningResponse, summary="Start learning a video")
async def start_video_learning(request: StartLearningRequest, user=Depends(get_verified_user)):
    """触发给定视频的学习工作流程。"""
    try:
        business_name = _resolve_business_name(user)
        log.info("Start video learning: video_id=%s business=%s", request.video_id, business_name)

        video = HSAIBusinessGoodVideos.get_video_by_id(request.video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )

        existing_status = HSAIVideoLearningStatuses.get_status_by_business_and_video(
            business_name,
            str(request.video_id),
        )
        if existing_status and existing_status.status == HSAIVideoLearningStatusEnum.LEARNING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video is already in learning status",
            )

        if existing_status:
            return StartLearningResponse(
                success=True,
                message="Learning status already exists",
                status_id=existing_status.id,
            )

        webhook_url = "https://webhook-n8n.hsai.cc/webhook/video2new_tts_text"
        video_payload: Dict[str, Any] = video.model_dump()
        # Convert all datetime fields to ISO format strings for JSON serialization
        datetime_fields = ("publishedtime", "createdat", "updatedat", "review_time")
        for field in datetime_fields:
            if field in video_payload and video_payload[field] and hasattr(video_payload[field], "isoformat"):
                video_payload[field] = video_payload[field].isoformat()
        video_payload["businessname"] = business_name
        video_payload["user_id"] = user.id

        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=video_payload,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "OpenWebUI-HSAI/1.0",
                },
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Invoke n8n workflow failed: {error_text}",
                    )

        status_form = {
            "business_name": business_name,
            "video_id": str(request.video_id),
            "status": HSAIVideoLearningStatusEnum.LEARNING.value,
        }
        new_status = HSAIVideoLearningStatuses.insert_new_status(status_form)

        return StartLearningResponse(
            success=True,
            message="Video learning started",
            status_id=new_status.id if new_status else None,
        )

    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Failed to start video learning: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        ) from exc


@router.put("/update-video-content", response_model=UpdateVideoContentLearnedResponse, summary="Update video content learned")
async def update_video_content_learned(request: UpdateVideoContentLearnedRequest, user=Depends(get_verified_user)):
    """更新视频内容学习信息。"""
    try:
        log.info("Update video content learned: id=%s", request.id)
        
        # 1. 验证视频学习内容是否存在
        video_content = HSAIBusinessVideoContentLearneds.get_video_content_by_id(request.id)
        if not video_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video content not found",
            )
        
        # 2. 验证用户是否有权限修改（通过business_name）
        business_name = _resolve_business_name(user)
        if video_content.businessname != business_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have permission to modify this video content",
            )
        
        # 3. 准备更新数据
        update_data = {}
        if request.videotranscript is not None:
            update_data["videotranscript"] = request.videotranscript
        if request.newttscontent is not None:
            update_data["newttscontent"] = request.newttscontent
            
        # 4. 执行更新操作
        updated_content = HSAIBusinessVideoContentLearneds.update_video_content(request.id, update_data)
        
        if not updated_content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update video content",
            )
        
        return UpdateVideoContentLearnedResponse(
            success=True,
            message="Video content updated successfully",
            updated_content=updated_content,
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Failed to update video content learned: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        ) from exc


@router.post(
    "/revoke-learning",
    response_model=RevokeLearningResponse,
    summary="Revoke learned video and reset status to pending",
)
async def revoke_video_learning(request: RevokeLearningRequest, user=Depends(get_verified_user)):
    """删除已学习的视频条目并恢复学习状态。"""
    try:
        business_name = _resolve_business_name(user)
        log.info(
            "Revoke learned video content: learned_id=%s business=%s",
            request.learned_id,
            business_name,
        )

        video_content = HSAIBusinessVideoContentLearneds.get_video_content_by_id(request.learned_id)
        if not video_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learned video not found",
            )

        if video_content.businessname != business_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have permission to revoke this video",
            )

        video_id = str(video_content.videoid)
        existing_status = HSAIVideoLearningStatuses.get_status_by_business_and_video(
            business_name=business_name,
            video_id=video_id,
        )

        deleted = HSAIBusinessVideoContentLearneds.delete_video_content(request.learned_id, business_name)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove learned video entry",
            )

        pending_status = HSAIVideoLearningStatuses.mark_pending(
            business_name=business_name,
            video_id=video_id,
        )

        HSAIVideoLearningLogs.record_status_change(
            business_name=business_name,
            video_id=video_id,
            from_status=existing_status.status if existing_status else None,
            to_status=HSAIVideoLearningStatusEnum.PENDING.value,
            reason=request.reason or "Manual revoke: reset to pending",
            operator=getattr(user, "id", "system"),
        )

        return RevokeLearningResponse(
            success=True,
            message="Learning revoked and status reset to pending",
            restored_status=HSAIVideoLearningStatusEnum.PENDING.value,
        )

    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Failed to revoke video learning: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        ) from exc


@router.get("/test", summary="视频学习路由健康检查")
async def test_endpoint():
    """简单的测试端点。"""
    return {"message": "Video learning API is operational"}
