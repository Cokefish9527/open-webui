from __future__ import annotations
import logging
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, get_db
from open_webui.models.chats import Chats

from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import BigInteger, Column, Text, JSON, Boolean
from ._timestamp_utils import normalize_required_timestamp

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Feedback DB Schema
####################


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = {'extend_existing': True}
    id = Column(Text, primary_key=True)
    user_id = Column(Text)
    version = Column(BigInteger, default=0)
    type = Column(Text)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    snapshot = Column(JSON, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class FeedbackModel(BaseModel):
    """反馈模型"""
    id: str = Field(description="反馈唯一标识符")
    user_id: str = Field(description="用户ID")
    version: int = Field(description="版本号")
    type: str = Field(description="反馈类型")
    data: Optional[dict] = Field(default=None, description="反馈数据")
    meta: Optional[dict] = Field(default=None, description="元数据")
    snapshot: Optional[dict] = Field(default=None, description="快照数据")
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


    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class FeedbackResponse(BaseModel):
    """反馈响应模型"""
    id: str = Field(description="反馈唯一标识符")
    user_id: str = Field(description="用户ID")
    version: int = Field(description="版本号")
    type: str = Field(description="反馈类型")
    data: Optional[dict] = Field(default=None, description="反馈数据")
    meta: Optional[dict] = Field(default=None, description="元数据")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class RatingData(BaseModel):
    """评分数据模型"""
    rating: Optional[str | int] = Field(default=None, description="评分")
    model_id: Optional[str] = Field(default=None, description="模型ID")
    sibling_model_ids: Optional[list[str]] = Field(default=None, description="兄弟模型ID列表")
    reason: Optional[str] = Field(default=None, description="评分原因")
    comment: Optional[str] = Field(default=None, description="评论")
    model_config = ConfigDict(extra="allow", protected_namespaces=())


class MetaData(BaseModel):
    """元数据模型"""
    arena: Optional[bool] = Field(default=None, description="是否为竞技场模式")
    chat_id: Optional[str] = Field(default=None, description="聊天ID")
    message_id: Optional[str] = Field(default=None, description="消息ID")
    tags: Optional[list[str]] = Field(default=None, description="标签列表")
    model_config = ConfigDict(extra="allow")


class SnapshotData(BaseModel):
    """快照数据模型"""
    chat: Optional[dict] = Field(default=None, description="聊天内容")
    model_config = ConfigDict(extra="allow")


class FeedbackForm(BaseModel):
    """反馈表单模型"""
    type: str = Field(description="反馈类型")
    data: Optional[RatingData] = Field(default=None, description="评分数据")
    meta: Optional[dict] = Field(default=None, description="元数据")
    snapshot: Optional[SnapshotData] = Field(default=None, description="快照数据")
    model_config = ConfigDict(extra="allow")


class FeedbackTable:
    def insert_new_feedback(
        self, user_id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            feedback = FeedbackModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "version": 0,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            try:
                result = Feedback(**feedback.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return FeedbackModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error creating a new feedback: {e}")
                return None

    def get_feedback_by_id(self, id: str) -> Optional[FeedbackModel]:
        try:
            with get_db() as db:
                feedback = db.query(Feedback).filter_by(id=id).first()
                if not feedback:
                    return None
                return FeedbackModel.model_validate(feedback)
        except Exception:
            return None

    def get_feedback_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[FeedbackModel]:
        try:
            with get_db() as db:
                feedback = db.query(Feedback).filter_by(id=id, user_id=user_id).first()
                if not feedback:
                    return None
                return FeedbackModel.model_validate(feedback)
        except Exception:
            return None

    def get_all_feedbacks(self) -> list[FeedbackModel]:
        with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in db.query(Feedback)
                .order_by(Feedback.updated_at.desc())
                .all()
            ]

    def get_feedbacks_by_type(self, type: str) -> list[FeedbackModel]:
        with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in db.query(Feedback)
                .filter_by(type=type)
                .order_by(Feedback.updated_at.desc())
                .all()
            ]

    def get_feedbacks_by_user_id(self, user_id: str) -> list[FeedbackModel]:
        with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in db.query(Feedback)
                .filter_by(user_id=user_id)
                .order_by(Feedback.updated_at.desc())
                .all()
            ]

    def update_feedback_by_id(
        self, id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        with get_db() as db:
            feedback = db.query(Feedback).filter_by(id=id).first()
            if not feedback:
                return None

            if form_data.data:
                feedback.data = form_data.data.model_dump()
            if form_data.meta:
                feedback.meta = form_data.meta
            if form_data.snapshot:
                feedback.snapshot = form_data.snapshot.model_dump()

            feedback.updated_at = int(time.time())

            db.commit()
            return FeedbackModel.model_validate(feedback)

    def update_feedback_by_id_and_user_id(
        self, id: str, user_id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        with get_db() as db:
            feedback = db.query(Feedback).filter_by(id=id, user_id=user_id).first()
            if not feedback:
                return None

            if form_data.data:
                feedback.data = form_data.data.model_dump()
            if form_data.meta:
                feedback.meta = form_data.meta
            if form_data.snapshot:
                feedback.snapshot = form_data.snapshot.model_dump()

            feedback.updated_at = int(time.time())

            db.commit()
            return FeedbackModel.model_validate(feedback)

    def delete_feedback_by_id(self, id: str) -> bool:
        with get_db() as db:
            feedback = db.query(Feedback).filter_by(id=id).first()
            if not feedback:
                return False
            db.delete(feedback)
            db.commit()
            return True

    def delete_feedback_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        with get_db() as db:
            feedback = db.query(Feedback).filter_by(id=id, user_id=user_id).first()
            if not feedback:
                return False
            db.delete(feedback)
            db.commit()
            return True

    def delete_feedbacks_by_user_id(self, user_id: str) -> bool:
        with get_db() as db:
            feedbacks = db.query(Feedback).filter_by(user_id=user_id).all()
            if not feedbacks:
                return False
            for feedback in feedbacks:
                db.delete(feedback)
            db.commit()
            return True

    def delete_all_feedbacks(self) -> bool:
        with get_db() as db:
            feedbacks = db.query(Feedback).all()
            if not feedbacks:
                return False
            for feedback in feedbacks:
                db.delete(feedback)
            db.commit()
            return True


Feedbacks = FeedbackTable()
