import logging
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, String, Text, JSON, ForeignKey

from ._timestamp_utils import normalize_required_timestamp, EpochTimestamp

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# HSAI Companies DB Schema
####################


class Company(Base):
    """公司表"""
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_user_id = Column(String, nullable=False)
    company_info = Column(JSON, nullable=True)
    status = Column(String, default="active")
    config = Column(JSON, nullable=True)
    created_at = Column(EpochTimestamp())
    updated_at = Column(EpochTimestamp())


####################
# Pydantic Models
####################


class CompanyModel(BaseModel):
    """公司模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="公司唯一标识符")
    name: str = Field(description="公司名称")
    description: Optional[str] = Field(default=None, description="公司描述")
    owner_user_id: str = Field(description="公司负责人用户ID")
    company_info: Optional[dict] = Field(default=None, description="公司详细信息")
    status: str = Field(default="active", description="公司状态")
    config: Optional[dict] = Field(default=None, description="公司配置")
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


class CompanyForm(BaseModel):
    name: str
    description: Optional[str] = None
    company_info: Optional[dict] = None
    config: Optional[dict] = None
    owner_user_id: Optional[str] = None


class CompanyUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    company_info: Optional[dict] = None
    status: Optional[str] = None
    config: Optional[dict] = None
    owner_user_id: Optional[str] = None


####################
# Response Models
####################


class CompanyResponse(BaseModel):
    id: str = Field(description="公司唯一标识符")
    name: str = Field(description="公司名称")
    description: Optional[str] = Field(default=None, description="公司描述")
    owner_user_id: str = Field(description="公司负责人用户ID")
    company_info: Optional[dict] = Field(default=None, description="公司详细信息")
    status: str = Field(default="active", description="公司状态")
    config: Optional[dict] = Field(default=None, description="公司配置")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class PaginationData(BaseModel):
    """分页数据模型"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")


class PaginatedCompanyResponse(BaseModel):
    """分页的公司响应模型"""
    data: List[CompanyResponse] = Field(description="公司数据列表")
    pagination: PaginationData = Field(description="分页信息")


####################
# Database Tables
####################


class CompaniesTable:
    def insert_new_company(
        self, owner_user_id: str, form_data: CompanyForm
    ) -> Optional[CompanyModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            form_payload = form_data.model_dump(exclude_unset=True)
            explicit_owner = form_payload.pop("owner_user_id", None)
            company = CompanyModel(
                **{
                    "id": id,
                    "owner_user_id": explicit_owner or owner_user_id,
                    **form_payload,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = Company(**company.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return CompanyModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating company: {e}")
                return None

    def get_companies_by_owner_user_id(
        self, 
        owner_user_id: str, 
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[CompanyModel]:
        with get_db() as db:
            try:
                query = db.query(Company).filter_by(owner_user_id=owner_user_id)
                
                if status:
                    query = query.filter_by(status=status)
                    
                companies = query.order_by(
                    Company.updated_at.desc()
                ).limit(limit).offset(offset).all()
                
                return [CompanyModel.model_validate(company) for company in companies]
            except Exception as e:
                log.exception(f"Error getting companies: {e}")
                return []

    def get_companies_count(
        self, 
        owner_user_id: str, 
        status: Optional[str] = None
    ) -> int:
        """获取公司总数"""
        with get_db() as db:
            try:
                query = db.query(Company).filter_by(owner_user_id=owner_user_id)
                
                if status:
                    query = query.filter_by(status=status)
                    
                return query.count()
            except Exception as e:
                log.exception(f"Error counting companies: {e}")
                return 0

    def get_company_by_id(self, company_id: str) -> Optional[CompanyModel]:
        with get_db() as db:
            try:
                company = db.get(Company, company_id)
                return CompanyModel.model_validate(company) if company else None
            except Exception:
                return None

    def get_company_by_name(self, name: str) -> Optional[CompanyModel]:
        """
        根据公司名称查找公司
        """
        with get_db() as db:
            try:
                company = db.query(Company).filter_by(name=name).first()
                return CompanyModel.model_validate(company) if company else None
            except Exception:
                return None

    def update_company_by_id(
        self, company_id: str, form_data: CompanyUpdateForm
    ) -> Optional[CompanyModel]:
        with get_db() as db:
            try:
                company = db.get(Company, company_id)
                if company:
                    payload = form_data.model_dump(exclude_unset=True)
                    owner_override = payload.pop("owner_user_id", None)
                    for key, value in payload.items():
                        setattr(company, key, value)
                    if owner_override:
                        company.owner_user_id = owner_override
                    company.updated_at = int(time.time())
                    
                    db.commit()
                    db.refresh(company)
                    return CompanyModel.model_validate(company)
                return None
            except Exception as e:
                log.exception(f"Error updating company: {e}")
                return None

    def delete_company_by_id(self, company_id: str) -> bool:
        """删除公司"""
        with get_db() as db:
            try:
                company = db.get(Company, company_id)
                if company:
                    db.delete(company)
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error deleting company: {e}")
                return False

    def get_all_companies(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CompanyModel]:
        """获取所有公司列表"""
        with get_db() as db:
            try:
                query = db.query(Company)
                if status:
                    query = query.filter_by(status=status)

                companies = (
                    query.order_by(Company.updated_at.desc())
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                return [CompanyModel.model_validate(company) for company in companies]
            except Exception as e:
                log.exception(f"Error getting all companies: {e}")
                return []

    def get_all_companies_count(self, status: Optional[str] = None) -> int:
        """统计公司数量"""
        with get_db() as db:
            try:
                query = db.query(Company)
                if status:
                    query = query.filter_by(status=status)
                return query.count()
            except Exception as e:
                log.exception(f"Error counting all companies: {e}")
                return 0


# 全局实例
Companies = CompaniesTable()
