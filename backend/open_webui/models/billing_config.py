import logging
import time
import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import BigInteger, Column, String, Text, JSON

from ._timestamp_utils import normalize_required_timestamp

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Billing Config DB Schema
####################


class BillingConfig(Base):
    """计费配置表 - 用于存储计费比率等配置信息"""
    __tablename__ = "billing_config"

    id = Column(String, primary_key=True)
    config_type = Column(String, nullable=False)  # 配置类型：resource
    config_key = Column(String, nullable=False)   # 配置键名
    config_value = Column(JSON, nullable=False)   # 配置值
    description = Column(Text)                    # 配置描述
    is_active = Column(String, default="1")      # 是否启用
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic Models
####################


class BillingConfigModel(BaseModel):
    """计费配置模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="配置唯一标识符")
    config_type: str = Field(description="配置类型")
    config_key: str = Field(description="配置键名")
    config_value: Dict[str, Any] = Field(description="配置值")
    description: Optional[str] = Field(default=None, description="配置描述")
    is_active: bool = Field(default=True, description="是否启用")
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


class BillingConfigForm(BaseModel):
    config_type: str
    config_key: str
    config_value: Dict[str, Any]
    description: Optional[str] = None
    is_active: bool = True


class BillingConfigUpdateForm(BaseModel):
    config_type: Optional[str] = None
    config_key: Optional[str] = None
    config_value: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


####################
# Response Models
####################


class BillingConfigResponse(BaseModel):
    id: str = Field(description="配置唯一标识符")
    config_type: str = Field(description="配置类型")
    config_key: str = Field(description="配置键名")
    config_value: Dict[str, Any] = Field(description="配置值")
    description: Optional[str] = Field(default=None, description="配置描述")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class PaginationData(BaseModel):
    """分页数据模型"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")


class PaginatedBillingConfigResponse(BaseModel):
    """分页的计费配置响应模型"""
    data: List[BillingConfigResponse] = Field(description="计费配置数据列表")
    pagination: PaginationData = Field(description="分页信息")


####################
# Database Tables
####################


class BillingConfigsTable:
    def insert_new_config(
        self, form_data: BillingConfigForm
    ) -> Optional[BillingConfigModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            config = BillingConfigModel(
                **{
                    "id": id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = BillingConfig(
                    id=config.id,
                    config_type=config.config_type,
                    config_key=config.config_key,
                    config_value=config.config_value,
                    description=config.description,
                    is_active="1" if config.is_active else "0",
                    created_at=config.created_at,
                    updated_at=config.updated_at
                )
                db.add(result)
                db.commit()
                db.refresh(result)
                return BillingConfigModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating billing config: {e}")
                db.rollback()
                return None

    def get_config_by_type_and_key(
        self, config_type: str, config_key: str
    ) -> Optional[BillingConfigModel]:
        """根据配置类型和键名获取计费配置"""
        with get_db() as db:
            try:
                config = db.query(BillingConfig).filter_by(
                    config_type=config_type, 
                    config_key=config_key,
                    is_active="1"
                ).first()
                return BillingConfigModel.model_validate(config) if config else None
            except Exception as e:
                log.exception(f"Error getting billing config by type and key: {e}")
                return None

    def get_billing_rate(self, config_type: str, config_key: str) -> Decimal:
        """获取计费比率"""
        config = self.get_config_by_type_and_key(config_type, config_key)
        
        if config:
            rate_str = config.config_value.get("rate", "0")
            try:
                return Decimal(rate_str)
            except:
                return Decimal("0")
        return Decimal("0")

    def get_configs(
        self, 
        config_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[BillingConfigModel]:
        """获取计费配置列表"""
        with get_db() as db:
            try:
                query = db.query(BillingConfig)
                
                if config_type:
                    query = query.filter_by(config_type=config_type)
                    
                if is_active is not None:
                    query = query.filter_by(is_active="1" if is_active else "0")
                    
                configs = query.order_by(
                    BillingConfig.updated_at.desc()
                ).limit(limit).offset(offset).all()
                
                return [BillingConfigModel.model_validate(config) for config in configs]
            except Exception as e:
                log.exception(f"Error getting billing configs: {e}")
                return []

    def get_configs_count(
        self, 
        config_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """获取计费配置总数"""
        with get_db() as db:
            try:
                query = db.query(BillingConfig)
                
                if config_type:
                    query = query.filter_by(config_type=config_type)
                    
                if is_active is not None:
                    query = query.filter_by(is_active="1" if is_active else "0")
                    
                return query.count()
            except Exception as e:
                log.exception(f"Error counting billing configs: {e}")
                return 0

    def get_config_by_id(self, config_id: str) -> Optional[BillingConfigModel]:
        """根据ID获取计费配置"""
        with get_db() as db:
            try:
                config = db.get(BillingConfig, config_id)
                return BillingConfigModel.model_validate(config) if config else None
            except Exception:
                return None

    def update_config_by_id(
        self, config_id: str, form_data: BillingConfigUpdateForm
    ) -> Optional[BillingConfigModel]:
        """更新计费配置"""
        with get_db() as db:
            try:
                config = db.get(BillingConfig, config_id)
                if config:
                    update_data = form_data.model_dump(exclude_unset=True)
                    for key, value in update_data.items():
                        if key == "is_active":
                            setattr(config, key, "1" if value else "0")
                        else:
                            setattr(config, key, value)
                    setattr(config, 'updated_at', int(time.time()))
                    
                    db.commit()
                    db.refresh(config)
                    return BillingConfigModel.model_validate(config)
                return None
            except Exception as e:
                log.exception(f"Error updating billing config: {e}")
                db.rollback()
                return None

    def delete_config_by_id(self, config_id: str) -> bool:
        """删除计费配置"""
        with get_db() as db:
            try:
                config = db.get(BillingConfig, config_id)
                if config:
                    db.delete(config)
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error deleting billing config: {e}")
                db.rollback()
                return False


# 全局实例
BillingConfigs = BillingConfigsTable()
