import logging
import time
from typing import Optional, List
from enum import Enum

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, String, Text, Integer
from ._timestamp_utils import normalize_required_timestamp, EpochTimestamp

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# HSAI Video Learning Status DB Schema
####################


class HSAIVideoLearningStatusEnum(str, Enum):
    """视频学习状态枚举"""
    LEARNING = "learning"      # Learning
    LEARNED = "learned"       # Learned
    ABANDONED = "abandoned"     # Abandoned
    # Note: Pending status is not stored in the table, but determined during query


class HSAIVideoLearningStatus(Base):
    """HSAI视频学习状态表"""
    __tablename__ = "hsai_video_learning_status"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 自增主键
    business_name = Column(String, nullable=False)              # 公司名称
    video_id = Column(String, nullable=False)                   # 学习的视频ID
    status = Column(String, nullable=False)                     # 学习状态
    
    # 时间戳
    created_at = Column(EpochTimestamp())
    updated_at = Column(EpochTimestamp())


####################
# Pydantic Models
####################


class HSAIVideoLearningStatusModel(BaseModel):
    """HSAI视频学习状态模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Auto-increment primary key")
    business_name: str = Field(description="Business name")
    video_id: str = Field(description="Video ID")
    status: str = Field(description="Learning status: learning, learned, abandoned")
    
    # Timestamps
    created_at: int = Field(description="Creation timestamp")
    updated_at: int = Field(description="Update timestamp")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_required_timestamps(cls, value):
        if value is None:
            raise ValueError("Timestamp value cannot be None")
        try:
            return normalize_required_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp value: {exc}") from exc


class HSAIVideoLearningStatusForm(BaseModel):
    """HSAI视频学习状态表单模型"""
    model_config = ConfigDict(from_attributes=True)

    business_name: str = Field(description="Business name")
    video_id: str = Field(description="Video ID")
    status: str = Field(description="Learning status: learning, learned, abandoned")


class HSAIVideoLearningStatusTable:
    """HSAI视频学习状态表操作类"""
    
    def insert_new_status(self, form_data: dict) -> Optional[HSAIVideoLearningStatusModel]:
        """插入新的视频学习状态记录"""
        with get_db() as db:
            status = HSAIVideoLearningStatus(
                **{
                    **form_data,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            db.add(status)
            db.commit()
            db.refresh(status)
            
            return HSAIVideoLearningStatusModel.model_validate(status) if status else None
    
    def get_status_by_video_id(self, video_id: str) -> Optional[HSAIVideoLearningStatusModel]:
        """根据视频ID获取学习状态"""
        with get_db() as db:
            status = db.query(HSAIVideoLearningStatus).filter(HSAIVideoLearningStatus.video_id == video_id).first()
            return HSAIVideoLearningStatusModel.model_validate(status) if status else None
    
    def get_status_by_business_and_video(self, business_name: str, video_id: str) -> Optional[HSAIVideoLearningStatusModel]:
        """根据公司名称和视频ID获取学习状态"""
        with get_db() as db:
            status = db.query(HSAIVideoLearningStatus).filter(
                HSAIVideoLearningStatus.business_name == business_name,
                HSAIVideoLearningStatus.video_id == video_id
            ).first()
            return HSAIVideoLearningStatusModel.model_validate(status) if status else None
    
    def update_status(self, id: int, form_data: dict) -> Optional[HSAIVideoLearningStatusModel]:
        """更新学习状态"""
        with get_db() as db:
            status = db.query(HSAIVideoLearningStatus).filter(HSAIVideoLearningStatus.id == id).first()
            if status:
                # 更新字段
                for key, value in form_data.items():
                    if hasattr(status, key):
                        setattr(status, key, value)
                
                setattr(status, 'updated_at', int(time.time()))
                
                db.commit()
                db.refresh(status)
                
                return HSAIVideoLearningStatusModel.model_validate(status)
            return None
    
    def delete_status_by_id(self, id: int) -> bool:
        """根据ID删除学习状态"""
        with get_db() as db:
            status = db.query(HSAIVideoLearningStatus).filter(HSAIVideoLearningStatus.id == id).first()
            if status:
                db.delete(status)
                db.commit()
                return True
            return False


# 全局实例
HSAIVideoLearningStatuses = HSAIVideoLearningStatusTable()