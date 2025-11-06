import logging
import time
import uuid
from typing import Optional, List, Dict, Any

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, String, Text, JSON, ForeignKey, Integer
from sqlalchemy.orm import relationship

from ._timestamp_utils import normalize_required_timestamp, EpochTimestamp

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# HSAI Projects DB Schema
####################


class HSAIProject(Base):
    """HSAI项目表"""
    __tablename__ = "hsai_projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    business_name = Column(String, nullable=False)
    company_info = Column(JSON, nullable=True)
    user_id = Column(String, nullable=False)
    status = Column(String, default="active")
    config = Column(JSON, nullable=True)
    # 添加公司关联字段
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)
    created_at = Column(EpochTimestamp())
    updated_at = Column(EpochTimestamp())


####################
# Pydantic Models
####################


class HSAIProjectModel(BaseModel):
    """HSAI项目模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="项目唯一标识符")
    name: str = Field(description="项目名称")
    description: Optional[str] = Field(default=None, description="项目描述")
    business_name: str = Field(description="企业名称")
    company_info: Optional[dict] = Field(default=None, description="企业信息")
    user_id: str = Field(description="用户ID")
    status: str = Field(default="active", description="项目状态")
    config: Optional[dict] = Field(default=None, description="项目配置")
    # 添加公司关联字段
    company_id: Optional[str] = Field(default=None, description="所属公司ID")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_required_timestamps(cls, value):
        if value is None:
            raise ValueError("Timestamp value cannot be None")
        try:
            return normalize_required_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp value: {exc}") from exc


####################
# Forms
####################


class HSAIProjectForm(BaseModel):
    name: str
    description: Optional[str] = None
    business_name: str
    company_info: Optional[dict] = None
    config: Optional[dict] = None


class HSAIProjectUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    business_name: Optional[str] = None
    company_info: Optional[dict] = None
    status: Optional[str] = None
    config: Optional[dict] = None


####################
# Response Models
####################


class HSAIProjectResponse(BaseModel):
    id: str = Field(description="项目唯一标识符")
    name: str = Field(description="项目名称")
    description: Optional[str] = Field(default=None, description="项目描述")
    business_name: str = Field(description="企业名称")
    company_info: Optional[dict] = Field(default=None, description="企业信息")
    status: str = Field(default="active", description="项目状态")
    config: Optional[dict] = Field(default=None, description="项目配置")
    # 添加公司关联字段
    company_id: Optional[str] = Field(default=None, description="所属公司ID")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class PaginationData(BaseModel):
    """分页数据模型"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")


class PaginatedHSAIProjectResponse(BaseModel):
    """分页的项目响应模型"""
    data: List[HSAIProjectResponse] = Field(description="项目数据列表")
    pagination: PaginationData = Field(description="分页信息")


####################
# Database Tables
####################


class HSAIProjectsTable:
    def insert_new_project(
        self, user_id: str, form_data: HSAIProjectForm
    ) -> Optional[HSAIProjectModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            project = HSAIProjectModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = HSAIProject(**project.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return HSAIProjectModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating project: {e}")
                return None

    def get_projects_by_user_id(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[HSAIProjectModel]:
        with get_db() as db:
            try:
                query = db.query(HSAIProject).filter_by(user_id=user_id)

                if status:
                    query = query.filter_by(status=status)
                    
                projects = query.order_by(
                    HSAIProject.updated_at.desc()
                ).limit(limit).offset(offset).all()
                
                return [HSAIProjectModel.model_validate(project) for project in projects]
            except Exception as e:
                log.exception(f"Error getting projects: {e}")
                return []

    def get_projects_count(
        self,
        user_id: str,
        status: Optional[str] = None,
    ) -> int:
        """获取项目总数"""
        with get_db() as db:
            try:
                query = db.query(HSAIProject).filter_by(user_id=user_id)

                if status:
                    query = query.filter_by(status=status)
                    
                return query.count()
            except Exception as e:
                log.exception(f"Error counting projects: {e}")
                return 0

    def get_project_by_id(self, project_id: str) -> Optional[HSAIProjectModel]:
        with get_db() as db:
            try:
                project = db.query(HSAIProject).filter_by(id=project_id).first()
                return HSAIProjectModel.model_validate(project) if project else None
            except Exception:
                return None

    def get_projects_by_company_id(
        self, 
        company_id: str, 
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[HSAIProjectModel]:
        """根据公司ID获取项目列表"""
        with get_db() as db:
            try:
                query = db.query(HSAIProject).filter_by(company_id=company_id)
                
                if status:
                    query = query.filter_by(status=status)
                    
                projects = query.order_by(
                    HSAIProject.updated_at.desc()
                ).limit(limit).offset(offset).all()
                
                return [HSAIProjectModel.model_validate(project) for project in projects]
            except Exception as e:
                log.exception(f"Error getting projects by company id: {e}")
                return []

    def get_projects_by_company_name(
        self, 
        company_name: str, 
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[HSAIProjectModel]:
        """根据公司名称获取项目列表"""
        with get_db() as db:
            try:
                # 先根据公司名称查找公司
                from open_webui.models.hsai_companies import Companies
                company = Companies.get_company_by_name(company_name)
                if not company:
                    return []
                
                query = db.query(HSAIProject).filter_by(company_id=company.id)
                
                if status:
                    query = query.filter_by(status=status)
                    
                projects = query.order_by(
                    HSAIProject.updated_at.desc()
                ).limit(limit).offset(offset).all()
                
                return [HSAIProjectModel.model_validate(project) for project in projects]
            except Exception as e:
                log.exception(f"Error getting projects by company name: {e}")
                return []

    def get_projects_count_by_company_id(
        self, 
        company_id: str, 
        status: Optional[str] = None
    ) -> int:
        """根据公司ID获取项目总数"""
        with get_db() as db:
            try:
                query = db.query(HSAIProject).filter_by(company_id=company_id)
                
                if status:
                    query = query.filter_by(status=status)
                    
                return query.count()
            except Exception as e:
                log.exception(f"Error counting projects by company id: {e}")
                return 0

    def update_project_by_id(
        self, project_id: str, form_data: HSAIProjectUpdateForm
    ) -> Optional[HSAIProjectModel]:
        with get_db() as db:
            try:
                project = db.get(HSAIProject, project_id)
                if project:
                    for key, value in form_data.model_dump(exclude_unset=True).items():
                        setattr(project, key, value)
                    setattr(project, 'updated_at', int(time.time()))
                    
                    db.commit()
                    db.refresh(project)
                    return HSAIProjectModel.model_validate(project)
                return None
            except Exception as e:
                log.exception(f"Error updating project: {e}")
                return None

    def delete_project_by_id(self, project_id: str) -> bool:
        """删除项目"""
        with get_db() as db:
            try:
                project = db.get(HSAIProject, project_id)
                if project:
                    db.delete(project)
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error deleting project: {e}")
                return False


# 全局实例
HSAIProjects = HSAIProjectsTable()
