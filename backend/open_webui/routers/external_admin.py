import logging
import os
import time
from collections import defaultdict, deque
from secrets import token_urlsafe
from threading import Lock
from typing import Optional, List, Deque, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from open_webui.models.users import Users, UserModel, UserListResponse
from open_webui.models.hsai_companies import (
    Companies,
    CompanyForm,
    CompanyUpdateForm,
    CompanyResponse,
    PaginatedCompanyResponse,
    PaginationData as CompanyPaginationData,
)
from open_webui.models.hsai_projects import (
    HSAIProjects,
    HSAIProjectForm,
    HSAIProjectUpdateForm,
    HSAIProjectResponse,
    PaginatedHSAIProjectResponse,
    PaginationData as ProjectPaginationData,
)
from open_webui.models.hsai_blueprint_progress import (
    HSAIBlueprintProgressTable,
    HSAIBlueprintProgressModel,
    HSAIBlueprintProgressHistoryModel,
    BlueprintProgressState,
)
from open_webui.models.social_accounts import SocialAccounts
from open_webui.models.hsai_tiktok_publish_log import HSAITikTokPublishLogs
from open_webui.models.hsai_compose_traces import (
    ComposeTraceCreateForm,
    HSAIComposeTraces,
    HSAIComposeTraceModel,
    HSAIComposeStepModel,
    HSAIComposeArtifactModel,
)
from open_webui.services.compose_trace_sync_service import sync_trace_once
from open_webui.models.auths import (
    Auths,
    AddUserForm,
    ExternalAdminUserUpdateForm,
)
from open_webui.config import ENABLE_CUSTOMER_PERMISSION_API
from open_webui.utils.auth import get_password_hash
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.external_admin_tokens import ExternalAdminTokens
from open_webui.services.enterprise_provisioning import provision_enterprise_membership
from open_webui.services.customer_permissions import customer_permissions_service

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("CONFIG", "INFO"))

EXTERNAL_ADMIN_IP_WHITELIST = [
    ip.strip() for ip in os.environ.get("EXTERNAL_ADMIN_IP_WHITELIST", "").split(",") if ip.strip()
]

EXTERNAL_ADMIN_CLIENT_ID = os.environ.get("EXTERNAL_ADMIN_CLIENT_ID", "external-admin")
EXTERNAL_ADMIN_CLIENT_SECRET = os.environ.get("EXTERNAL_ADMIN_CLIENT_SECRET")
EXTERNAL_ADMIN_CLIENT_SECRET_ROLLOVER = os.environ.get("EXTERNAL_ADMIN_CLIENT_SECRET_ROLLOVER")
EXTERNAL_ADMIN_TOKEN_TTL_SECONDS = int(os.environ.get("EXTERNAL_ADMIN_TOKEN_TTL_SECONDS", "900"))

_raw_allowed_scopes = os.environ.get("EXTERNAL_ADMIN_ALLOWED_SCOPES", "")
EXTERNAL_ADMIN_ALLOWED_SCOPES = [scope.strip() for scope in _raw_allowed_scopes.split() if scope.strip()]

EXTERNAL_ADMIN_RATE_LIMIT_PER_MIN = int(os.environ.get("EXTERNAL_ADMIN_RATE_LIMIT_PER_MIN", "60"))
_RATE_LIMIT_WINDOW_SECONDS = 60
_rate_lock = Lock()
_rate_limit_state: Dict[str, Deque[float]] = defaultdict(deque)

_auth_bypass_raw = os.environ.get("EXTERNAL_ADMIN_AUTH_BYPASS", "false").strip().lower()
EXTERNAL_ADMIN_AUTH_BYPASS = _auth_bypass_raw in {"1", "true", "yes", "on"}
_AUTH_BYPASS_WARNING_EMITTED = False


def _parse_required_tiktok_accounts(raw: Optional[str]) -> Optional[int]:
    """从蓝图配置的 required_tiktok_accounts 字段中抽取整数数量."""
    if not raw:
        return None
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if not digits:
        return None
    try:
        value = int(digits)
        return value if value >= 0 else None
    except ValueError:
        return None


def _build_project_response_with_tiktok(project) -> HSAIProjectResponse:
    """在基础项目信息上补充 TikTok 账号矩阵指标."""
    required_accounts: Optional[int] = None
    active_accounts: Optional[int] = None

    try:
        progress = HSAIBlueprintProgressTable.get_by_project(project.id)
        if progress and progress.required_tiktok_accounts:
            required_accounts = _parse_required_tiktok_accounts(
                progress.required_tiktok_accounts
            )
    except Exception:  # pragma: no cover - 监控即可
        required_accounts = None

    try:
        if getattr(project, "company_id", None):
            active_accounts = SocialAccounts.count_active_accounts(
                project.company_id,
                platform="tiktok",
            )
    except Exception:  # pragma: no cover - 监控即可
        active_accounts = None

    payload = project.model_dump()
    payload["tiktok_required_accounts"] = required_accounts
    payload["tiktok_active_accounts"] = active_accounts
    return HSAIProjectResponse(**payload)


class TikTokProjectStatsResponse(BaseModel):
    project_id: str = Field(description="项目 ID")
    company_id: str = Field(description="公司 ID")
    required_accounts: int = Field(description="该项目蓝图要求的 TikTok 账号数量")
    active_accounts: int = Field(description="该项目所属公司已绑定的 TikTok active 账号数量")
    last_publish_at: Optional[int] = Field(default=None, description="该项目最近一次成功发布的时间戳（秒）")
    publish_last_7d_total: int = Field(description="近 7 天成功发布总数")
    publish_last_7d_inbox: int = Field(description="近 7 天成功发布（INBOX）数量")
    publish_last_7d_direct: int = Field(description="近 7 天成功发布（DIRECT）数量")


class BlueprintProgressResponse(BaseModel):
    id: str = Field(description="蓝图进度 ID")
    project_id: str = Field(description="项目 ID")
    blueprint_version: str = Field(description="蓝图版本")
    execution_duration_days: Optional[str] = Field(default=None, description="执行周期天数（原始字符串）")
    planned_total_posts: Optional[str] = Field(default=None, description="计划总帖子数（原始字符串）")
    posting_frequency: Optional[str] = Field(default=None, description="发帖频率（原始字符串）")
    required_tiktok_accounts: Optional[str] = Field(default=None, description="所需 TikTok 账号数（原始字符串）")
    summary_md: Optional[str] = Field(default=None, description="战略蓝图 Markdown（摘要/正文）")
    blueprint_raw: Optional[str] = Field(default=None, description="战略蓝图原始内容（通常同 summary_md）")
    latest_digest: Optional[Dict] = Field(default=None, description="最近一次同步摘要信息")
    progress_state: BlueprintProgressState = Field(description="蓝图进度状态")
    daily_cycle_config: Optional[Dict] = Field(default=None, description="每日周期配置")
    info_collection_processed: bool = Field(description="是否已处理信息收集完成状态")
    last_synced_at: int = Field(description="最后同步时间戳（秒）")
    created_at: int = Field(description="创建时间戳（秒）")
    updated_at: int = Field(description="更新时间戳（秒）")

    @classmethod
    def from_model(cls, progress: HSAIBlueprintProgressModel) -> "BlueprintProgressResponse":
        return cls(**progress.model_dump())


class BlueprintHistoryEntry(BaseModel):
    id: str = Field(description="历史记录 ID")
    progress_id: str = Field(description="蓝图进度 ID")
    operation: str = Field(description="操作类型（INSERT/UPDATE/...）")
    operator_id: Optional[str] = Field(default=None, description="操作者 ID（可空）")
    changes_json: Optional[Dict] = Field(default=None, description="变更前后快照（可空）")
    snapshot_md: Optional[str] = Field(default=None, description="当时的蓝图内容快照（可空）")
    created_at: int = Field(description="创建时间戳（秒）")

    @classmethod
    def from_model(
        cls, history: HSAIBlueprintProgressHistoryModel
    ) -> "BlueprintHistoryEntry":
        return cls(**history.model_dump())


class ProjectBlueprintResponse(BaseModel):
    project_id: str = Field(description="项目 ID")
    company_id: Optional[str] = Field(default=None, description="公司 ID（若可解析）")
    blueprint: BlueprintProgressResponse = Field(description="蓝图详情（含 Markdown）")
    history: List[BlueprintHistoryEntry] = Field(description="蓝图历史记录（倒序）")


class CompanyBlueprintResponse(BaseModel):
    company_id: str = Field(description="公司 ID")
    resolved_project_id: str = Field(description="命中的项目 ID（默认项目或最新项目）")
    blueprint: BlueprintProgressResponse = Field(description="蓝图详情（含 Markdown）")
    history: List[BlueprintHistoryEntry] = Field(description="蓝图历史记录（倒序）")


class ComposeTraceListItem(BaseModel):
    trace_id: str
    n8n_session_id: Optional[str] = None
    company_id: Optional[str] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    business_name: Optional[str] = None
    source_learned_id: Optional[int] = None
    status: str
    final_video_url: Optional[str] = None
    last_n8n_updated_at: Optional[int] = None
    last_synced_at: Optional[int] = None
    created_at: int
    updated_at: int


class PaginatedComposeTraceResponse(BaseModel):
    items: List[ComposeTraceListItem]
    pagination: ProjectPaginationData


class ComposeTraceDetailResponse(BaseModel):
    trace: HSAIComposeTraceModel
    final_video_url: Optional[str] = None
    steps: List[HSAIComposeStepModel]
    artifacts: List[HSAIComposeArtifactModel]


def _resolve_default_project_for_company(company_id: str):
    projects = HSAIProjects.get_projects_by_company_id(company_id, limit=50)
    if not projects:
        return None
    for project in projects:
        config = getattr(project, "config", None) or {}
        if isinstance(config, dict) and config.get("is_default"):
            return project
    return projects[0]


def _load_project_blueprint_or_404(project_id: str, history_limit: int):
    progress = HSAIBlueprintProgressTable.get_by_project(project_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该项目暂无战略蓝图",
        )
    history = []
    if history_limit > 0:
        history = HSAIBlueprintProgressTable.list_history(progress.id, limit=history_limit)
    return progress, history



def _oauth_error(status_code: int, error_code: str, description: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error": error_code,
            "error_description": description,
        },
    )

def _derive_allowed_scopes() -> List[str]:
    return EXTERNAL_ADMIN_ALLOWED_SCOPES.copy() if EXTERNAL_ADMIN_ALLOWED_SCOPES else []

def _validate_and_resolve_scopes(requested_scope: Optional[str]) -> List[str]:
    allowed = _derive_allowed_scopes()
    if requested_scope in (None, ""):
        return allowed
    requested = [scope.strip() for scope in requested_scope.split() if scope.strip()]
    if not requested:
        return allowed
    if allowed and not set(requested).issubset(set(allowed)):
        raise _oauth_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_scope",
            "requested scope exceeds allowed scopes",
        )
    return requested

def _validate_client_credentials(client_id: str, client_secret: str) -> None:
    valid_secrets = [secret for secret in (
        EXTERNAL_ADMIN_CLIENT_SECRET,
        EXTERNAL_ADMIN_CLIENT_SECRET_ROLLOVER,
    ) if secret]
    if not valid_secrets:
        raise _oauth_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "client_secret_not_configured",
            "external admin client secret is not configured",
        )
    if client_id != EXTERNAL_ADMIN_CLIENT_ID or client_secret not in valid_secrets:
        raise _oauth_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_client",
            "client credentials are incorrect",
        )

def _enforce_rate_limit(client_id: str) -> None:
    if EXTERNAL_ADMIN_RATE_LIMIT_PER_MIN <= 0:
        return
    now = time.time()
    with _rate_lock:
        bucket = _rate_limit_state[client_id]
        cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= EXTERNAL_ADMIN_RATE_LIMIT_PER_MIN:
            raise _oauth_error(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "rate_limited",
                "token endpoint rate limit exceeded; retry later",
            )
        bucket.append(now)
router = APIRouter(prefix="/external/admin", tags=["external_admin"])

# 验证外部系统请求
def verify_external_request(request: Request):
    """验证外部系统请求的合法性"""
    global _AUTH_BYPASS_WARNING_EMITTED

    if EXTERNAL_ADMIN_AUTH_BYPASS:
        if not _AUTH_BYPASS_WARNING_EMITTED:
            log.warning(
                "EXTERNAL_ADMIN_AUTH_BYPASS enabled; skipping external admin IP/token checks. "
                "禁用该开关即可恢复鉴权。"
            )
            _AUTH_BYPASS_WARNING_EMITTED = True
        return EXTERNAL_ADMIN_CLIENT_ID

    if EXTERNAL_ADMIN_IP_WHITELIST:
        if not request.client:
            raise _oauth_error(
                status.HTTP_403_FORBIDDEN,
                "ip_not_allowed",
                "无法获取客户端IP",
            )
        client_ip = request.client.host
        if client_ip not in EXTERNAL_ADMIN_IP_WHITELIST:
            raise _oauth_error(
                status.HTTP_403_FORBIDDEN,
                "ip_not_allowed",
                "IP地址不在白名单中",
            )

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise _oauth_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_token",
            "缺少访问令牌",
        )

    raw_token = auth_header.split(" ", 1)[1].strip()
    token_record = ExternalAdminTokens.get_valid_token(raw_token)
    if not token_record:
        raise _oauth_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_token",
            "访问令牌无效或已过期",
        )

    return token_record.client_id


class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: List[UserModel] = Field(description="用户列表")
    total: int = Field(description="用户总数")


class CompanyCreateRequest(BaseModel):
    """公司创建请求模型"""
    name: str
    description: Optional[str] = None
    company_info: Optional[dict] = None
    config: Optional[dict] = None
    owner_user_id: str = Field(description="公司负责人用户ID")


class ProjectCreateRequest(BaseModel):
    """项目创建请求模型"""
    name: str
    description: Optional[str] = None
    business_name: str
    company_info: Optional[dict] = None
    config: Optional[dict] = None
    company_id: Optional[str] = Field(default=None, description="所属公司ID")
    user_id: str = Field(description="项目负责人用户ID")
    status: Optional[str] = "active"


class ProjectUpdateRequest(HSAIProjectUpdateForm):
    user_id: Optional[str] = Field(default=None, description="项目负责人用户ID")
    company_id: Optional[str] = Field(default=None, description="所属公司ID")


def _build_company_pagination(total: int, page: int, size: int) -> CompanyPaginationData:
    total_pages = (total + size - 1) // size if size else 0
    return CompanyPaginationData(total=total, page=page, size=size, total_pages=total_pages)


def _build_project_pagination(total: int, page: int, size: int) -> ProjectPaginationData:
    total_pages = (total + size - 1) // size if size else 0
    return ProjectPaginationData(total=total, page=page, size=size, total_pages=total_pages)


class OAuthTokenRequest(BaseModel):
    grant_type: str = Field(default="client_credentials")
    client_id: str
    client_secret: str
    scope: Optional[str] = Field(default=None, description="空值时使用配置默认 scope")


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = Field(default="bearer")
    expires_in: int
    scope: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6, description="新密码，需至少 6 位")


class OperationResponse(BaseModel):
    success: bool = True
    message: str
    active: Optional[bool] = None

