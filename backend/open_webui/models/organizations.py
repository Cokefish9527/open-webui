import logging
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, JSON, Boolean, ForeignKey

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Organizations DB Schema
####################


class Organization(Base):
    """组织表"""
    __tablename__ = "organizations"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # 组织管理员
    admin_user_id = Column(String, ForeignKey("user.id"), nullable=True)
    
    # 组织状态
    status = Column(String, default="active")
    
    # 组织配置
    config = Column(JSON, nullable=True)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic Models
####################


class OrganizationModel(BaseModel):
    """组织模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="组织唯一标识符")
    name: str = Field(description="组织名称")
    description: Optional[str] = Field(default=None, description="组织描述")
    admin_user_id: Optional[str] = Field(default=None, description="组织管理员用户ID")
    status: str = Field(default="active", description="组织状态")
    config: Optional[dict] = Field(default=None, description="组织配置")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


####################
# Forms
####################


class OrganizationForm(BaseModel):
    name: str
    description: Optional[str] = None
    config: Optional[dict] = None


class OrganizationUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    admin_user_id: Optional[str] = None
    status: Optional[str] = None
    config: Optional[dict] = None


####################
# Response Models
####################


class OrganizationResponse(BaseModel):
    id: str = Field(description="组织唯一标识符")
    name: str = Field(description="组织名称")
    description: Optional[str] = Field(default=None, description="组织描述")
    admin_user_id: Optional[str] = Field(default=None, description="组织管理员用户ID")
    status: str = Field(default="active", description="组织状态")
    config: Optional[dict] = Field(default=None, description="组织配置")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class PaginationData(BaseModel):
    """分页数据模型"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")


class PaginatedOrganizationResponse(BaseModel):
    """分页的组织响应模型"""
    data: List[OrganizationResponse] = Field(description="组织数据列表")
    pagination: PaginationData = Field(description="分页信息")


####################
# Database Tables
####################


class OrganizationsTable:
    def insert_new_organization(
        self, form_data: OrganizationForm, admin_user_id: Optional[str] = None
    ) -> Optional[OrganizationModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            organization = OrganizationModel(
                **{
                    "id": id,
                    "admin_user_id": admin_user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = Organization(**organization.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return OrganizationModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating organization: {e}")
                return None

    def get_organizations(
        self, 
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[OrganizationModel]:
        with get_db() as db:
            try:
                query = db.query(Organization)
                
                if status:
                    query = query.filter_by(status=status)
                    
                organizations = query.order_by(
                    Organization.updated_at.desc()
                ).limit(limit).offset(offset).all()
                
                return [OrganizationModel.model_validate(org) for org in organizations]
            except Exception as e:
                log.exception(f"Error getting organizations: {e}")
                return []

    def get_organizations_count(
        self, 
        status: Optional[str] = None
    ) -> int:
        """获取组织总数"""
        with get_db() as db:
            try:
                query = db.query(Organization)
                
                if status:
                    query = query.filter_by(status=status)
                    
                return query.count()
            except Exception as e:
                log.exception(f"Error counting organizations: {e}")
                return 0

    def get_organization_by_id(self, organization_id: str) -> Optional[OrganizationModel]:
        with get_db() as db:
            try:
                organization = db.get(Organization, organization_id)
                return OrganizationModel.model_validate(organization) if organization else None
            except Exception:
                return None

    def get_organization_by_name(self, name: str) -> Optional[OrganizationModel]:
        """
        根据组织名称查找组织
        """
        with get_db() as db:
            try:
                organization = db.query(Organization).filter_by(name=name).first()
                return OrganizationModel.model_validate(organization) if organization else None
            except Exception:
                return None

    def update_organization_by_id(
        self, organization_id: str, form_data: OrganizationUpdateForm
    ) -> Optional[OrganizationModel]:
        with get_db() as db:
            try:
                organization = db.get(Organization, organization_id)
                if organization:
                    update_data = form_data.model_dump(exclude_unset=True)
                    update_data["updated_at"] = int(time.time())
                    
                    for key, value in update_data.items():
                        setattr(organization, key, value)
                    
                    db.commit()
                    db.refresh(organization)
                    return OrganizationModel.model_validate(organization)
                return None
            except Exception as e:
                log.exception(f"Error updating organization: {e}")
                return None

    def delete_organization_by_id(self, organization_id: str) -> bool:
        """删除组织"""
        with get_db() as db:
            try:
                organization = db.get(Organization, organization_id)
                if organization:
                    db.delete(organization)
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error deleting organization: {e}")
                return False


# 全局实例
Organizations = OrganizationsTable()