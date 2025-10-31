from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from open_webui.models.organizations import (
    Organizations,
    OrganizationForm,
    OrganizationUpdateForm,
    OrganizationResponse,
    PaginatedOrganizationResponse,
    PaginationData,
)
from open_webui.models.users import Users, UserListResponse
from open_webui.models.hsai_projects import HSAIProjects
from open_webui.utils.tenant_access_control import (
    require_system_admin,
    require_org_admin,
    require_org_access,
)
from open_webui.models.users import UserModel

# 组织管理路由（统一中文标签）
router = APIRouter(tags=["组织管理"])


@router.get(
    "/",
    response_model=PaginatedOrganizationResponse,
    summary="获取组织列表",
    description="分页获取组织列表，仅系统管理员可访问。参数：page（页码，>=1），size（页大小，1-100）。返回包含分页信息的组织列表。",
)
async def get_organizations(
    page: int = 1,
    size: int = 20,
    user: UserModel = Depends(require_system_admin),
):
    """获取组织列表（仅系统管理员）。"""
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    offset = (page - 1) * size
    organizations = Organizations.get_organizations(limit=size, offset=offset)
    total = Organizations.get_organizations_count()
    total_pages = (total + size - 1) // size

    return PaginatedOrganizationResponse(
        data=[OrganizationResponse(**org.model_dump()) for org in organizations],
        pagination=PaginationData(total=total, page=page, size=size, total_pages=total_pages),
    )


@router.post(
    "/",
    response_model=OrganizationResponse,
    summary="创建组织",
    description="创建新的组织，仅系统管理员可访问。重名将返回 400；内部错误返回 500。",
)
async def create_organization(
    form_data: OrganizationForm, user: UserModel = Depends(require_system_admin)
):
    """创建组织（仅系统管理员）。"""
    existing_org = Organizations.get_organization_by_name(form_data.name)
    if existing_org:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组织名称已存在")

    organization = Organizations.insert_new_organization(form_data)
    if not organization:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建组织失败")

    return OrganizationResponse(**organization.model_dump())


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="获取组织详情",
    description="按 ID 获取组织详情，需具备该组织的访问权限。未找到返回 404。",
)
async def get_organization_by_id(
    organization_id: str, user: UserModel = Depends(require_org_access)
):
    """获取组织详情。"""
    organization = Organizations.get_organization_by_id(organization_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组织不存在")

    return OrganizationResponse(**organization.model_dump())


@router.post(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="更新组织信息",
    description="更新指定组织的基础信息，需组织管理员或系统管理员权限。无权或不存在将返回 403/404。",
)
async def update_organization(
    organization_id: str,
    form_data: OrganizationUpdateForm,
    user: UserModel = Depends(require_org_admin),
):
    """更新组织信息（组织管理员）。"""
    if not user.is_super_admin and user.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该组织信息")

    organization = Organizations.get_organization_by_id(organization_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组织不存在")

    updated_organization = Organizations.update_organization_by_id(organization_id, form_data)
    if not updated_organization:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新组织失败")

    return OrganizationResponse(**updated_organization.model_dump())


@router.delete(
    "/{organization_id}",
    summary="删除组织",
    description="删除指定组织，仅系统管理员可访问。若组织下仍有关联用户或项目，将返回 400。",
)
async def delete_organization(
    organization_id: str, user: UserModel = Depends(require_system_admin)
):
    """删除组织（仅系统管理员）。"""
    organization = Organizations.get_organization_by_id(organization_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组织不存在")

    users = Users.get_users(organization_id=organization_id)
    if users and users.total > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组织下存在用户，无法删除")

    # TODO: 若需要校验组织下是否存在项目，请在模型层按组织维度实现查询

    result = Organizations.delete_organization_by_id(organization_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除组织失败")

    return {"message": "组织删除成功"}


@router.get(
    "/{organization_id}/users",
    response_model=UserListResponse,
    summary="获取组织用户列表",
    description="分页获取指定组织的用户列表，需组织访问权限。参数：page，size。",
)
async def get_organization_users(
    organization_id: str,
    page: int = 1,
    size: int = 20,
    user: UserModel = Depends(require_org_access),
):
    """获取组织下的用户列表。"""
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    offset = (page - 1) * size
    users_response = Users.get_users(skip=offset, limit=size, organization_id=organization_id)
    return users_response


@router.post(
    "/{organization_id}/users/{user_id}",
    summary="将用户加入组织",
    description="将指定用户加入组织并可设置其为组织管理员。需组织管理员或系统管理员权限。",
)
async def add_user_to_organization(
    organization_id: str,
    user_id: str,
    is_org_admin: bool = False,
    user: UserModel = Depends(require_org_admin),
):
    """将用户加入组织（组织管理员）。"""
    if not user.is_super_admin and user.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权管理该组织用户")

    target_user = Users.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    updated_user = Users.update_user_by_id(
        user_id,
        {"organization_id": organization_id, "is_org_admin": is_org_admin},
    )
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新用户失败")

    return {"message": "用户已成功加入组织"}


@router.delete(
    "/{organization_id}/users/{user_id}",
    summary="将用户从组织移除",
    description="从组织中移除指定用户，需组织管理员或系统管理员权限。不可移除自己。",
)
async def remove_user_from_organization(
    organization_id: str,
    user_id: str,
    user: UserModel = Depends(require_org_admin),
):
    """将用户从组织移除（组织管理员）。"""
    if not user.is_super_admin and user.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权管理该组织用户")

    target_user = Users.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能移除自己")

    updated_user = Users.update_user_by_id(user_id, {"organization_id": None, "is_org_admin": False})
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新用户失败")

    return {"message": "用户已成功从组织移除"}

