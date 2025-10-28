import logging
import time
from typing import Optional, List, Dict
from enum import Enum

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, String, Integer, UniqueConstraint, Index
from sqlalchemy.exc import IntegrityError

from ._timestamp_utils import normalize_required_timestamp, EpochTimestamp

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# ORM definitions
####################


class HSAIVideoLearningStatusEnum(str, Enum):
    """Valid learning status values."""

    LEARNING = "learning"
    LEARNED = "learned"
    ABANDONED = "abandoned"


class HSAIVideoLearningStatus(Base):
    """ORM model for hsai_video_learning_status."""

    __tablename__ = "hsai_video_learning_status"
    __table_args__ = (
        UniqueConstraint(
            "business_name",
            "video_id",
            name="uq_hsai_video_learning_status_business_video",
        ),
        Index(
            "idx_hsai_video_learning_status_business_status",
            "business_name",
            "status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_name = Column(String, nullable=False)
    video_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(EpochTimestamp())
    updated_at = Column(EpochTimestamp())


####################
# Pydantic models
####################


class HSAIVideoLearningStatusModel(BaseModel):
    """Read model for video learning status."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Primary key")
    business_name: str = Field(description="Company or tenant name")
    video_id: str = Field(description="Video identifier")
    status: str = Field(description="Learning status value")
    created_at: int = Field(description="Creation timestamp (epoch seconds)")
    updated_at: int = Field(description="Update timestamp (epoch seconds)")

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
    """Write model for inserting a video learning status."""

    model_config = ConfigDict(from_attributes=True)

    business_name: str = Field(description="Company or tenant name")
    video_id: str = Field(description="Video identifier")
    status: str = Field(description="Learning status value")


class HSAIVideoLearningStatusTable:
    """Table operations for hsai_video_learning_status."""

    def insert_new_status(self, form_data: dict) -> Optional[HSAIVideoLearningStatusModel]:
        """Insert a new learning status entry."""
        with get_db() as db:
            now_ts = int(time.time())
            status = HSAIVideoLearningStatus(
                **{
                    **form_data,
                    "created_at": now_ts,
                    "updated_at": now_ts,
                }
            )

            db.add(status)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                log.error("Failed to insert video learning status, data=%s", form_data, exc_info=True)
                raise exc

            db.refresh(status)
            return HSAIVideoLearningStatusModel.model_validate(status) if status else None

    def get_status_by_video_id(
        self,
        video_id: str,
        business_name: str,
    ) -> Optional[HSAIVideoLearningStatusModel]:
        """Retrieve status by video id and business name."""
        if not business_name:
            raise ValueError("business_name is required to query learning status")

        with get_db() as db:
            status = (
                db.query(HSAIVideoLearningStatus)
                .filter(
                    HSAIVideoLearningStatus.business_name == business_name,
                    HSAIVideoLearningStatus.video_id == video_id,
                )
                .first()
            )
            return HSAIVideoLearningStatusModel.model_validate(status) if status else None

    def get_status_by_business_and_video(
        self,
        business_name: str,
        video_id: str,
    ) -> Optional[HSAIVideoLearningStatusModel]:
        """Compatibility wrapper for querying by business and video."""
        return self.get_status_by_video_id(video_id=video_id, business_name=business_name)

    def get_status_map_for_business(
        self,
        business_name: str,
        video_ids: List[str],
    ) -> Dict[str, HSAIVideoLearningStatusModel]:
        """Return a mapping of video_id -> status model for the given business."""
        if not video_ids:
            return {}

        with get_db() as db:
            statuses = (
                db.query(HSAIVideoLearningStatus)
                .filter(
                    HSAIVideoLearningStatus.business_name == business_name,
                    HSAIVideoLearningStatus.video_id.in_(video_ids),
                )
                .all()
            )
            return {
                status.video_id: HSAIVideoLearningStatusModel.model_validate(status)
                for status in statuses
            }

    def list_video_ids_by_business(
        self,
        business_name: str,
        status_filter: Optional[str] = None,
    ) -> List[str]:
        """List video ids for the given tenant and (optional) status filter."""
        with get_db() as db:
            query = db.query(HSAIVideoLearningStatus.video_id).filter(
                HSAIVideoLearningStatus.business_name == business_name
            )
            if status_filter and status_filter != "all":
                query = query.filter(HSAIVideoLearningStatus.status == status_filter)

            return [row[0] for row in query.all()]

    def update_status(self, id: int, form_data: dict) -> Optional[HSAIVideoLearningStatusModel]:
        """Update a learning status entry by id."""
        with get_db() as db:
            status = (
                db.query(HSAIVideoLearningStatus)
                .filter(HSAIVideoLearningStatus.id == id)
                .first()
            )
            if status:
                for key, value in form_data.items():
                    if hasattr(status, key):
                        setattr(status, key, value)
                status.updated_at = int(time.time())

                db.commit()
                db.refresh(status)

                return HSAIVideoLearningStatusModel.model_validate(status)
            return None

    def delete_status_by_id(self, id: int) -> bool:
        """Delete a learning status entry by id."""
        with get_db() as db:
            status = (
                db.query(HSAIVideoLearningStatus)
                .filter(HSAIVideoLearningStatus.id == id)
                .first()
            )
            if status:
                db.delete(status)
                db.commit()
                return True
            return False


# Global table helper
HSAIVideoLearningStatuses = HSAIVideoLearningStatusTable()