@router.post("/oauth/token", response_model=OAuthTokenResponse)
async def issue_oauth_token(payload: OAuthTokenRequest):
    """颁发外部管理 OAuth2 访问令牌"""
    ExternalAdminTokens.cleanup_expired()

    if payload.grant_type != "client_credentials":
        raise _oauth_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_grant",
            "授权类型必须为 client_credentials",
        )

    client_id = payload.client_id or ""
    _enforce_rate_limit(client_id or "unknown")
    _validate_client_credentials(client_id, payload.client_secret)
    resolved_scopes = _validate_and_resolve_scopes(payload.scope)

    raw_token = token_urlsafe(48)
    issued = ExternalAdminTokens.issue_token(client_id, raw_token, EXTERNAL_ADMIN_TOKEN_TTL_SECONDS)
    if not issued:
        raise _oauth_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "token_issue_failed",
            "生成访问令牌失败",
        )

    log.info(
        "Issued external admin token",
        extra={
            "client_id": client_id,
            "scope": " ".join(resolved_scopes) if resolved_scopes else "",
        },
    )

    return OAuthTokenResponse(
        access_token=raw_token,
        expires_in=EXTERNAL_ADMIN_TOKEN_TTL_SECONDS,
        scope=" ".join(resolved_scopes) if resolved_scopes else None,
    )


