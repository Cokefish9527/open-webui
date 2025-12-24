import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.social_accounts import SocialAccounts, SocialAccount
from open_webui.utils.auth import get_verified_user
from open_webui.utils.hsai_oauth_handler import hsai_oauth_handler

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

router = APIRouter(
    prefix="/api/v1/hsai/social",
    tags=["HSAI 社交集成"],
)


class TikTokAccountResponse(BaseModel):
    id: int = Field(description="social_accounts 主键 ID")
    company_id: str
    platform: str
    account_name: str
    account_id: str
    account_url: Optional[str] = None


class TikTokUnlinkForm(BaseModel):
    account_id: int


@router.get("/tiktok/login")
async def tiktok_login(
    request: Request,
    company_id: Optional[str] = None,
    user=Depends(get_verified_user),
):
    """
    生成 TikTok Login Kit 授权地址。
    """
    base_url = request.app.state.config.WEBUI_URL.rstrip("/")
    redirect_uri = f"{base_url}/api/v1/hsai/social/tiktok/callback"

    data = hsai_oauth_handler.generate_oauth_url(
        platform_type="tiktok",
        redirect_uri=redirect_uri,
        user_id=user.id,
        company_id=company_id,
    )
    return data


@router.get("/tiktok/callback")
async def tiktok_callback(
    request: Request,
    code: str,
    state: str,
):
    """
    TikTok OAuth 回调。完成 token 交换与账号落库后，重定向回前端。
    """
    result = hsai_oauth_handler.handle_oauth_callback(
        platform_type="tiktok",
        code=code,
        state=state,
    )
    redirect_uri = result.get("redirect_uri") or request.app.state.config.WEBUI_URL
    # 在前端可通过该 query 标识绑定成功并刷新列表
    return RedirectResponse(url=f"{redirect_uri.rstrip('/')}?tiktok_connected=1")


@router.get("/tiktok/accounts", response_model=List[TikTokAccountResponse])
async def list_tiktok_accounts(
    company_id: str,
    user=Depends(get_verified_user),
):
    """
    列出指定公司的 TikTok 账号列表（仅返回基础信息，不包含 token）。
    """
    # TODO: 可根据 user 与 company_id 做权限校验
    accounts = SocialAccounts.get_accounts_by_company(company_id, platform="tiktok")
    results: List[TikTokAccountResponse] = []
    for acc in accounts:
        if not isinstance(acc, SocialAccount):
            continue
        results.append(
            TikTokAccountResponse(
                id=acc.id,
                company_id=acc.company_id,
                platform=acc.platform,
                account_name=acc.account_name,
                account_id=acc.account_id,
                account_url=acc.account_url,
            )
        )
    return results


@router.post("/tiktok/unlink")
async def unlink_tiktok_account(
    form: TikTokUnlinkForm,
    user=Depends(get_verified_user),
):
    """
    将 TikTok 账号标记为 disabled，用于“解绑”。
    """
    account = SocialAccounts.get_account_by_id(form.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # TODO: 可根据 account.company_id 与 user 权限做校验
    from open_webui.internal.db import get_db

    with get_db() as db:
        try:
            account.status = "disabled"
            account.updated_at = account.updated_at or account.created_at
            db.add(account)
            db.commit()
        except Exception as exc:  # pylint: disable=broad-except
            log.error("Failed disabling TikTok account %s: %s", form.account_id, exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to unlink account")

    return {"status": True}

