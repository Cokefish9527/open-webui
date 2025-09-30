import logging
import time
from typing import Optional, List

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Integer, Text

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# HSAI Video Learning Log DB Schema
####################


class HSAIVideoLearningLog(Base):
    """HSAI视频学习日志表"""
    __tablename__ = "hsai_video_learning_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 自增主键
    business_name = Column(String, nullable=False)              # 公司名称
    video_id = Column(String, nullable=False)                   # 学习的视频ID
    from_status = Column(String, nullable=True)                 # 原始状态
    to_status = Column(String, nullable=False)                  # 目标状态
    change_reason = Column(Text, nullable=True)                 # 状态变更原因
    changed_by = Column(String, nullable=True)                  # 变更操作人
    
    # 时间戳
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic Models
####################


class HSAIVideoLearningLogModel(BaseModel):
    """HSAI视频学习日志模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Auto-increment primary key")
    business_name: str = Field(description="Business name")
    video_id: str = Field(description="Video ID")
    from_status: Optional[str] = Field(description="Original status")
    to_status: str = Field(description="Target status")
    change_reason: Optional[str] = Field(description="Status change reason")
    changed_by: Optional[str] = Field(description="Operator who made the change")
    
    # Timestamps
    created_at: int = Field(description="Creation timestamp")
    updated_at: int = Field(description="Update timestamp")


class HSAIVideoLearningLogForm(BaseModel):
    """HSAI视频学习日志表单模型"""
    model_config = ConfigDict(from_attributes=True)

    business_name: str = Field(description="Business name")
    video_id: str = Field(description="Video ID")
    from_status: Optional[str] = Field(description="Original status")
    to_status: str = Field(description="Target status")
    change_reason: Optional[str] = Field(description="Status change reason")
    changed_by: Optional[str] = Field(description="Operator who made the change")


class HSAIVideoLearningLogTable:
    """HSAI视频学习日志表操作类"""
    
    def insert_new_log(self, form_data: dict) -> Optional[HSAIVideoLearningLogModel]:
        """插入新的视频学习日志记录"""
        with get_db() as db:
            log_entry = HSAIVideoLearningLog(
                **{
                    **form_data,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            
            return HSAIVideoLearningLogModel.model_validate(log_entry) if log_entry else None
    
    def get_logs_by_video_id(self, video_id: str) -> List[HSAIVideoLearningLogModel]:
        """根据视频ID获取学习日志"""
        with get_db() as db:
            logs = db.query(HSAIVideoLearningLog).filter(HSAIVideoLearningLog.video_id == video_id).order_by(HSAIVideoLearningLog.created_at.desc()).all()
            return [HSAIVideoLearningLogModel.model_validate(log) for log in logs]
    
    def get_logs_by_business_and_video(self, business_name: str, video_id: str) -> List[HSAIVideoLearningLogModel]:
        """根据公司名称和视频ID获取学习日志"""
        with get_db() as db:
            logs = db.query(HSAIVideoLearningLog).filter(
                HSAIVideoLearningLog.business_name == business_name,
                HSAIVideoLearningLog.video_id == video_id
            ).order_by(HSAIVideoLearningLog.created_at.desc()).all()
            return [HSAIVideoLearningLogModel.model_validate(log) for log in logs]
    
    def get_recent_logs(self, limit: int = 50) -> List[HSAIVideoLearningLogModel]:
        """获取最近的学习日志"""
        with get_db() as db:
            logs = db.query(HSAIVideoLearningLog).order_by(HSAIVideoLearningLog.created_at.desc()).limit(limit).all()
            return [HSAIVideoLearningLogModel.model_validate(log) for log in logs]


# 全局实例
HSAIVideoLearningLogs = HSAIVideoLearningLogTable()