# 用户管理接口
@router.post("/users", response_model=UserModel)
async def create_user(form_data: AddUserForm, request: Request):
    """创建用户（仅外部管理系统可访问）"""
    verify_external_request(request)

    business_name = (form_data.business_name or "").strip()
    if not business_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="business_name is required",
        )

    if Users.get_user_by_email(form_data.email.lower()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户邮箱已存在",
        )

    hashed_password = get_password_hash(form_data.password)

    user = Auths.insert_new_auth(
        email=form_data.email.lower(),
        password=hashed_password,
        name=form_data.name,
        profile_image_url=form_data.profile_image_url or "/user.png",
        role=form_data.role or "pending",
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.CREATE_USER_ERROR,
        )

    try:
        provision_enterprise_membership(
            user_id=user.id,
            business_name=business_name,
            promote_as_admin=True,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return user


@router.put("/users/{user_id}", response_model=UserModel)
async def update_user(
    user_id: str, form_data: ExternalAdminUserUpdateForm, request: Request
):
    """更新用户信息（仅外部管理系统可访问）"""
    verify_external_request(request)

    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    update_data = {
        "name": form_data.name,
        "email": form_data.email.lower(),
        "role": form_data.role or "pending",
        "profile_image_url": form_data.profile_image_url or "/user.png",
    }

    if form_data.password:
        hashed_password = get_password_hash(form_data.password)
        Auths.update_user_password_by_id(user_id, hashed_password)

    updated_user = Users.update_user_by_id(user_id, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户失败",
        )

    business_name = (form_data.business_name or "").strip() if form_data.business_name else None
    if business_name:
        try:
            provision_enterprise_membership(
                user_id=user_id,
                business_name=business_name,
                promote_as_admin=False,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

    return updated_user


class UserPermissionsResponse(BaseModel):
    role: str = Field(description="用户角色")
    permissions: Optional[dict] = Field(default=None, description="用户自定义权限(settings.permissions)")


class UpdateUserPermissionsRequest(BaseModel):
    role: Optional[str] = Field(default=None, description="新的角色，pending/user/admin")
    permissions: Optional[dict] = Field(default=None, description="要写入 settings.permissions 的 JSON")
    use_template: bool = Field(default=False, description="是否应用 CUSTOMER_PERMISSION_TEMPLATE")


class CompanyUserPermission(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    role: str
    permissions: Optional[dict] = None


class CompanyPermissionsResponse(BaseModel):
    company_id: str
    company_name: Optional[str] = None
    page: int
    page_size: int
    total: int
    users: List[CompanyUserPermission]


class CompanyPermissionsUpdateItem(BaseModel):
    user_id: str
    role: Optional[str] = None
    permissions: Optional[dict] = None
    use_template: bool = False


class BulkUpdateCompanyPermissionsRequest(BaseModel):
    users: List[CompanyPermissionsUpdateItem]
    fallback_to_template: bool = Field(default=False, description="当 payload 中缺少 permissions 时是否自动套用模板")
    page: Optional[int] = Field(default=1, description="批量更新后返回的分页页码")
    page_size: Optional[int] = Field(default=50, description="批量更新后返回的分页大小")


def _ensure_permission_api_enabled():
    if not ENABLE_CUSTOMER_PERMISSION_API.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )


def _format_company_permissions_payload(
    company_id: str,
    company_name: Optional[str],
    users: List[UserModel],
    *,
    page: int,
    page_size: int,
    total: int,
) -> CompanyPermissionsResponse:
    items: List[CompanyUserPermission] = []
    for item in users:
        permissions = (item.settings or {}).get("permissions") if item.settings else None
        items.append(
            CompanyUserPermission(
                user_id=item.id,
                name=item.name,
                email=item.email,
                role=item.role,
                permissions=permissions,
            )
        )
    return CompanyPermissionsResponse(
        company_id=company_id,
        company_name=company_name,
        page=page,
        page_size=page_size,
        total=total,
        users=items,
    )


@router.get("/users/{user_id}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(user_id: str, request: Request):
    """
    查询用户角色与 permissions（供后台客户管理调用）
    """
    verify_external_request(request)
    _ensure_permission_api_enabled()

    user, perms = customer_permissions_service.get_user_permissions(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )

    return UserPermissionsResponse(role=user.role, permissions=perms)


@router.patch("/users/{user_id}/permissions", response_model=UserPermissionsResponse)
async def update_user_permissions(
    user_id: str, payload: UpdateUserPermissionsRequest, request: Request
):
    """
    更新用户角色或 permissions（供后台客户管理调用）
    """
    verify_external_request(request)
    _ensure_permission_api_enabled()

    try:
        updated = customer_permissions_service.update_user_permissions(
            user_id,
            role=payload.role,
            explicit_permissions=payload.permissions,
            use_template=payload.use_template,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )

    user, perms = updated
    return UserPermissionsResponse(role=user.role, permissions=perms)


@router.get(
    "/companies/{company_id}/permissions",
    response_model=CompanyPermissionsResponse,
)
async def get_company_permissions(
    company_id: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    verify_external_request(request)
    _ensure_permission_api_enabled()

    company, user_list, normalized_page, normalized_size = (
        customer_permissions_service.list_company_permissions(
            company_id, page=page, page_size=page_size
        )
    )

    return _format_company_permissions_payload(
        company_id=company_id,
        company_name=company.name if company else None,
        users=user_list.users,
        page=normalized_page,
        page_size=normalized_size,
        total=user_list.total,
    )


@router.patch(
    "/companies/{company_id}/permissions",
    response_model=CompanyPermissionsResponse,
)
async def update_company_permissions(
    company_id: str,
    payload: BulkUpdateCompanyPermissionsRequest,
    request: Request,
):
    verify_external_request(request)
    _ensure_permission_api_enabled()

    if not payload.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="users payload is empty"
        )

    try:
        customer_permissions_service.bulk_update_company_permissions(
            company_id,
            [item.dict() for item in payload.users],
            fallback_to_template=payload.fallback_to_template,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    company, user_list, normalized_page, normalized_size = (
        customer_permissions_service.list_company_permissions(
            company_id, page=payload.page or 1, page_size=payload.page_size or 50
        )
    )

    return _format_company_permissions_payload(
        company_id=company_id,
        company_name=company.name if company else None,
        users=user_list.users,
        page=normalized_page,
        page_size=normalized_size,
        total=user_list.total,
    )


@router.post("/users/{user_id}/reset-password", response_model=OperationResponse)
async def reset_user_password(
    user_id: str,
    payload: ResetPasswordRequest,
    request: Request,
):
    """重置用户密码（仅外部管理系统可访问）"""
    verify_external_request(request)

    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    hashed = get_password_hash(payload.new_password)
    if not Auths.update_user_password_by_id(user_id, hashed):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置密码失败",
        )
    return OperationResponse(message="密码已重置")


@router.post("/users/{user_id}/enable", response_model=OperationResponse)
async def enable_user(user_id: str, request: Request):
    """启用用户账号（仅外部管理系统可访问）"""
    verify_external_request(request)

    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if not Auths.set_active_by_id(user_id, True):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="启用账号失败",
        )
    return OperationResponse(message="账号已启用", active=True)


@router.post("/users/{user_id}/disable", response_model=OperationResponse)
async def disable_user(user_id: str, request: Request):
    """禁用用户账号（仅外部管理系统可访问）"""
    verify_external_request(request)

    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if not Auths.set_active_by_id(user_id, False):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="禁用账号失败",
        )
    return OperationResponse(message="账号已禁用", active=False)

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    """删除用户（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    # 检查用户是否存在
    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 删除用户
    result = Auths.delete_auth_by_id(user_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除用户失败"
        )
    
    return {"message": "用户删除成功"}

@router.get("/users", response_model=UserListResponse)
async def get_users(
    request: Request,
    page: int = Query(1, ge=1, description="分页页码，从1开始"),
    size: int = Query(20, ge=1, le=100, description="分页大小"),
    company_id: Optional[str] = Query(None, description="按公司筛选"),
    query: Optional[str] = Query(None, description="名称/邮箱模糊匹配"),
    order_by: Optional[str] = Query(
        None,
        description="排序字段，可选 name/email/created_at/last_active_at/updated_at/role",
    ),
    direction: Optional[str] = Query(
        None,
        description="排序方向 asc/desc（默认 desc）",
    ),
    user_id: Optional[str] = Query(None, description="指定用户ID时直接返回单条记录"),
):
    """获取用户列表（仅外部管理系统可访问）"""
    verify_external_request(request)

    if user_id:
        user = Users.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.USER_NOT_FOUND,
            )
        return UserListResponse(users=[user], total=1)

    offset = (page - 1) * size
    filter_params: Dict[str, Any] = {}
    if query:
        filter_params["query"] = query
    if order_by:
        filter_params["order_by"] = order_by
    if direction:
        filter_params["direction"] = direction

    users_response = Users.get_users(
        filter=filter_params or None,
        skip=offset,
        limit=size,
        company_id=company_id,
    )

    return users_response


@router.get("/users/{user_id}", response_model=UserModel)
async def get_user_detail(user_id: str, request: Request):
    """获取用户详情（仅外部管理系统可访问）"""
    verify_external_request(request)
    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )
    return user

# 公司管理接口
@router.get("/companies", response_model=PaginatedCompanyResponse)
async def list_companies_admin(
    request: Request,
    company_status: Optional[str] = Query(None, description="公司状态过滤"),
    ps: int = Query(20, ge=1, le=100, description="分页大小"),
    pi: int = Query(1, ge=1, description="分页索引，从1开始"),
):
    """获取公司列表（仅外部管理系统可访问）"""
    verify_external_request(request)

    offset = (pi - 1) * ps
    companies = Companies.get_all_companies(
        status=company_status,
        limit=ps,
        offset=offset,
    )
    total = Companies.get_all_companies_count(status=company_status)
    responses = [CompanyResponse(**company.model_dump()) for company in companies]
    pagination = _build_company_pagination(total, pi, ps)
    return PaginatedCompanyResponse(data=responses, pagination=pagination)


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company_admin(company_id: str, request: Request):
    """获取公司详情（仅外部管理系统可访问）"""
    verify_external_request(request)
    company = Companies.get_company_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公司不存在",
        )
    return CompanyResponse(**company.model_dump())


@router.get(
    "/companies/{company_id}/projects",
    response_model=PaginatedHSAIProjectResponse,
)
async def list_company_projects_admin(
    company_id: str,
    request: Request,
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="项目状态过滤（可使用 status 参数传入）",
    ),
    ps: int = Query(20, ge=1, le=100, description="分页大小"),
    pi: int = Query(1, ge=1, description="分页索引，从1开始"),
):
    """获取公司下项目列表（仅外部管理系统可访问）"""
    verify_external_request(request)
    company = Companies.get_company_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公司不存在",
        )
    offset = (pi - 1) * ps
    projects = HSAIProjects.get_projects_by_company_id(
        company_id,
        status=status_filter,
        limit=ps,
        offset=offset,
    )
    total = HSAIProjects.get_projects_count_by_company_id(
        company_id,
        status=status_filter,
    )
    responses = [_build_project_response_with_tiktok(project) for project in projects]
    pagination = _build_project_pagination(total, pi, ps)
    return PaginatedHSAIProjectResponse(data=responses, pagination=pagination)


@router.post("/companies", response_model=CompanyResponse)
async def create_company(payload: CompanyCreateRequest, request: Request):
    """创建公司（仅外部管理系统可访问）"""
    verify_external_request(request)

    owner = Users.get_user_by_id(payload.owner_user_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="负责人用户不存在",
        )

    form = CompanyForm(
        name=payload.name,
        description=payload.description,
        company_info=payload.company_info,
        config=payload.config,
    )
    company = Companies.insert_new_company(payload.owner_user_id, form)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建公司失败",
        )
    return CompanyResponse(**company.model_dump())


@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(company_id: str, form_data: CompanyUpdateForm, request: Request):
    """更新公司信息（仅外部管理系统可访问）"""
    verify_external_request(request)

    company = Companies.get_company_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公司不存在",
        )

    updated_company = Companies.update_company_by_id(company_id, form_data)
    if not updated_company:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新公司失败",
        )
    return CompanyResponse(**updated_company.model_dump())


@router.delete("/companies/{company_id}")
async def delete_company(company_id: str, request: Request):
    """删除公司（仅外部管理系统可访问）"""
    verify_external_request(request)

    company = Companies.get_company_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公司不存在",
        )

    # 删除前校验是否仍有关联项目或用户
    from open_webui.models.hsai_projects import HSAIProjects

    related_projects = HSAIProjects.get_projects_by_company_id(company_id, limit=1)
    if related_projects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="公司下仍存在项目，无法删除",
        )

    users_in_company = Users.get_users(company_id=company_id)
    if users_in_company.total > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="公司下仍有关联用户，无法删除",
        )

    if not Companies.delete_company_by_id(company_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除公司失败",
        )
    return {"message": "公司删除成功"}


@router.get("/projects", response_model=PaginatedHSAIProjectResponse)
async def list_projects_admin(
    request: Request,
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="项目状态过滤（可使用 status 参数传入）",
    ),
    company_id: Optional[str] = Query(None, description="所属公司ID"),
    ps: int = Query(20, ge=1, le=100, description="分页大小"),
    pi: int = Query(1, ge=1, description="分页索引，从1开始"),
):
    """获取项目列表（仅外部管理系统可访问）"""
    verify_external_request(request)
    offset = (pi - 1) * ps

    if company_id:
        company = Companies.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="公司不存在",
            )
        projects = HSAIProjects.get_projects_by_company_id(
            company_id,
            status=status_filter,
            limit=ps,
            offset=offset,
        )
        total = HSAIProjects.get_projects_count_by_company_id(
            company_id,
            status=status_filter,
        )
    else:
        projects = HSAIProjects.get_projects(
            status=status_filter,
            limit=ps,
            offset=offset,
        )
        total = HSAIProjects.get_projects_count_all(status=status_filter)

    responses = [_build_project_response_with_tiktok(project) for project in projects]
    pagination = _build_project_pagination(total, pi, ps)
    return PaginatedHSAIProjectResponse(data=responses, pagination=pagination)


@router.get("/projects/{project_id}", response_model=HSAIProjectResponse)
async def get_project_admin(project_id: str, request: Request):
    """获取项目详情（仅外部管理系统可访问）"""
    verify_external_request(request)
    project = HSAIProjects.get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )
    return _build_project_response_with_tiktok(project)


@router.post("/projects", response_model=HSAIProjectResponse)
async def create_project_admin(payload: ProjectCreateRequest, request: Request):
    """创建项目（仅外部管理系统可访问）"""
    verify_external_request(request)

    owner = Users.get_user_by_id(payload.user_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目负责人不存在",
        )
    if payload.company_id:
        company = Companies.get_company_by_id(payload.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="公司不存在",
            )

    form = HSAIProjectForm(
        name=payload.name,
        description=payload.description,
        business_name=payload.business_name,
        company_info=payload.company_info,
        config=payload.config,
        company_id=payload.company_id,
        user_id=payload.user_id,
        status=payload.status,
    )
    project = HSAIProjects.insert_new_project(payload.user_id, form)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建项目失败",
        )
    return _build_project_response_with_tiktok(project)


@router.put("/projects/{project_id}", response_model=HSAIProjectResponse)
async def update_project_admin(
    project_id: str,
    form_data: ProjectUpdateRequest,
    request: Request,
):
    """更新项目信息（仅外部管理系统可访问）"""
    verify_external_request(request)

    project = HSAIProjects.get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )

    if form_data.user_id:
        owner = Users.get_user_by_id(form_data.user_id)
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目负责人不存在",
            )
    if form_data.company_id:
        company = Companies.get_company_by_id(form_data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="公司不存在",
            )

    updated_project = HSAIProjects.update_project_by_id(project_id, form_data)
    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新项目失败",
        )
    return _build_project_response_with_tiktok(updated_project)


@router.get("/projects/{project_id}/tiktok-stats", response_model=TikTokProjectStatsResponse)
async def get_project_tiktok_stats_admin(project_id: str, request: Request):
    """获取项目维度的 TikTok 运营指标（仅外部管理系统可访问）"""
    verify_external_request(request)
    project = HSAIProjects.get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )

    company_id = str(getattr(project, "company_id", "") or "")
    if not company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目未绑定公司，无法计算 TikTok 指标",
        )

    required_accounts = 0
    progress = HSAIBlueprintProgressTable.get_by_project(project_id)
    if progress and progress.required_tiktok_accounts:
        required_accounts = _parse_required_tiktok_accounts(progress.required_tiktok_accounts) or 0

    active_accounts = SocialAccounts.count_active_accounts(company_id, platform="tiktok")

    now_ts = int(time.time())
    since_7d = now_ts - 7 * 24 * 60 * 60

    last_publish_at = HSAITikTokPublishLogs.get_last_publish_at(
        company_id=company_id,
        project_id=project_id,
        status="success",
    )
    publish_last_7d_total = HSAITikTokPublishLogs.count_publishes_since(
        company_id=company_id,
        project_id=project_id,
        since_ts=since_7d,
        status="success",
        mode=None,
    )
    publish_last_7d_inbox = HSAITikTokPublishLogs.count_publishes_since(
        company_id=company_id,
        project_id=project_id,
        since_ts=since_7d,
        status="success",
        mode="INBOX",
    )
    publish_last_7d_direct = HSAITikTokPublishLogs.count_publishes_since(
        company_id=company_id,
        project_id=project_id,
        since_ts=since_7d,
        status="success",
        mode="DIRECT",
    )

    return TikTokProjectStatsResponse(
        project_id=project_id,
        company_id=company_id,
        required_accounts=required_accounts,
        active_accounts=active_accounts,
        last_publish_at=last_publish_at,
        publish_last_7d_total=publish_last_7d_total,
        publish_last_7d_inbox=publish_last_7d_inbox,
        publish_last_7d_direct=publish_last_7d_direct,
    )


@router.post("/compose/traces", response_model=HSAIComposeTraceModel)
async def upsert_compose_trace_admin(form_data: ComposeTraceCreateForm, request: Request):
    """注册/更新合成追溯（仅外部管理系统可访问）"""
    verify_external_request(request)
    trace = HSAIComposeTraces.upsert_trace(form_data)
    # 尽量同步一次（失败不影响注册）
    try:
        sync_trace_once(trace.trace_id)
    except Exception:  # pragma: no cover
        pass
    return trace


@router.get("/compose/traces", response_model=PaginatedComposeTraceResponse)
async def list_compose_traces_admin(
    request: Request,
    company_id: Optional[str] = Query(None, description="公司ID过滤"),
    project_id: Optional[str] = Query(None, description="项目ID过滤"),
    status_filter: Optional[str] = Query(None, alias="status", description="状态过滤"),
    ps: int = Query(20, ge=1, le=100, description="分页大小"),
    pi: int = Query(1, ge=1, description="分页索引（从 1 开始）"),
):
    """分页列出合成追溯（仅外部管理系统可访问）"""
    verify_external_request(request)

    offset = (pi - 1) * ps
    total = HSAIComposeTraces.count_traces(
        company_id=company_id,
        project_id=project_id,
        status=status_filter,
    )
    traces = HSAIComposeTraces.list_traces(
        company_id=company_id,
        project_id=project_id,
        status=status_filter,
        limit=ps,
        offset=offset,
    )

    items: List[ComposeTraceListItem] = []
    for trace in traces:
        final_url = None
        try:
            final_url = HSAIComposeTraces.get_final_video_url(trace.trace_id)
        except Exception:  # pragma: no cover
            final_url = None
        items.append(
            ComposeTraceListItem(
                trace_id=trace.trace_id,
                n8n_session_id=trace.n8n_session_id,
                company_id=trace.company_id,
                project_id=trace.project_id,
                user_id=trace.user_id,
                business_name=trace.business_name,
                source_learned_id=trace.source_learned_id,
                status=trace.status,
                final_video_url=final_url,
                last_n8n_updated_at=trace.last_n8n_updated_at,
                last_synced_at=trace.last_synced_at,
                created_at=trace.created_at,
                updated_at=trace.updated_at,
            )
        )

    pagination = _build_project_pagination(total, pi, ps)
    return PaginatedComposeTraceResponse(items=items, pagination=pagination)


@router.get("/compose/traces/{trace_id}", response_model=ComposeTraceDetailResponse)
async def get_compose_trace_admin(trace_id: str, request: Request):
    """获取合成追溯详情（仅外部管理系统可访问）"""
    verify_external_request(request)

    # 先同步一次，确保详情尽量新
    try:
        sync_trace_once(trace_id)
    except Exception:  # pragma: no cover
        pass

    trace = HSAIComposeTraces.get_trace(trace_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="追溯记录不存在",
        )

    steps = HSAIComposeTraces.list_steps(trace_id)
    artifacts = HSAIComposeTraces.list_artifacts(trace_id)
    final_url = HSAIComposeTraces.get_final_video_url(trace_id)
    return ComposeTraceDetailResponse(
        trace=trace,
        final_video_url=final_url,
        steps=steps,
        artifacts=artifacts,
    )


@router.get("/projects/{project_id}/blueprint", response_model=ProjectBlueprintResponse)
async def get_project_blueprint_admin(
    project_id: str,
    request: Request,
    history_limit: int = Query(20, description="返回历史记录条数（0-100）", ge=0, le=100),
):
    """获取项目战略蓝图（Markdown + 元信息 + 历史）（仅外部管理系统可访问）"""
    verify_external_request(request)

    project = HSAIProjects.get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )

    progress, history = _load_project_blueprint_or_404(project_id, history_limit=history_limit)

    company_id = str(getattr(project, "company_id", "") or "") or None
    return ProjectBlueprintResponse(
        project_id=project_id,
        company_id=company_id,
        blueprint=BlueprintProgressResponse.from_model(progress),
        history=[BlueprintHistoryEntry.from_model(item) for item in history],
    )


@router.get("/companies/{company_id}/blueprint", response_model=CompanyBlueprintResponse)
async def get_company_blueprint_admin(
    company_id: str,
    request: Request,
    project_id: Optional[str] = Query(None, description="指定项目 ID（可选，必须属于该公司）"),
    history_limit: int = Query(20, description="返回历史记录条数（0-100）", ge=0, le=100),
):
    """获取公司战略蓝图（默认项目/指定项目）（仅外部管理系统可访问）"""
    verify_external_request(request)

    company = Companies.get_company_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公司不存在",
        )

    resolved_project = None
    if project_id:
        resolved_project = HSAIProjects.get_project_by_id(project_id)
        if not resolved_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在",
            )
        if str(getattr(resolved_project, "company_id", "") or "") != company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该项目不属于指定公司",
            )
    else:
        resolved_project = _resolve_default_project_for_company(company_id)
        if not resolved_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="公司下暂无项目，无法解析战略蓝图",
            )

    progress, history = _load_project_blueprint_or_404(resolved_project.id, history_limit=history_limit)
    return CompanyBlueprintResponse(
        company_id=company_id,
        resolved_project_id=resolved_project.id,
        blueprint=BlueprintProgressResponse.from_model(progress),
        history=[BlueprintHistoryEntry.from_model(item) for item in history],
    )


@router.delete("/projects/{project_id}")
async def delete_project_admin(project_id: str, request: Request):
    """删除项目（仅外部管理系统可访问）"""
    verify_external_request(request)
    project = HSAIProjects.get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )
    if not HSAIProjects.delete_project_by_id(project_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除项目失败",
        )
    return {"message": "项目删除成功"}



@router.post("/companies/{company_id}/users/{user_id}")
async def assign_user_to_company(company_id: str, user_id: str, request: Request):
    """将用户分配到公司（仅外部管理系统可访问）"""
    verify_external_request(request)

    company = Companies.get_company_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公司不存在",
        )

    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    update_data = {"company_id": company_id, "business_name": company.name}
    updated_user = Users.update_user_by_id(user_id, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户公司信息失败",
        )

    return {"message": "用户已成功分配到公司"}


@router.delete("/companies/{company_id}/users/{user_id}")
async def remove_user_from_company(company_id: str, user_id: str, request: Request):
    """将用户从公司移除（仅外部管理系统可访问）"""
    verify_external_request(request)

    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    update_data = {"company_id": None, "business_name": None}
    updated_user = Users.update_user_by_id(user_id, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户公司信息失败",
        )

    return {"message": "用户已成功从公司移除"}


# ========================================================================
# Materials Management Routes (素材管理路由)
# ========================================================================

from open_webui.routers.external_admin_materials import (
    list_materials,
    get_material_detail,
    resync_material,
    MaterialDetailResponse,
    PaginatedHSAIMaterialResponse as MaterialsPaginatedResponse,
)

# 注册素材管理路由
router.get("/materials/", response_model=MaterialsPaginatedResponse, summary="查询素材列表")(list_materials)
router.get("/materials/{material_id}", response_model=MaterialDetailResponse, summary="查询素材详情")(get_material_detail)
router.post("/materials/{material_id}/resync", summary="强制重新同步OSS")(resync_material)
