import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.social_automation import (
    SocialAccountModel,
    SocialAutomationRunModel,
    SocialPostModel,
)
from open_webui.services.playwright_mcp_service import playwright_mcp_service
from open_webui.utils.auth import get_verified_user
from open_webui.utils.playwright_mcp_client import PlaywrightMCPError

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/social", tags=["社交账号自动化"])


def _tenant_id(user) -> str:
    return getattr(user, "organization_id", None) or getattr(user, "id")


class CreateAccountRequest(BaseModel):
    platform: str = Field(description="平台标识，例如 tiktok")
    handle: str = Field(description="账号用户名/唯一标识")
    display_name: Optional[str] = Field(default=None, description="账号昵称")
    encrypted_credentials_ref: Optional[str] = Field(
        default=None, description="加密凭证引用ID（留空时将自动生成模板文件）"
    )
    playwright_profile_path: Optional[str] = Field(
        default=None, description="浏览器配置目录（留空时自动生成目录）"
    )
    vpn_profile_id: Optional[str] = Field(default=None, description="VPN配置标识")
    auto_prepare: bool = Field(
        default=True, description="创建后自动生成凭证模板及目录，并提示交互式登录流程"
    )


class PrepareAccountRequest(BaseModel):
    interactive: bool = Field(
        default=True, description="是否进入交互式登录模式（需人工在浏览器中完成登录）"
    )
    interactive_timeout: Optional[int] = Field(
        default=None, description="交互式等待的超时时间（毫秒）。默认 300000（5 分钟）。"
    )


class TikTokCreatorRequest(BaseModel):
    target_handle: str = Field(description="目标创作者Handle/主页ID")


class TikTokVideoRequest(BaseModel):
    video_url: str = Field(description="TikTok视频链接")


class CreatePostRequest(BaseModel):
    account_id: str = Field(description="关联账号ID")
    title: Optional[str] = Field(default=None, description="视频标题")
    caption: Optional[str] = Field(default=None, description="视频描述/文案")
    media_assets: Optional[Dict[str, Any]] = Field(default=None, description="素材文件引用")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="自定义元数据")
    schedule_time: Optional[int] = Field(default=None, description="计划发布时间（Epoch秒）")
    campaign_id: Optional[str] = Field(default=None, description="关联活动ID")


class PublishResponse(BaseModel):
    run: SocialAutomationRunModel
    result: Dict[str, Any]


class MCPExecutionResponse(BaseModel):
    request_id: str
    status: str
    message: Optional[str] = None
    artifacts: Dict[str, Any] = Field(default_factory=dict)


