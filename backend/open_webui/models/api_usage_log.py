import logging
import time
import uuid
from decimal import Decimal
from typing import Optional, List
from datetime import datetime

from open_webui.internal.db_n8n import N8NBase, get_n8n_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, Numeric, DateTime
from sqlalchemy.sql import func

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# API Usage Log DB Schema
####################


class APIUsageLog(N8NBase):
    """API使用记录表 - 用于记录第三方API调用的使用情况"""
    __tablename__ = "hsai_business_api_usage_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    session_id = Column(Text)
    service_provider = Column(String(100), nullable=False)
    model_name = Column(String(100))
    credits_consumed = Column(Numeric(12, 6), nullable=False, default=0)
    consumed_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


####################
# Pydantic Models
####################


class APIUsageLogModel(BaseModel):
    """API使用记录模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="记录唯一标识符")
    user_id: str = Field(description="用户ID")
    session_id: Optional[str] = Field(default=None, description="会话ID")
    service_provider: str = Field(description="服务提供商")
    model_name: Optional[str] = Field(default=None, description="模型名称")
    credits_consumed: Decimal = Field(default=Decimal("0"), description="消耗的积分数量")
    consumed_at: datetime = Field(description="消耗时间")


####################
# Forms
####################


class APIUsageLogForm(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    service_provider: str
    model_name: Optional[str] = None
    credits_consumed: Decimal = Decimal("0")


####################
# Response Models
####################


class APIUsageLogResponse(BaseModel):
    id: int = Field(description="记录唯一标识符")
    user_id: str = Field(description="用户ID")
    session_id: Optional[str] = Field(default=None, description="会话ID")
    service_provider: str = Field(description="服务提供商")
    model_name: Optional[str] = Field(default=None, description="模型名称")
    credits_consumed: Decimal = Field(default=Decimal("0"), description="消耗的积分数量")
    consumed_at: datetime = Field(description="消耗时间")


class APIUsageLogPaginationData(BaseModel):
    """API使用记录分页数据模型"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")


class PaginatedAPIUsageLogResponse(BaseModel):
    """分页的API使用记录响应模型"""
    data: List[APIUsageLogResponse] = Field(description="API使用记录数据列表")
    pagination: APIUsageLogPaginationData = Field(description="分页信息")


####################
# Database Tables
####################


class APIUsageLogsTable:
    def insert_new_log(
        self, form_data: APIUsageLogForm
    ) -> Optional[APIUsageLogModel]:
        with get_n8n_db() as db:
            try:
                # 创建API使用记录
                api_log = APIUsageLog(
                    user_id=form_data.user_id,
                    session_id=form_data.session_id,
                    service_provider=form_data.service_provider,
                    model_name=form_data.model_name,
                    credits_consumed=form_data.credits_consumed,
                    consumed_at=func.now()
                )
                
                db.add(api_log)
                db.commit()
                db.refresh(api_log)
                return APIUsageLogModel.model_validate(api_log) if api_log else None
            except Exception as e:
                log.exception(f"Error creating API usage log: {e}")
                db.rollback()
                return None

    def get_logs_by_session_id(
        self, session_id: str
    ) -> List[APIUsageLogModel]:
        """根据会话ID获取API使用记录"""
        with get_n8n_db() as db:
            try:
                logs = db.query(APIUsageLog).filter_by(session_id=session_id).all()
                return [APIUsageLogModel.model_validate(log) for log in logs]
            except Exception as e:
                log.exception(f"Error getting API usage logs by session_id: {e}")
                return []

    def get_total_credits_consumed_by_session(
        self, session_id: str
    ) -> Decimal:
        """根据会话ID获取总消耗积分"""
        with get_n8n_db() as db:
            try:
                result = db.query(func.sum(APIUsageLog.credits_consumed)).filter_by(session_id=session_id).scalar()
                return result if result else Decimal("0")
            except Exception as e:
                log.exception(f"Error getting total credits consumed by session_id: {e}")
                return Decimal("0")

    def get_logs_by_user_id(
        self, 
        user_id: str, 
        limit: int = 20,
        offset: int = 0
    ) -> List[APIUsageLogModel]:
        """根据用户ID获取API使用记录"""
        with get_n8n_db() as db:
            try:
                logs = db.query(APIUsageLog).filter_by(user_id=user_id).order_by(
                    APIUsageLog.consumed_at.desc()
                ).limit(limit).offset(offset).all()
                return [APIUsageLogModel.model_validate(log) for log in logs]
            except Exception as e:
                log.exception(f"Error getting API usage logs by user_id: {e}")
                return []

    def get_logs_count_by_user_id(
        self, user_id: str
    ) -> int:
        """获取用户API使用记录总数"""
        with get_n8n_db() as db:
            try:
                return db.query(APIUsageLog).filter_by(user_id=user_id).count()
            except Exception as e:
                log.exception(f"Error counting API usage logs by user_id: {e}")
                return 0


# 全局实例
APIUsageLogs = APIUsageLogsTable()
