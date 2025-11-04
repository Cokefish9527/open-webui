import logging
import time
import uuid
from typing import Optional, Dict, Any

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, String, UniqueConstraint

from ._timestamp_utils import normalize_required_timestamp, EpochTimestamp

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class OperationStatus:
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class HSAIIdempotentOperation(Base):
    """幂等操作记录"""
    __tablename__ = "hsai_idempotent_operations"
    __table_args__ = (
        UniqueConstraint("operation_id", name="uq_idempotent_operation"),
    )

    id = Column(String, primary_key=True)
    operation_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default=OperationStatus.PENDING)
    context = Column(JSONField, nullable=True)
    last_error = Column(String, nullable=True)
    created_at = Column(EpochTimestamp(), nullable=False)
    updated_at = Column(EpochTimestamp(), nullable=False)


class HSAIIdempotentOperationModel(BaseModel):
    """幂等操作模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="记录ID")
    operation_id: str = Field(description="幂等操作ID")
    status: str = Field(description="状态")
    context: Optional[Dict[str, Any]] = Field(default=None, description="附加信息")
    last_error: Optional[str] = Field(default=None, description="最近一次错误")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")

    @classmethod
    def _normalize_ts(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        return normalize_required_timestamp(value)

    @classmethod
    def model_validate(cls, obj):
        model = super().model_validate(obj)
        return model


class HSAIIdempotentOperationsTable:
    """幂等操作表操作"""

    def upsert_operation(
        self,
        operation_id: str,
        context: Optional[Dict[str, Any]] = None,
        status: str = OperationStatus.PENDING,
    ) -> HSAIIdempotentOperationModel:
        with get_db() as db:
            record = (
                db.query(HSAIIdempotentOperation)
                .filter_by(operation_id=operation_id)
                .with_for_update(nowait=False)
                .first()
            )
            now_ts = int(time.time())
            if record:
                record.context = context or record.context
                record.status = status
                record.updated_at = now_ts
            else:
                record = HSAIIdempotentOperation(
                    id=str(uuid.uuid4()),
                    operation_id=operation_id,
                    status=status,
                    context=context,
                    created_at=now_ts,
                    updated_at=now_ts,
                )
                db.add(record)
            db.commit()
            db.refresh(record)
            return HSAIIdempotentOperationModel.model_validate(record)

    def get_operation(self, operation_id: str) -> Optional[HSAIIdempotentOperationModel]:
        with get_db() as db:
            record = db.query(HSAIIdempotentOperation).filter_by(operation_id=operation_id).first()
            return HSAIIdempotentOperationModel.model_validate(record) if record else None

    def mark_failed(self, operation_id: str, error_message: str) -> None:
        with get_db() as db:
            record = db.query(HSAIIdempotentOperation).filter_by(operation_id=operation_id).first()
            if not record:
                return
            record.status = OperationStatus.FAILED
            record.last_error = error_message
            record.updated_at = int(time.time())
            db.commit()


HSAIIdempotentOperations = HSAIIdempotentOperationsTable()
