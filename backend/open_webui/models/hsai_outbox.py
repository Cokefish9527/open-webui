import logging
import time
import uuid
from typing import Dict, Any, List, Optional

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, String, Integer, Text

from ._timestamp_utils import normalize_required_timestamp, EpochTimestamp

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class OutboxEventStatus:
    PENDING = "pending"
    DISPATCHED = "dispatched"
    FAILED = "failed"


class HSAIOutboxEvent(Base):
    """Outbox 事件表"""
    __tablename__ = "hsai_outbox_events"

    id = Column(String, primary_key=True)
    operation_id = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSONField, nullable=False)
    status = Column(String, nullable=False, default=OutboxEventStatus.PENDING)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    scheduled_at = Column(EpochTimestamp(), nullable=True)
    created_at = Column(EpochTimestamp(), nullable=False)
    updated_at = Column(EpochTimestamp(), nullable=False)


class HSAIOutboxEventModel(BaseModel):
    """Outbox 事件模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="事件唯一标识")
    operation_id: Optional[str] = Field(default=None, description="幂等操作ID")
    event_type: str = Field(description="事件类型")
    payload: Dict[str, Any] = Field(description="事件载荷")
    status: str = Field(description="当前状态")
    attempts: int = Field(description="重试次数")
    last_error: Optional[str] = Field(default=None, description="最近一次错误信息")
    scheduled_at: Optional[int] = Field(default=None, description="计划执行时间戳")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")

    @classmethod
    def _normalize_ts(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        return normalize_required_timestamp(value)

    @staticmethod
    def _normalize_required_ts(value: int) -> int:
        return normalize_required_timestamp(value)

    @classmethod
    def model_validate(cls, obj):
        model = super().model_validate(obj)
        return model


class HSAIOutboxTable:
    """Outbox 事件表操作"""

    def enqueue(
        self,
        event_type: str,
        payload: Dict[str, Any],
        operation_id: Optional[str] = None,
        scheduled_at: Optional[int] = None,
    ) -> HSAIOutboxEventModel:
        with get_db() as db:
            now_ts = int(time.time())
            event = HSAIOutboxEvent(
                id=str(uuid.uuid4()),
                operation_id=operation_id,
                event_type=event_type,
                payload=payload,
                status=OutboxEventStatus.PENDING,
                attempts=0,
                scheduled_at=scheduled_at,
                created_at=now_ts,
                updated_at=now_ts,
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            return HSAIOutboxEventModel.model_validate(event)

    def acquire_pending(
        self,
        batch_size: int = 50,
        max_attempts: int = 5,
        now_ts: Optional[int] = None,
    ) -> List[HSAIOutboxEventModel]:
        with get_db() as db:
            current_ts = now_ts or int(time.time())
            records = (
                db.query(HSAIOutboxEvent)
                .filter(HSAIOutboxEvent.status == OutboxEventStatus.PENDING)
                .filter(
                    (HSAIOutboxEvent.scheduled_at.is_(None))
                    | (HSAIOutboxEvent.scheduled_at <= current_ts)
                )
                .filter(HSAIOutboxEvent.attempts < max_attempts)
                .order_by(HSAIOutboxEvent.created_at.asc())
                .limit(batch_size)
                .all()
            )
            return [HSAIOutboxEventModel.model_validate(item) for item in records]

    def mark_dispatched(self, event_id: str) -> bool:
        with get_db() as db:
            event = db.get(HSAIOutboxEvent, event_id)
            if not event:
                return False
            event.status = OutboxEventStatus.DISPATCHED
            event.updated_at = int(time.time())
            db.commit()
            return True

    def mark_failed(self, event_id: str, error_message: str) -> bool:
        with get_db() as db:
            event = db.get(HSAIOutboxEvent, event_id)
            if not event:
                return False
            event.status = OutboxEventStatus.FAILED
            event.last_error = error_message
            event.attempts += 1
            event.updated_at = int(time.time())
            db.commit()
            return True

    def reschedule(
        self,
        event_id: str,
        delay_seconds: int,
        error_message: Optional[str] = None,
    ) -> bool:
        with get_db() as db:
            event = db.get(HSAIOutboxEvent, event_id)
            if not event:
                return False
            event.attempts += 1
            if error_message:
                event.last_error = error_message
            event.scheduled_at = int(time.time()) + max(delay_seconds, 0)
            event.updated_at = int(time.time())
            db.commit()
            return True


HSAIOutboxEvents = HSAIOutboxTable()