@router.get("/accounts", response_model=List[SocialAccountModel], summary="列出当前租户的社交账号")
async def list_accounts(user=Depends(get_verified_user)):
    try:
        return playwright_mcp_service.list_accounts(_tenant_id(user))
    except Exception as exc:
        log.exception("获取账号列表失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post("/accounts", response_model=SocialAccountModel, summary="创建社交账号")
async def create_account(payload: CreateAccountRequest, user=Depends(get_verified_user)):
    try:
        return playwright_mcp_service.create_account(
            tenant_id=_tenant_id(user),
            platform=payload.platform,
            handle=payload.handle,
            display_name=payload.display_name,
            encrypted_credentials_ref=payload.encrypted_credentials_ref,
            playwright_profile_path=payload.playwright_profile_path,
            vpn_profile_id=payload.vpn_profile_id,
            created_by=user.id,
            auto_prepare=payload.auto_prepare,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        log.exception("创建社交账号失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.delete("/accounts/{account_id}", response_model=bool, summary="删除社交账号")
async def delete_account(account_id: str, user=Depends(get_verified_user)):
    try:
        deleted = playwright_mcp_service.delete_account(_tenant_id(user), account_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="账号不存在",
            )
        return True
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("删除社交账号失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post(
    "/accounts/{account_id}/prepare",
    response_model=MCPExecutionResponse,
    summary="准备账号（生成凭证模板并可选交互式登录）",
)
async def prepare_account(
    account_id: str,
    payload: PrepareAccountRequest = Body(default=PrepareAccountRequest()),
    user=Depends(get_verified_user),
):
    try:
        result = await playwright_mcp_service.prepare_account(
            account_id=account_id,
            initiated_by=user.id,
            interactive=payload.interactive,
            interactive_timeout=payload.interactive_timeout,
        )
        return MCPExecutionResponse(
            request_id=result.request_id,
            status=result.status,
            message=result.message,
            artifacts=result.artifacts or {},
        )
    except PlaywrightMCPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception as exc:
        log.exception("账号准备流程失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post(
    "/accounts/{account_id}/tiktok/login",
    response_model=MCPExecutionResponse,
    summary="触发TikTok自动登录",
)
async def tiktok_login(account_id: str, user=Depends(get_verified_user)):
    try:
        result = await playwright_mcp_service.ensure_tiktok_login(account_id, user.id)
        return MCPExecutionResponse(
            request_id=result.request_id,
            status=result.status,
            message=result.message,
            artifacts=result.artifacts or {},
        )
    except PlaywrightMCPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception as exc:
        log.exception("TikTok自动登录失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post(
    "/accounts/{account_id}/tiktok/creator",
    response_model=MCPExecutionResponse,
    summary="获取TikTok创作者信息",
)
async def tiktok_creator_info(
    account_id: str,
    payload: TikTokCreatorRequest,
    user=Depends(get_verified_user),
):
    try:
        result = await playwright_mcp_service.fetch_tiktok_creator_info(
            account_id, payload.target_handle, user.id
        )
        return MCPExecutionResponse(
            request_id=result.request_id,
            status=result.status,
            message=result.message,
            artifacts=result.artifacts or {},
        )
    except PlaywrightMCPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception as exc:
        log.exception("获取TikTok创作者信息失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post(
    "/accounts/{account_id}/tiktok/video",
    response_model=MCPExecutionResponse,
    summary="获取TikTok视频信息",
)
async def tiktok_video_info(
    account_id: str,
    payload: TikTokVideoRequest,
    user=Depends(get_verified_user),
):
    try:
        result = await playwright_mcp_service.fetch_tiktok_video_info(
            account_id, payload.video_url, user.id
        )
        return MCPExecutionResponse(
            request_id=result.request_id,
            status=result.status,
            message=result.message,
            artifacts=result.artifacts or {},
        )
    except PlaywrightMCPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception as exc:
        log.exception("获取TikTok视频信息失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post(
    "/posts",
    response_model=SocialPostModel,
    summary="创建社交发布任务",
)
async def create_post(payload: CreatePostRequest, user=Depends(get_verified_user)):
    try:
        return playwright_mcp_service.create_post(
            tenant_id=_tenant_id(user),
            account_id=payload.account_id,
            created_by=user.id,
            title=payload.title,
            caption=payload.caption,
            media_assets=payload.media_assets,
            metadata=payload.metadata,
            schedule_time=payload.schedule_time,
            campaign_id=payload.campaign_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        log.exception("创建发布任务失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.get(
    "/posts",
    response_model=List[SocialPostModel],
    summary="获取社交发布任务列表",
)
async def list_posts(account_id: Optional[str] = None, user=Depends(get_verified_user)):
    try:
        return playwright_mcp_service.list_posts(
            tenant_id=_tenant_id(user),
            account_id=account_id,
        )
    except Exception as exc:
        log.exception("获取发布任务列表失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post(
    "/posts/{post_id}/publish",
    response_model=PublishResponse,
    summary="发布TikTok视频",
)
async def publish_post(post_id: str, user=Depends(get_verified_user)):
    try:
        run, result = await playwright_mcp_service.publish_tiktok_video(post_id, user.id)
        return PublishResponse(run=run, result=result.artifacts or {})
    except PlaywrightMCPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        log.exception("发布TikTok视频失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

