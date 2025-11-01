import logging
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import BigInteger, Column, String, Text, JSON
from ._timestamp_utils import (
    normalize_optional_timestamp,
    normalize_required_timestamp,
    EpochTimestamp,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Redis Queue Messages DB Schema
####################


class RedisQueueMessage(Base):
    """Redis队列消息表"""
    __tablename__ = "redis_queue_messages"

    id = Column(String, primary_key=True)
    queue_name = Column(String, nullable=False)  # Redis队列名称
    correlation_id = Column(String, nullable=True)  # 关联ID（request_id/reply_id）
    raw_data = Column(Text, nullable=False)      # 获取到的原始数据
    fetched_at = Column(EpochTimestamp(), nullable=False)  # 获取时间
    execution_result = Column(Text, nullable=True)   # 执行结果
    error_message = Column(Text, nullable=True)      # 异常信息
    last_executed_at = Column(BigInteger, nullable=True)  # 最后一次执行时间
    status = Column(String, nullable=False, default="pending")  # 消息处理状态
    retry_count = Column(BigInteger, default=0)  # 重试次数
    created_at = Column(EpochTimestamp())
    updated_at = Column(EpochTimestamp())


####################
# Pydantic Models
####################


class RedisQueueMessageModel(BaseModel):
    """Redis队列消息模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="消息唯一标识符")
    queue_name: str = Field(description="Redis队列名称")
    correlation_id: Optional[str] = Field(default=None, description="关联ID（request_id/reply_id）")
    raw_data: str = Field(description="获取到的原始数据")
    fetched_at: int = Field(description="获取时间")
    execution_result: Optional[str] = Field(default=None, description="执行结果")
    error_message: Optional[str] = Field(default=None, description="异常信息")
    last_executed_at: Optional[int] = Field(default=None, description="最后一次执行时间")
    status: str = Field(default="pending", description="消息处理状态")
    retry_count: int = Field(default=0, description="重试次数")
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

    @field_validator("fetched_at", "last_executed_at", mode="before")
    @classmethod
    def validate_optional_timestamps(cls, value):
        if value is None:
            return None
        try:
            return normalize_optional_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid optional timestamp value: {exc}") from exc


####################
# Forms
####################


class RedisQueueMessageForm(BaseModel):
    queue_name: str
    raw_data: str
    fetched_at: Optional[int] = None
    execution_result: Optional[str] = None
    error_message: Optional[str] = None
    last_executed_at: Optional[int] = None
    status: Optional[str] = "pending"
    retry_count: Optional[int] = 0
    correlation_id: Optional[str] = None


class RedisQueueMessageUpdateForm(BaseModel):
    execution_result: Optional[str] = None
    error_message: Optional[str] = None
    last_executed_at: Optional[int] = None
    status: Optional[str] = None
    retry_count: Optional[int] = None


####################
# Response Models
####################


class RedisQueueMessageResponse(BaseModel):
    id: str = Field(description="消息唯一标识符")
    queue_name: str = Field(description="Redis队列名称")
    correlation_id: Optional[str] = Field(default=None, description="关联ID（request_id/reply_id）")
    raw_data: str = Field(description="获取到的原始数据")
    fetched_at: int = Field(description="获取时间")
    execution_result: Optional[str] = Field(default=None, description="执行结果")
    error_message: Optional[str] = Field(default=None, description="异常信息")
    last_executed_at: Optional[int] = Field(default=None, description="最后一次执行时间")
    status: str = Field(description="消息处理状态")
    retry_count: int = Field(description="重试次数")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class PaginationData(BaseModel):
    """分页数据模型"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")


class PaginatedRedisQueueMessageResponse(BaseModel):
    """分页的Redis队列消息响应模型"""
    data: List[RedisQueueMessageResponse] = Field(description="消息数据列表")
    pagination: PaginationData = Field(description="分页信息")


####################
# Database Tables
####################


