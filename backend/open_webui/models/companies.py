import time
import uuid
from typing import List, Optional

from open_webui.internal.db import Base, JSONField, get_db
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship


####################
# Company DB Schema
####################


class Company(Base):
    __tablename__ = "company"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    business_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class CompanyModel(BaseModel):
    """公司模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(description="公司唯一标识符")
    name: str = Field(description="公司名称")
    business_name: str = Field(description="业务名称")
    description: Optional[str] = Field(default=None, description="公司描述")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


####################
# Forms
####################


class CompanyForm(BaseModel):
    """公司表单模型"""
    name: str = Field(description="公司名称")
    business_name: str = Field(description="业务名称")
    description: Optional[str] = Field(default=None, description="公司描述")


class CompanyUpdateForm(CompanyForm):
    """公司更新表单模型"""
    pass


class CompaniesTable:
    def insert_new_company(self, form_data: CompanyForm) -> Optional[CompanyModel]:
        with get_db() as db:
            company = CompanyModel(
                **{
                    **form_data.model_dump(exclude_none=True),
                    "id": str(uuid.uuid4()),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Company(**company.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return CompanyModel.model_validate(result)
                else:
                    return None

            except Exception:
                return None

    def get_company_by_id(self, id: str) -> Optional[CompanyModel]:
        try:
            with get_db() as db:
                company = db.query(Company).filter_by(id=id).first()
                return CompanyModel.model_validate(company) if company else None
        except Exception:
            return None

    def get_company_by_business_name(self, business_name: str) -> Optional[CompanyModel]:
        try:
            with get_db() as db:
                company = db.query(Company).filter_by(business_name=business_name).first()
                return CompanyModel.model_validate(company) if company else None
        except Exception:
            return None

    def get_companies(self) -> List[CompanyModel]:
        with get_db() as db:
            companies = db.query(Company).all()
            return [CompanyModel.model_validate(company) for company in companies]

    def update_company_by_id(self, id: str, updated: dict) -> Optional[CompanyModel]:
        try:
            with get_db() as db:
                db.query(Company).filter_by(id=id).update(updated)
                db.commit()

                company = db.query(Company).filter_by(id=id).first()
                return CompanyModel.model_validate(company) if company else None
        except Exception:
            return None

    def delete_company_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Company).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False


Companies = CompaniesTable()