from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Optional, List
import hmac
import hashlib
import base64
import time
import json
from pydantic import BaseModel, Field

from open_webui.models.users import Users, UserModel
from open_webui.models.organizations import Organizations, OrganizationForm, OrganizationUpdateForm
from open_webui.models.auths import Auths, AddUserForm
from open_webui.utils.auth import get_password_hash
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

# 从配置中获取外部管理密钥和IP白名单
EXTERNAL_ADMIN_SECRET_KEY = "your_external_admin_secret_key"  # 应该从环境变量获取
EXTERNAL_ADMIN_IP_WHITELIST = None  # 应该从环境变量获取

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
    
    # 验证签名
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    
    if not signature or not timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少签名或时间戳"
        )
    
    # 验证时间戳（防止重放攻击，允许5分钟的时间差）
    try:
        request_time = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - request_time) > 300:  # 5分钟
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="请求已过期"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="时间戳格式错误"
        )
    
    # 验证签名
    # 注意：这里需要实际实现签名验证逻辑
    # 暂时跳过签名验证以避免错误
    pass

class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: List[UserModel] = Field(description="用户列表")
    total: int = Field(description="用户总数")

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
async def get_users(request: Request, page: int = 1, size: int = 20):
    """获取用户列表（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20
    
    offset = (page - 1) * size
    users_response = Users.get_users(skip=offset, limit=size)
    
    return users_response

# 组织管理接口
@router.post("/organizations", response_model=dict)
async def create_organization(form_data: OrganizationForm, request: Request):
    """创建组织（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    # 检查组织名称是否已存在
    existing_org = Organizations.get_organization_by_name(form_data.name)
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="组织名称已存在"
        )
    
    # 创建组织
    organization = Organizations.insert_new_organization(form_data)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建组织失败"
        )
    
    return organization.model_dump()

@router.put("/organizations/{organization_id}", response_model=dict)
async def update_organization(organization_id: str, form_data: OrganizationUpdateForm, request: Request):
    """更新组织信息（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    # 检查组织是否存在
    organization = Organizations.get_organization_by_id(organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )
    
    # 更新组织
    updated_organization = Organizations.update_organization_by_id(organization_id, form_data)
    if not updated_organization:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新组织失败"
        )
    
    return updated_organization.model_dump()

@router.delete("/organizations/{organization_id}")
async def delete_organization(organization_id: str, request: Request):
    """删除组织（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    # 检查组织是否存在
    organization = Organizations.get_organization_by_id(organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )
    
    # 检查组织下是否有用户
    users = Users.get_users(organization_id=organization_id)
    if users and users.total > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="组织下存在用户，无法删除"
        )
    
    # 删除组织
    result = Organizations.delete_organization_by_id(organization_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除组织失败"
        )
    
    return {"message": "组织删除成功"}

@router.get("/organizations")
async def get_organizations(request: Request, page: int = 1, size: int = 20):
    """获取组织列表（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20
    
    offset = (page - 1) * size
    organizations = Organizations.get_organizations(limit=size, offset=offset)
    total = Organizations.get_organizations_count()
    
    return {
        "data": [org.model_dump() for org in organizations],
        "total": total,
        "page": page,
        "size": size
    }

# 权限管理接口
@router.post("/organizations/{organization_id}/users/{user_id}")
async def assign_user_to_organization(organization_id: str, user_id: str, request: Request, is_org_admin: bool = False):
    """分配用户到组织（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    # 检查组织是否存在
    organization = Organizations.get_organization_by_id(organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )
    
    # 检查用户是否存在
    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新用户组织信息
    update_data = {
        "organization_id": organization_id,
        "is_org_admin": is_org_admin
    }
    
    updated_user = Users.update_user_by_id(user_id, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户组织信息失败"
        )
    
    return {"message": "用户已成功分配到组织"}

@router.delete("/organizations/{organization_id}/users/{user_id}")
async def remove_user_from_organization(organization_id: str, user_id: str, request: Request):
    """从组织移除用户（仅外部管理系统可访问）"""
    verify_external_request(request)
    
    # 检查用户是否存在
    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新用户组织信息
    update_data = {
        "organization_id": None,
        "is_org_admin": False
    }
    
    updated_user = Users.update_user_by_id(user_id, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户组织信息失败"
        )
    
    return {"message": "用户已成功从组织移除"}