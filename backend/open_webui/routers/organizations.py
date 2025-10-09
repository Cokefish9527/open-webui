from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from open_webui.models.organizations import (
    Organizations, 
    OrganizationForm, 
    OrganizationUpdateForm,
    OrganizationResponse,
    PaginatedOrganizationResponse,
    PaginationData
)
from open_webui.models.users import Users, UserResponse, UserListResponse
from open_webui.models.hsai_projects import HSAIProjects
from open_webui.utils.tenant_access_control import (
    require_system_admin, 
    require_org_admin,
    require_org_access,
    check_user_org_access
)
from open_webui.models.users import UserModel
from open_webui.constants import ERROR_MESSAGES

router = APIRouter()


############################
# 获取组织列表
############################

@router.get("/", response_model=PaginatedOrganizationResponse)
async def get_organizations(
    page: int = 1,
    size: int = 20,
    user: UserModel = Depends(require_system_admin)
):
    """
    获取组织列表（仅系统管理员可访问）
    """
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20
    
    offset = (page - 1) * size
    organizations = Organizations.get_organizations(limit=size, offset=offset)
    total = Organizations.get_organizations_count()
    
    total_pages = (total + size - 1) // size  # 向上取整
    
    return PaginatedOrganizationResponse(
        data=[OrganizationResponse(**org.model_dump()) for org in organizations],
        pagination=PaginationData(
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
    )


############################
# 创建组织
############################

@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    form_data: OrganizationForm,
    user: UserModel = Depends(require_system_admin)
):
    """
    创建新组织（仅系统管理员可访问）
    """
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
    
    return OrganizationResponse(**organization.model_dump())


############################
# 获取组织详情
############################

@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization_by_id(
    organization_id: str,
    user: UserModel = Depends(require_org_access)
):
    """
    获取组织详情
    """
    organization = Organizations.get_organization_by_id(organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )
    
    return OrganizationResponse(**organization.model_dump())


############################
# 更新组织信息
############################

@router.post("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    form_data: OrganizationUpdateForm,
    user: UserModel = Depends(require_org_admin)
):
    """
    更新组织信息（组织管理员及以上可访问）
    """
    # 验证组织访问权限
    if not user.is_super_admin:
        if user.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改该组织信息"
            )
    
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
    
    return OrganizationResponse(**updated_organization.model_dump())


############################
# 删除组织
############################

@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    user: UserModel = Depends(require_system_admin)
):
    """
    删除组织（仅系统管理员可访问）
    """
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
    
    # 检查组织下是否有项目
    projects = HSAIProjects.get_projects_by_user_id(user.id, limit=1)
    # 这里需要根据实际情况调整查询逻辑，检查该组织下的项目
    
    # 删除组织
    result = Organizations.delete_organization_by_id(organization_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除组织失败"
        )
    
    return {"message": "组织删除成功"}


############################
# 获取组织用户列表
############################

@router.get("/{organization_id}/users", response_model=UserListResponse)
async def get_organization_users(
    organization_id: str,
    page: int = 1,
    size: int = 20,
    user: UserModel = Depends(require_org_access)
):
    """
    获取组织用户列表
    """
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20
    
    offset = (page - 1) * size
    users_response = Users.get_users(
        skip=offset, 
        limit=size, 
        organization_id=organization_id
    )
    
    return users_response


############################
# 添加用户到组织
############################

@router.post("/{organization_id}/users/{user_id}")
async def add_user_to_organization(
    organization_id: str,
    user_id: str,
    is_org_admin: bool = False,
    user: UserModel = Depends(require_org_admin)
):
    """
    添加用户到组织（组织管理员及以上可访问）
    """
    # 验证组织访问权限
    if not user.is_super_admin:
        if user.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作该组织用户"
            )
    
    # 检查用户是否存在
    target_user = Users.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新用户组织信息
    updated_data = {
        "organization_id": organization_id,
        "is_org_admin": is_org_admin
    }
    
    updated_user = Users.update_user_by_id(user_id, updated_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户失败"
        )
    
    return {"message": "用户已成功添加到组织"}


############################
# 从组织移除用户
############################

@router.delete("/{organization_id}/users/{user_id}")
async def remove_user_from_organization(
    organization_id: str,
    user_id: str,
    user: UserModel = Depends(require_org_admin)
):
    """
    从组织移除用户（组织管理员及以上可访问）
    """
    # 验证组织访问权限
    if not user.is_super_admin:
        if user.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作该组织用户"
            )
    
    # 检查用户是否存在
    target_user = Users.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 不能移除自己
    if user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能移除自己"
        )
    
    # 更新用户组织信息
    updated_data = {
        "organization_id": None,
        "is_org_admin": False
    }
    
    updated_user = Users.update_user_by_id(user_id, updated_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户失败"
        )
    
    return {"message": "用户已成功从组织移除"}