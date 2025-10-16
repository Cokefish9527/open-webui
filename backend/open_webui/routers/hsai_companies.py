import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from open_webui.models.hsai_companies import (
    Companies,
    CompanyForm,
    CompanyUpdateForm,
    CompanyResponse,
    PaginatedCompanyResponse
)

from open_webui.models.hsai_projects import (
    HSAIProjects,
    HSAIProjectResponse,
    PaginatedHSAIProjectResponse,
    PaginationData
)

from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/companies", tags=["HSAI 公司管理"])


@router.get("/", response_model=PaginatedCompanyResponse, summary="获取公司列表")
async def get_companies(
    company_status: Optional[str] = Query(None, description="公司状态过滤"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取用户创建的公司列表（分页）。
    
    Args:
        status (Optional[str]): 公司状态过滤
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedCompanyResponse: 分页的公司列表
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        companies = Companies.get_companies_by_owner_user_id(
            user.id,
            status=company_status,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = Companies.get_companies_count(
            user.id,
            status=company_status
        )
        
        responses = [CompanyResponse(**company.model_dump()) for company in companies]
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedCompanyResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting companies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/", response_model=CompanyResponse, summary="创建公司")
async def create_company(
    form_data: CompanyForm,
    user=Depends(get_verified_user)
):
    """
    创建新的公司。
    
    Args:
        form_data (CompanyForm): 公司创建表单
        user: 已认证的用户对象
        
    Returns:
        CompanyResponse: 创建的公司信息
    """
    try:
        company = Companies.insert_new_company(user.id, form_data)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create company"
            )
        
        return CompanyResponse(**company.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating company: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{company_id}", response_model=CompanyResponse, summary="获取公司详情")
async def get_company(
    company_id: str,
    user=Depends(get_verified_user)
):
    """获取单个公司详情"""
    try:
        company = Companies.get_company_by_id(company_id)
        if not company or company.owner_user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        return CompanyResponse(**company.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting company: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/{company_id}", response_model=CompanyResponse, summary="更新公司")
async def update_company(
    company_id: str,
    form_data: CompanyUpdateForm,
    user=Depends(get_verified_user)
):
    """更新公司"""
    try:
        # 验证公司所有权
        existing_company = Companies.get_company_by_id(company_id)
        if not existing_company or existing_company.owner_user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        company = Companies.update_company_by_id(company_id, form_data)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update company"
            )
        
        return CompanyResponse(**company.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating company: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.delete("/{company_id}", response_model=bool, summary="删除公司")
async def delete_company(
    company_id: str,
    user=Depends(get_verified_user)
):
    """删除公司"""
    try:
        # 验证公司所有权
        existing_company = Companies.get_company_by_id(company_id)
        if not existing_company or existing_company.owner_user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        result = Companies.delete_company_by_id(company_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete company"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error deleting company: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{company_id}/projects", response_model=PaginatedHSAIProjectResponse, summary="获取公司项目列表")
async def get_company_projects(
    company_id: str,
    status: Optional[str] = Query(None, description="项目状态过滤"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取指定公司的项目列表（分页）。
    
    Args:
        company_id (str): 公司ID
        status (Optional[str]): 项目状态过滤
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAIProjectResponse: 分页的项目列表
    """
    try:
        # 验证公司所有权
        company = Companies.get_company_by_id(company_id)
        if not company or company.owner_user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        # 计算offset
        offset = (pi - 1) * ps
        
        projects = HSAIProjects.get_projects_by_company_id(
            company_id,
            status=status,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = HSAIProjects.get_projects_count_by_company_id(
            company_id,
            status=status
        )
        
        responses = [HSAIProjectResponse(**project.model_dump()) for project in projects]
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIProjectResponse(
            data=responses,
            pagination=pagination
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting company projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )