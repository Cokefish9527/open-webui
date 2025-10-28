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
        default="pending",
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


def _normalize_status_filter(value: Optional[str]) -> str:
    valid = {"all", "pending", "learning", "learned", "abandoned"}
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
    """List videos and merge learning status under the current business tenant."""
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

        videos_with_status = [
            VideoWithStatus(
                video=video,
                status=status_map.get(str(video.id)).status if status_map.get(str(video.id)) else "pending",
            )
            for video in videos
        ]

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
    """Trigger the learning workflow for a given video."""
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
        for field in ("publishedtime", "createdat", "updatedat"):
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


@router.get("/test", summary="Health check for video learning router")
async def test_endpoint():
    """Simple test endpoint."""
    return {"message": "Video learning API is operational"}
