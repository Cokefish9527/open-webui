import logging
import time
import uuid
from typing import Optional, List
from enum import Enum

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import BigInteger, Column, String, Text, JSON, Boolean, Integer

from ._timestamp_utils import (
    normalize_optional_timestamp,
    normalize_required_timestamp,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# HSAI Viral Videos DB Schema
####################


class HSAIViralVideoStatus(str, Enum):
    """爆款视频状态枚举"""
    PENDING = "pending"      # 待处理
    PROCESSED = "processed"  # 已处理
    LEARNED = "learned"      # 已学习
    ARCHIVED = "archived"    # 已归档


class HSAIViralVideo(Base):
    """HSAI爆款视频表"""
    __tablename__ = "hsai_viral_videos"

    id = Column(String, primary_key=True)
    video_url = Column(String, nullable=False)           # 视频链接
    title = Column(String, nullable=False)               # 视频标题
    description = Column(Text, nullable=True)            # 视频描述
    thumbnail_url = Column(String, nullable=True)        # 缩略图链接
    duration = Column(Integer, nullable=True)            # 视频时长（秒）
    platform = Column(String, nullable=False)            # 平台名称（如抖音、快手等）
    
    # 标签和元数据
    tags = Column(JSON, nullable=True)                   # 视频标签
    metadata = Column(JSON, nullable=True)               # 其他元数据
    
    # 处理状态
    status = Column(String, nullable=False, default=HSAIViralVideoStatus.PENDING)  # 处理状态
    is_learned = Column(Boolean, nullable=False, default=False)  # 是否已学习
    
    # 关联信息
    material_id = Column(String, nullable=True)          # 关联的素材ID
    task_id = Column(String, nullable=True)              # 关联的任务ID
    
    # 时间戳
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    processed_at = Column(BigInteger, nullable=True)     # 处理时间
    learned_at = Column(BigInteger, nullable=True)       # 学习时间


####################
# Pydantic Models
####################


class HSAIViralVideoModel(BaseModel):
    """HSAI爆款视频模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="视频唯一标识符")
    video_url: str = Field(description="视频链接")
    title: str = Field(description="视频标题")
    description: Optional[str] = Field(default=None, description="视频描述")
    thumbnail_url: Optional[str] = Field(default=None, description="缩略图链接")
    duration: Optional[int] = Field(default=None, description="视频时长（秒）")
    platform: str = Field(description="平台名称（如抖音、快手等）")
    
    # 标签和元数据
    tags: Optional[List[str]] = Field(default=None, description="视频标签")
    metadata: Optional[dict] = Field(default=None, description="其他元数据")
    
    # 处理状态
    status: str = Field(default=HSAIViralVideoStatus.PENDING, description="处理状态")
    is_learned: bool = Field(default=False, description="是否已学习")
    
    # 关联信息
    material_id: Optional[str] = Field(default=None, description="关联的素材ID")
    task_id: Optional[str] = Field(default=None, description="关联的任务ID")
    
    # 时间戳
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")
    processed_at: Optional[int] = Field(default=None, description="处理时间")
    learned_at: Optional[int] = Field(default=None, description="学习时间")


    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_required_timestamps(cls, value):
        if value is None:
            raise ValueError("Timestamp value cannot be None")
        try:
            return normalize_required_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp value: {exc}") from exc

    @field_validator("processed_at", "learned_at", mode="before")
    @classmethod
    def validate_optional_timestamps(cls, value):
        if value is None:
            return None
        try:
            return normalize_optional_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid optional timestamp value: {exc}") from exc


class HSAIViralVideosTable:
    """HSAI爆款视频表操作类"""
    
    def insert_new_video(self, form_data: dict) -> Optional[HSAIViralVideoModel]:
        """插入新的爆款视频记录"""
        with get_db() as db:
            video = HSAIViralVideo(
                **{
                    **form_data,
                    "id": str(uuid.uuid4()),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            db.add(video)
            db.commit()
            db.refresh(video)
            
            return HSAIViralVideoModel.model_validate(video) if video else None
    
    def update_video_by_id(self, video_id: str, form_data: dict) -> Optional[HSAIViralVideoModel]:
        """根据ID更新视频记录"""
        with get_db() as db:
            video = db.query(HSAIViralVideo).filter(HSAIViralVideo.id == video_id).first()
            if video:
                # 更新字段
                for key, value in form_data.items():
                    if hasattr(video, key):
                        setattr(video, key, value)
                
                setattr(video, 'updated_at', int(time.time()))
                
                db.commit()
                db.refresh(video)
                
                return HSAIViralVideoModel.model_validate(video)
            return None
    
    def get_videos_by_status(self, status: str) -> List[HSAIViralVideoModel]:
        """根据状态获取视频列表"""
        with get_db() as db:
            videos = db.query(HSAIViralVideo).filter(HSAIViralVideo.status == status).all()
            return [HSAIViralVideoModel.model_validate(video) for video in videos]
    
    def get_unprocessed_videos(self) -> List[HSAIViralVideoModel]:
        """获取未处理的视频列表"""
        return self.get_videos_by_status(HSAIViralVideoStatus.PENDING)
    
    def get_unlearned_videos(self) -> List[HSAIViralVideoModel]:
        """获取未学习的视频列表"""
        with get_db() as db:
            videos = db.query(HSAIViralVideo).filter(
                HSAIViralVideo.is_learned == False,
                HSAIViralVideo.status == HSAIViralVideoStatus.PROCESSED
            ).all()
            return [HSAIViralVideoModel.model_validate(video) for video in videos]
    
    def update_video_status(self, video_id: str, status: str, processed_at: Optional[int] = None) -> Optional[HSAIViralVideoModel]:
        """更新视频状态"""
        with get_db() as db:
            video = db.query(HSAIViralVideo).filter(HSAIViralVideo.id == video_id).first()
            if video:
                # 使用setattr来避免类型检查错误
                setattr(video, 'status', status)
                setattr(video, 'processed_at', processed_at or int(time.time()))
                setattr(video, 'updated_at', int(time.time()))
                
                db.commit()
                db.refresh(video)
                
                return HSAIViralVideoModel.model_validate(video)
            return None
    
    def mark_video_as_learned(self, video_id: str, task_id: str, material_id: str) -> Optional[HSAIViralVideoModel]:
        """标记视频为已学习"""
        with get_db() as db:
            video = db.query(HSAIViralVideo).filter(HSAIViralVideo.id == video_id).first()
            if video:
                # 使用setattr来避免类型检查错误
                setattr(video, 'is_learned', True)
                setattr(video, 'task_id', task_id)
                setattr(video, 'material_id', material_id)
                setattr(video, 'learned_at', int(time.time()))
                setattr(video, 'updated_at', int(time.time()))
                
                db.commit()
                db.refresh(video)
                
                return HSAIViralVideoModel.model_validate(video)
            return None
    
    @staticmethod
    def get_video_by_url(video_url: str) -> Optional[HSAIViralVideoModel]:
        """根据视频URL获取视频记录"""
        try:
            with get_db() as db:
                video = db.query(HSAIViralVideo).filter(HSAIViralVideo.video_url == video_url).first()
                return HSAIViralVideoModel.model_validate(video) if video else None
        except Exception:
            return None
    
    def get_video_by_id(self, video_id: str) -> Optional[HSAIViralVideoModel]:
        """根据ID获取视频"""
        with get_db() as db:
            video = db.query(HSAIViralVideo).filter(HSAIViralVideo.id == video_id).first()
            return HSAIViralVideoModel.model_validate(video) if video else None


# 全局实例
HSAIViralVideos = HSAIViralVideosTable()
