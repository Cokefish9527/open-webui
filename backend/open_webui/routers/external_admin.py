import os
from secrets import token_urlsafe
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from open_webui.models.users import Users, UserModel
from open_webui.models.hsai_companies import (
    Companies,
    CompanyForm,
    CompanyUpdateForm,
    CompanyModel,
)
from open_webui.models.auths import Auths, AddUserForm
from open_webui.utils.auth import get_password_hash
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.external_admin_tokens import ExternalAdminTokens

# 从配置中获取外部管理密钥和IP白名单
EXTERNAL_ADMIN_IP_WHITELIST = os.environ.get("EXTERNAL_ADMIN_IP_WHITELIST")

EXTERNAL_ADMIN_CLIENT_ID = os.environ.get("EXTERNAL_ADMIN_CLIENT_ID", "external-admin")
EXTERNAL_ADMIN_CLIENT_SECRET = os.environ.get("EXTERNAL_ADMIN_CLIENT_SECRET")
EXTERNAL_ADMIN_TOKEN_TTL_SECONDS = int(os.environ.get("EXTERNAL_ADMIN_TOKEN_TTL_SECONDS", "900"))

router = APIRouter(prefix="/external/admin", tags=["external_admin"])

# 验证外部系统请求
def verify_external_request(request: Request):
    """验证外部系统请求的合法性"""
    # IP白名单检查
    if EXTERNAL_ADMIN_IP_WHITELIST:
        if not request.client:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无法获取客户端IP"
            )
        client_ip = request.client.host
        allowed_ips = EXTERNAL_ADMIN_IP_WHITELIST.split(",")
        if client_ip not in allowed_ips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP地址不在白名单中"
            )

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少访问令牌",
        )
    raw_token = auth_header.split(" ", 1)[1].strip()
    token_record = ExternalAdminTokens.get_valid_token(raw_token)
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="访问令牌无效或已过期",
        )
    return token_record.client_id

class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: List[UserModel] = Field(description="用户列表")
    total: int = Field(description="用户总数")


class CompanyListResponse(BaseModel):
    """公司列表响应模型"""
    companies: List[CompanyModel] = Field(description="公司列表")
    total: int = Field(description="公司总数")


class CompanyCreateRequest(CompanyForm):
    owner_user_id: str = Field(description="公司负责人用户ID")


class OAuthTokenRequest(BaseModel):
    grant_type: str = Field(default="client_credentials")
    client_id: str
    client_secret: str


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = Field(default="bearer")
    expires_in: int


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='grant_type must be client_credentials'
        )
    if not EXTERNAL_ADMIN_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='external admin client secret is not configured'
        )
    if payload.client_id != EXTERNAL_ADMIN_CLIENT_ID or payload.client_secret != EXTERNAL_ADMIN_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='客户端凭据不正确'
        )
    raw_token = token_urlsafe(48)
    issued = ExternalAdminTokens.issue_token(payload.client_id, raw_token, EXTERNAL_ADMIN_TOKEN_TTL_SECONDS)
    if not issued:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='生成访问令牌失败'
        )
    return OAuthTokenResponse(access_token=raw_token, expires_in=EXTERNAL_ADMIN_TOKEN_TTL_SECONDS)

# 用户管理接口
@router.post("/users", response_model=UserModel)
async def create_user(form_data: AddUserForm, request: Request):
    """创建用户（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    # 检查用户是否已存在
    if Users.get_user_by_email(form_data.email.lower()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户邮箱已存在"
        )
    
    # 创建认证信息
    hashed_password = get_password_hash(form_data.password)
    
    # 创建用户
    user = Auths.insert_new_auth(
        email=form_data.email.lower(),
        password=hashed_password,
        name=form_data.name,
        profile_image_url=form_data.profile_image_url or "/user.png",
        role=form_data.role or "pending"
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.CREATE_USER_ERROR
        )
    
    return user

@router.put("/users/{user_id}", response_model=UserModel)
async def update_user(user_id: str, form_data: AddUserForm, request: Request):
    """更新用户信息（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    # 检查用户是否存在
    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新用户信息
    update_data = {
        "name": form_data.name,
        "email": form_data.email.lower(),
        "role": form_data.role or "pending",
        "profile_image_url": form_data.profile_image_url or "/user.png"
    }
    
    # 如果提供了新密码，则更新密码
    if form_data.password:
        hashed_password = get_password_hash(form_data.password)
        Auths.update_user_password_by_id(user_id, hashed_password)
    
    updated_user = Users.update_user_by_id(user_id, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户失败"
        )
    
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
@router.post("/companies", response_model=CompanyModel)
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
    return company


@router.put("/companies/{company_id}", response_model=CompanyModel)
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
    return updated_company


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


@router.get("/companies", response_model=CompanyListResponse)
async def list_companies(
    request: Request,
    page: int = 1,
    size: int = 20,
    status_filter: Optional[str] = None,
):
    """获取公司列表（仅外部管理系统可访问）"""
    verify_external_request(request)

    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    offset = (page - 1) * size
    companies = Companies.get_all_companies(
        status=status_filter,
        limit=size,
        offset=offset,
    )
    total = Companies.get_all_companies_count(status=status_filter)
    return CompanyListResponse(companies=companies, total=total)


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
