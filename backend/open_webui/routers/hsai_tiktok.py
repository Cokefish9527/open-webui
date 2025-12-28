import logging
from typing import Literal, Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.social_accounts import SocialAccounts
from open_webui.models.hsai_tiktok_publish_log import (
    HSAITikTokPublishLogs,
    HSAITikTokPublishLogModel,
)
from open_webui.models.hsai_companies import Companies
from open_webui.utils.auth import get_verified_user
from open_webui.services.tiktok_publisher import tiktok_publisher

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

router = APIRouter(
    # 统一由 main.py 以 prefix="/api/v1" 挂载，避免出现 /api/v1/api/v1 的重复前缀
    prefix="/hsai/tiktok",
    tags=["HSAI TikTok 集成"],
)


class TikTokPublishForm(BaseModel):
    company_id: str = Field(description="业务公司 ID")
    project_id: Optional[str] = Field(default=None, description="项目 ID（可选，用于日志归档）")
    account_id: int = Field(description="social_accounts 主键 ID")
    video_url: str = Field(description="可被 TikTok PULL_FROM_URL 访问的 HTTPS 视频地址")
    mode: Literal["INBOX", "DIRECT"] = Field(default="INBOX", description="发布模式")
    caption: Optional[str] = Field(default=None, description="视频文案/描述")
    privacy_level: Optional[str] = Field(default="PRIVATE", description="DIRECT 模式下的视频可见性")


class TikTokPublishLogPagination(BaseModel):
    total: int = Field(description="满足条件的日志总数")
    limit: int = Field(description="每页条数")
    offset: int = Field(description="偏移量（起始条数）")


class TikTokPublishLogsResponse(BaseModel):
    data: List[HSAITikTokPublishLogModel]
    pagination: TikTokPublishLogPagination


@router.post("/publish")
async def publish_video(
    form: TikTokPublishForm,
    user=Depends(get_verified_user),
):
    """
    使用 TikTok Content Posting API 发布视频。
    - INBOX 模式：推送到 TikTok Inbox，由用户在 TikTok 内完成发布；
    - DIRECT 模式：直接发帖，未审核应用一般仅支持 PRIVATE。
    """
    account = SocialAccounts.get_account_by_id(form.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="TikTok account not found")

    if str(account.company_id) != str(form.company_id):
        # 简单防护，后续可替换为完整权限体系
        raise HTTPException(status_code=400, detail="Company/account mismatch")

    if not account.access_token:
        raise HTTPException(status_code=400, detail="TikTok account has no access token")

    open_id = account.open_id or account.account_id
    if not open_id:
        raise HTTPException(status_code=400, detail="TikTok account missing open_id")

    # 如有需要，先刷新 access_token
    # 这里只做简单判断，生产环境可按 token_expires_at 提前刷新。
    publish_status = "success"
    error_message: Optional[str] = None
    try:
        publish_result: Dict[str, Any]
        if form.mode == "INBOX":
            publish_result = tiktok_publisher.init_inbox_upload(
                access_token=account.access_token,
                open_id=open_id,
                video_url=form.video_url,
                caption=form.caption,
            )
        else:
            privacy = form.privacy_level or "PRIVATE"
            publish_result = tiktok_publisher.init_direct_post(
                access_token=account.access_token,
                open_id=open_id,
                video_url=form.video_url,
                caption=form.caption,
                privacy_level=privacy,
            )
    except Exception as exc:  # pylint: disable=broad-except
        publish_status = "failed"
        error_message = str(exc)
        log.error("TikTok publish failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"TikTok publish failed: {exc}")
    finally:
        # 无论成功与否，都记录一条发布日志；日志失败不影响主流程。
        try:
            HSAITikTokPublishLogs.record_publish(
                company_id=str(form.company_id),
                project_id=getattr(form, "project_id", None),
                social_account_id=form.account_id,
                mode=form.mode,
                video_url=form.video_url,
                caption=form.caption,
                status=publish_status,
                error_message=error_message,
            )
        except Exception as log_exc:  # pylint: disable=broad-except
            log.error("Failed recording TikTok publish log: %s", log_exc, exc_info=True)

    return {
        "status": "success",
        "mode": form.mode,
        "account_id": form.account_id,
        "company_id": form.company_id,
        "project_id": form.project_id,
        "result": publish_result,
    }


@router.get("/logs", response_model=TikTokPublishLogsResponse)
async def list_publish_logs(
    company_id: str = Query(..., description="业务公司 ID"),
    project_id: Optional[str] = Query(None, description="项目 ID（可选）"),
    mode: Optional[Literal["INBOX", "DIRECT"]] = Query(None, description="发布模式过滤"),
    status_filter: Optional[Literal["success", "failed"]] = Query(
        None, alias="status", description="发布状态过滤"
    ),
    limit: int = Query(50, ge=1, le=200, description="每页条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user=Depends(get_verified_user),
):
    """
    查询 TikTok 视频发布日志（公司 / 项目维度）。

    仅允许公司所有者或超级管理员访问指定 company_id 下的日志。
    """
    company = Companies.get_company_by_id(company_id)
    if not company or (company.owner_user_id != user.id and not getattr(user, "is_super_admin", False)):
        raise HTTPException(status_code=404, detail="Company not found")

    logs: List[HSAITikTokPublishLogModel] = HSAITikTokPublishLogs.list_logs(
        company_id=company_id,
        project_id=project_id,
        mode=mode,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    total = HSAITikTokPublishLogs.count_logs(
        company_id=company_id,
        project_id=project_id,
        mode=mode,
        status=status_filter,
    )

    return TikTokPublishLogsResponse(
        data=logs,
        pagination=TikTokPublishLogPagination(total=total, limit=limit, offset=offset),
    )
