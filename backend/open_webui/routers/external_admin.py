import logging
import os
import time
from collections import defaultdict, deque
from secrets import token_urlsafe
from threading import Lock
from typing import Optional, List, Deque, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from open_webui.models.users import Users, UserModel
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
from open_webui.models.auths import (
    Auths,
    AddUserForm,
    ExternalAdminUserUpdateForm,
)
from open_webui.utils.auth import get_password_hash
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.external_admin_tokens import ExternalAdminTokens
from open_webui.services.enterprise_provisioning import provision_enterprise_membership

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


class CompanyCreateRequest(CompanyForm):
    owner_user_id: str = Field(description="公司负责人用户ID")


class ProjectCreateRequest(HSAIProjectForm):
    user_id: str = Field(description="项目负责人用户ID")
    company_id: Optional[str] = Field(default=None, description="所属公司ID")


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
            "grant_type must be client_credentials",
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

@router.get("/users")
async def get_users(
    request: Request,
    page: int = 1,
    size: int = 20,
    company_id: Optional[str] = None,
):
    """获取用户列表（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20
    
    offset = (page - 1) * size
    users_response = Users.get_users(skip=offset, limit=size, company_id=company_id)
    
    return users_response

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
    status_filter: Optional[str] = Query(None, description="项目状态过滤"),
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
    responses = [HSAIProjectResponse(**project.model_dump()) for project in projects]
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
    status_filter: Optional[str] = Query(None, description="项目状态过滤"),
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

    responses = [HSAIProjectResponse(**project.model_dump()) for project in projects]
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
    return HSAIProjectResponse(**project.model_dump())


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
    return HSAIProjectResponse(**project.model_dump())


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
    return HSAIProjectResponse(**updated_project.model_dump())


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
