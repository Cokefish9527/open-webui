from typing import Optional
from fastapi import HTTPException, status, Depends

from open_webui.models.users import Users, UserModel
from open_webui.models.organizations import Organizations
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_current_user


def require_system_admin(user: Optional[UserModel] = Depends(get_current_user)):
    """
    验证用户是否为系统管理员
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要系统管理员权限",
        )
    
    return user


def require_org_admin(user: Optional[UserModel] = Depends(get_current_user)):
    """
    验证用户是否为组织管理员或系统管理员
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    if not user.is_super_admin and not user.is_org_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要组织管理员权限",
        )
    
    return user


def require_org_access(organization_id: str, user: Optional[UserModel] = Depends(get_current_user)):
    """
    验证用户是否有权访问指定组织
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    # 系统管理员可以访问所有组织
    if user.is_super_admin:
        return user
    
    # 检查用户是否属于该组织
    if user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该组织资源",
        )
    
    return user


def filter_by_organization(query, model_class, user: UserModel):
    """
    根据用户权限过滤查询结果
    """
    # 系统管理员可以查看所有数据
    if user.is_super_admin:
        return query
    
    # 组织管理员和普通用户只能查看自己组织的数据
    return query.filter(model_class.organization_id == user.organization_id)


def check_user_org_access(user_id: str, current_user: UserModel) -> bool:
    """
    检查当前用户是否有权访问指定用户的数据
    """
    # 系统管理员可以访问所有用户
    if current_user.is_super_admin:
        return True
    
    # 获取目标用户信息
    target_user = Users.get_user_by_id(user_id)
    if not target_user:
        return False
    
    # 组织管理员和普通用户只能访问同组织的用户
    return target_user.organization_id == current_user.organization_id


def get_user_organizations(user: UserModel):
    """
    获取用户可以访问的组织列表
    """
    # 系统管理员可以访问所有组织
    if user.is_super_admin:
        return Organizations.get_organizations()
    
    # 组织管理员和普通用户只能访问自己的组织
    if user.organization_id:
        org = Organizations.get_organization_by_id(user.organization_id)
        return [org] if org else []
    return []


def validate_organization_access(organization_id: str, user: UserModel) -> bool:
    """
    验证用户对组织的访问权限
    """
    # 系统管理员可以访问所有组织
    if user.is_super_admin:
        return True
    
    # 检查用户是否属于该组织
    return user.organization_id == organization_id