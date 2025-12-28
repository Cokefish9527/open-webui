import logging
import uuid
from typing import List, Optional, Literal, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from open_webui.config_module import JWT_EXPIRES_IN
from open_webui.config import WEBUI_URL as WEBUI_URL_CONFIG
from open_webui.env import SRC_LOG_LEVELS
from open_webui.env import WEBUI_AUTH_COOKIE_SAME_SITE, WEBUI_AUTH_COOKIE_SECURE
from open_webui.models.auths import Auths
from open_webui.models.hsai_companies import Companies
from open_webui.models.social_accounts import SocialAccounts, SocialAccount
from open_webui.models.users import Users, UserModel
from open_webui.utils.auth import create_token, get_password_hash, get_verified_user
from open_webui.utils.hsai_oauth_handler import hsai_oauth_handler
from open_webui.utils.misc import parse_duration

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

router = APIRouter(
    # 统一由 main.py 以 prefix="/api/v1" 挂载，避免出现 /api/v1/api/v1 的重复前缀
    prefix="/hsai/social",
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


class TikTokSSOLoginResponse(BaseModel):
    authorization_url: str
    state: str


class TikTokSSOCallbackJSONResponse(BaseModel):
    token: str
    is_new_user: bool
    user: UserModel
    linked_social_account_id: Optional[int] = None


@router.get("/tiktok/sso/login", response_model=TikTokSSOLoginResponse)
async def tiktok_sso_login(request: Request):
    """
    TikTok SSO：生成 TikTok Login Kit 授权 URL（不要求 OwenAI 先登录）。

    回调后会在 open-webui 侧完成：
    - 查找是否存在已绑定的 social_accounts（open_id -> owner_user_id）
    - 若存在则登录该 OwenAI 用户
    - 若不存在则自动创建 OwenAI 用户（后续用户可在个人资料中修改信息）
    """
    # redirect_uri 需要与 TikTok 平台配置的 Redirect URL 完全一致。
    # 统一从配置读取 WEBUI_URL（例如：https://owen-ai.hsai.cc/）并拼接回调路径。
    base_url = (
        (WEBUI_URL_CONFIG.value or "")
        or str(getattr(getattr(request.app, "state", None), "config", None).WEBUI_URL or "")
        or str(request.base_url)
    ).rstrip("/")
    redirect_uri = f"{base_url}"

    data = hsai_oauth_handler.generate_oauth_url(
        platform_type="tiktok",
        redirect_uri=redirect_uri,
        user_id=None,
        company_id=None,
        purpose="sso",
    )
    return TikTokSSOLoginResponse(**data)


@router.get("/tiktok/sso/callback")
async def tiktok_sso_callback(
    request: Request,
    code: str,
    state: str,
    response_type: Literal["redirect", "json"] = "redirect",
):
    """
    TikTok SSO 回调：
    - 若该 TikTok open_id 已在 social_accounts 绑定（owner_user_id） -> 登录该用户
    - 否则创建新用户并登录

    response_type=redirect（默认）：302 到 `${WEBUI_URL}/auth#token=...`
    response_type=json：返回 JSON（用于移动端/自定义客户端）
    """
    try:
        result = hsai_oauth_handler.handle_tiktok_sso_callback(code=code, state=state)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail=f"TikTok SSO failed: {exc}")

    token_data: Dict[str, Any] = result.get("token_data") or {}
    user_info: Dict[str, Any] = result.get("user_info") or {}

    open_id = (
        user_info.get("open_id")
        or token_data.get("open_id")
        or token_data.get("openId")
        or token_data.get("open_id_v2")
    )
    if not open_id:
        raise HTTPException(status_code=400, detail="TikTok SSO missing open_id")

    linked_social_account_id: Optional[int] = None
    is_new_user = False

    # 1) 优先：若已有 TikTok 绑定账号（social_accounts.owner_user_id）则登录该 OwenAI 用户
    social = SocialAccounts.get_active_tiktok_account_by_open_id(open_id)
    user: Optional[UserModel] = None
    if social:
        linked_social_account_id = int(getattr(social, "id", 0) or 0) or None

        # 尽量刷新 token（不影响主流程）
        try:
            if token_data.get("access_token") and linked_social_account_id:
                SocialAccounts.update_token(
                    int(linked_social_account_id),
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    expires_in=token_data.get("expires_in"),
                    scope=token_data.get("scope"),
                    token_type=token_data.get("token_type"),
                )
        except Exception:  # pragma: no cover
            pass

        owner_id = getattr(social, "owner_user_id", None)
        if owner_id:
            user = Users.get_user_by_id(str(owner_id))

    # 2) 次选：按 oauth_sub 找用户（支持未做绑定的 SSO 注册用户）
    if not user:
        sub = f"tiktok:{open_id}"
        user = Users.get_user_by_oauth_sub(sub)

    # 3) 创建新用户
    if not user:
        is_new_user = True
        sub = f"tiktok:{open_id}"
        username = (user_info.get("display_name") or user_info.get("username") or "").strip()
        if not username:
            username = f"tiktok_{open_id[:8]}"

        # TikTok 不一定返回 email：使用可预测但唯一的占位邮箱，用户可在资料页后续修改
        email = f"tiktok+{open_id}@oauth.local"
        profile_image_url = (user_info.get("avatar_url") or "").strip() or "/user.png"

        created = Auths.insert_new_auth(
            email=email,
            password=get_password_hash(str(uuid.uuid4())),
            name=username,
            profile_image_url=profile_image_url,
            role="pending",
            oauth_sub=sub,
        )
        if not created:
            raise HTTPException(status_code=500, detail="Failed creating user for TikTok SSO")
        user = created

    # 4) 若存在 social_accounts 但缺 owner_user_id，则自动关联到该用户（避免后续无法“找回”绑定）
    if social and not getattr(social, "owner_user_id", None) and linked_social_account_id:
        try:
            SocialAccounts.set_owner_user_id(int(linked_social_account_id), user.id)
        except Exception:  # pragma: no cover
            pass

    # 5) 若 social_accounts 存在 company 归属，则尽量把 user.company_id 同步（不强制）
    if social and getattr(social, "company_id", None):
        try:
            company_id = str(getattr(social, "company_id"))
            update: Dict[str, Any] = {"company_id": company_id}
            company = Companies.get_company_by_id(company_id)
            if company and getattr(company, "name", None):
                update["business_name"] = getattr(company, "name")
            Users.update_user_by_id(user.id, update)
        except Exception:  # pragma: no cover
            pass

    jwt_token = create_token(
        data={"id": user.id},
        expires_delta=parse_duration(str(JWT_EXPIRES_IN)),
    )

    if response_type == "json":
        return TikTokSSOCallbackJSONResponse(
            token=jwt_token,
            is_new_user=is_new_user,
            user=UserModel.model_validate(user),
            linked_social_account_id=linked_social_account_id,
        )

    redirect_base_url = str(request.app.state.config.WEBUI_URL or request.base_url).rstrip("/")
    redirect_url = f"{redirect_base_url}/auth#token={jwt_token}"
    resp = RedirectResponse(url=redirect_url)
    resp.set_cookie(
        key="token",
        value=jwt_token,
        httponly=True,
        samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
        secure=WEBUI_AUTH_COOKIE_SECURE,
    )
    return resp


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
    # main.py 会以 prefix="/api/v1" 挂载本路由，因此回调路径是 /api/v1/hsai/social/...
    redirect_uri = f"{base_url}/api/v1/hsai/social/tiktok/callback"

    data = hsai_oauth_handler.generate_oauth_url(
        platform_type="tiktok",
        redirect_uri=redirect_uri,
        user_id=user.id,
        company_id=company_id,
        purpose="connect",
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
    try:
        result = hsai_oauth_handler.handle_oauth_callback(
            platform_type="tiktok",
            code=code,
            state=state,
        )
    except ValueError as exc:
        log.warning("TikTok OAuth callback rejected state=%s err=%s", state, exc)
        redirect_uri = request.app.state.config.WEBUI_URL or request.base_url
        return RedirectResponse(url=f"{str(redirect_uri).rstrip('/')}?tiktok_connected=0&tiktok_error=invalid_state")
    except Exception as exc:  # pylint: disable=broad-except
        log.exception("TikTok OAuth callback failed: %s", exc)
        redirect_uri = request.app.state.config.WEBUI_URL or request.base_url
        return RedirectResponse(url=f"{str(redirect_uri).rstrip('/')}?tiktok_connected=0&tiktok_error=server_error")

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