class RedisQueueMessagesTable:
    def insert_new_message(
        self, form_data: RedisQueueMessageForm
    ) -> Optional[RedisQueueMessageModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            # 如果没有提供获取时间，则使用当前时间
            fetched_at = form_data.fetched_at or int(time.time())
            
            message = RedisQueueMessageModel(
                **{
                    "id": id,
                    **form_data.model_dump(),
                    "fetched_at": fetched_at,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = RedisQueueMessage(**message.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return RedisQueueMessageModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating redis queue message: {e}")
                return None

    def get_message_by_id(self, message_id: str) -> Optional[RedisQueueMessageModel]:
        with get_db() as db:
            try:
                message = db.get(RedisQueueMessage, message_id)
                return RedisQueueMessageModel.model_validate(message) if message else None
            except Exception:
                return None

    def get_message_by_correlation_id(self, correlation_id: str) -> Optional[RedisQueueMessageModel]:
        """根据 correlation_id 获取消息记录"""
        if not correlation_id:
            return None
        with get_db() as db:
            try:
                message = db.query(RedisQueueMessage).filter_by(correlation_id=correlation_id).order_by(RedisQueueMessage.created_at.desc()).first()
                return RedisQueueMessageModel.model_validate(message) if message else None
            except Exception:
                return None

    def get_messages_by_queue_name(
        self, 
        queue_name: str, 
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RedisQueueMessageModel]:
        """根据队列名称获取消息"""
        with get_db() as db:
            try:
                query = db.query(RedisQueueMessage).filter_by(queue_name=queue_name)
                
                if status:
                    query = query.filter_by(status=status)
                    
                messages = query.order_by(
                    RedisQueueMessage.created_at.desc()
                ).limit(limit).offset(offset).all()
                
                return [RedisQueueMessageModel.model_validate(msg) for msg in messages]
            except Exception as e:
                log.exception(f"Error getting messages by queue name: {e}")
                return []

    def get_failed_messages(
        self, 
        queue_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RedisQueueMessageModel]:
        """获取失败的消息"""
        with get_db() as db:
            try:
                query = db.query(RedisQueueMessage).filter_by(status="failed")
                
                if queue_name:
                    query = query.filter_by(queue_name=queue_name)
                    
                messages = query.order_by(
                    RedisQueueMessage.created_at.desc()
                ).limit(limit).offset(offset).all()
                
                return [RedisQueueMessageModel.model_validate(msg) for msg in messages]
            except Exception as e:
                log.exception(f"Error getting failed messages: {e}")
                return []

    def update_message_by_id(
        self, message_id: str, form_data: RedisQueueMessageUpdateForm
    ) -> Optional[RedisQueueMessageModel]:
        """更新消息状态"""
        with get_db() as db:
            try:
                message = db.get(RedisQueueMessage, message_id)
                if message:
                    # 更新提供的字段
                    for key, value in form_data.model_dump(exclude_unset=True).items():
                        setattr(message, key, value)
                    
                    # 更新时间戳
                    setattr(message, 'updated_at', int(time.time()))
                    
                    db.commit()
                    db.refresh(message)
                    return RedisQueueMessageModel.model_validate(message)
                return None
            except Exception as e:
                log.exception(f"Error updating message: {e}")
                return None

    def increment_retry_count(self, message_id: str) -> bool:
        """增加重试次数"""
        with get_db() as db:
            try:
                message = db.get(RedisQueueMessage, message_id)
                if message:
                    setattr(message, 'retry_count', getattr(message, 'retry_count', 0) + 1)
                    setattr(message, 'updated_at', int(time.time()))
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error incrementing retry count: {e}")
                return False

    def get_messages_count(
        self, 
        queue_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """获取消息总数"""
        with get_db() as db:
            try:
                query = db.query(RedisQueueMessage)
                
                if queue_name:
                    query = query.filter_by(queue_name=queue_name)
                if status:
                    query = query.filter_by(status=status)
                    
                return query.count()
            except Exception as e:
                log.exception(f"Error counting messages: {e}")
                return 0

    def delete_message_by_id(self, message_id: str) -> bool:
        """删除消息"""
        with get_db() as db:
            try:
                message = db.get(RedisQueueMessage, message_id)
                if message:
                    db.delete(message)
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error deleting message: {e}")
                return False


# 全局实例
RedisQueueMessages = RedisQueueMessagesTable()
