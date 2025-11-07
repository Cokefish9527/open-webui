import logging
import time
import uuid
from enum import Enum
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import (
    Column,
    String,
    Text,
    JSON,
    ForeignKey,
    Enum as SAEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from ._timestamp_utils import EpochTimestamp

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", "INFO"))


class BlueprintProgressState(str, Enum):
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"


class HSAIBlueprintProgress(Base):
    __tablename__ = "hsai_blueprint_progress"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_hsai_blueprint_progress_project"),
    )

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("hsai_projects.id"), nullable=False)
    blueprint_version = Column(String, nullable=False)

    execution_duration_days = Column(String, nullable=True)
    planned_total_posts = Column(String, nullable=True)
    posting_frequency = Column(String, nullable=True)
    required_tiktok_accounts = Column(String, nullable=True)

    summary_md = Column(Text, nullable=True)
    blueprint_raw = Column(Text, nullable=True)
    latest_digest = Column(JSON, nullable=True)

    progress_state = Column(SAEnum(BlueprintProgressState), nullable=False, default=BlueprintProgressState.PLANNING)
    daily_cycle_config = Column(JSON, nullable=True)

    last_synced_at = Column(EpochTimestamp(), nullable=False)
    created_at = Column(EpochTimestamp(), nullable=False)
    updated_at = Column(EpochTimestamp(), nullable=False)

    project = relationship("HSAIProject", backref="blueprint_progress", lazy="joined")


class HSAIBlueprintProgressHistory(Base):
    __tablename__ = "hsai_blueprint_progress_history"

    id = Column(String, primary_key=True)
    progress_id = Column(String, ForeignKey("hsai_blueprint_progress.id"), nullable=False)
    operation = Column(String, nullable=False)
    operator_id = Column(String, nullable=True)
    changes_json = Column(JSON, nullable=True)
    snapshot_md = Column(Text, nullable=True)
    created_at = Column(EpochTimestamp(), nullable=False)


class HSAITaskBlueprintLink(Base):
    __tablename__ = "hsai_task_blueprint_links"
    __table_args__ = (
        UniqueConstraint("progress_id", "template_key", name="uq_blueprint_task_template"),
    )

    id = Column(String, primary_key=True)
    progress_id = Column(String, ForeignKey("hsai_blueprint_progress.id"), nullable=False)
    task_id = Column(String, ForeignKey("hsai_tasks.id"), nullable=False)
    template_key = Column(String, nullable=False)
    link_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(EpochTimestamp(), nullable=False)
    updated_at = Column(EpochTimestamp(), nullable=False)


class BlueprintDigest(BaseModel):
    version: str = Field(description="蓝图版本")
    execution_duration_days: Optional[str] = None
    planned_total_posts: Optional[str] = None
    posting_frequency: Optional[str] = None
    required_tiktok_accounts: Optional[str] = None


class HSAIBlueprintProgressModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    blueprint_version: str
    execution_duration_days: Optional[str] = None
    planned_total_posts: Optional[str] = None
    posting_frequency: Optional[str] = None
    required_tiktok_accounts: Optional[str] = None
    summary_md: Optional[str] = None
    blueprint_raw: Optional[str] = None
    latest_digest: Optional[Dict[str, Any]] = None
    progress_state: BlueprintProgressState
    daily_cycle_config: Optional[Dict[str, Any]] = None
    last_synced_at: int
    created_at: int
    updated_at: int


class HSAIBlueprintProgressHistoryModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    progress_id: str
    operation: str
    operator_id: Optional[str] = None
    changes_json: Optional[Dict[str, Any]] = None
    snapshot_md: Optional[str] = None
    created_at: int


class HSAITaskBlueprintLinkModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    progress_id: str
    task_id: str
    template_key: str
    link_metadata: Optional[Dict[str, Any]] = None
    created_at: int
    updated_at: int


class HSAIBlueprintProgressStore:
    """CRUD helpers for blueprint progress."""

    def _now(self) -> int:
        return int(time.time())

    def get_by_project(self, project_id: str) -> Optional[HSAIBlueprintProgressModel]:
        with get_db() as db:
            progress = (
                db.query(HSAIBlueprintProgress)
                .filter(HSAIBlueprintProgress.project_id == project_id)
                .one_or_none()
            )
            return HSAIBlueprintProgressModel.model_validate(progress) if progress else None

    def get_by_id(self, progress_id: str) -> Optional[HSAIBlueprintProgressModel]:
        with get_db() as db:
            progress = db.get(HSAIBlueprintProgress, progress_id)
            return HSAIBlueprintProgressModel.model_validate(progress) if progress else None

    def upsert_progress(
        self,
        project_id: str,
        payload: Dict[str, Any],
        operator_id: Optional[str] = None,
    ) -> HSAIBlueprintProgressModel:
        """Create or update blueprint progress and record history."""
        now_ts = self._now()
        with get_db() as db:
            existing = (
                db.query(HSAIBlueprintProgress)
                .filter(HSAIBlueprintProgress.project_id == project_id)
                .one_or_none()
            )

            if existing:
                old_snapshot = {
                    "blueprint_version": existing.blueprint_version,
                    "execution_duration_days": existing.execution_duration_days,
                    "planned_total_posts": existing.planned_total_posts,
                    "posting_frequency": existing.posting_frequency,
                    "required_tiktok_accounts": existing.required_tiktok_accounts,
                    "summary_md": existing.summary_md,
                    "progress_state": existing.progress_state.value if existing.progress_state else None,
                    "daily_cycle_config": existing.daily_cycle_config,
                    "latest_digest": existing.latest_digest,
                }

                for key, value in payload.items():
                    setattr(existing, key, value)

                existing.updated_at = now_ts
                existing.last_synced_at = now_ts
                db.add(existing)
                db.flush()

                history = HSAIBlueprintProgressHistory(
                    id=str(uuid.uuid4()),
                    progress_id=existing.id,
                    operation="UPDATE",
                    operator_id=operator_id,
                    changes_json={
                        "before": old_snapshot,
                        "after": {k: getattr(existing, k) for k in old_snapshot.keys()},
                    },
                    snapshot_md=existing.summary_md,
                    created_at=now_ts,
                )
                db.add(history)
                db.commit()
                db.refresh(existing)
                return HSAIBlueprintProgressModel.model_validate(existing)

            new_id = str(uuid.uuid4())
            record = HSAIBlueprintProgress(
                id=new_id,
                project_id=project_id,
                last_synced_at=now_ts,
                created_at=now_ts,
                updated_at=now_ts,
                **payload,
            )
            db.add(record)
            db.flush()

            history = HSAIBlueprintProgressHistory(
                id=str(uuid.uuid4()),
                progress_id=new_id,
                operation="INSERT",
                operator_id=operator_id,
                changes_json={"after": payload},
                snapshot_md=payload.get("summary_md"),
                created_at=now_ts,
            )
            db.add(history)
            db.commit()
            db.refresh(record)
            return HSAIBlueprintProgressModel.model_validate(record)

    def insert_history(
        self,
        progress_id: str,
        operation: str,
        changes_json: Optional[Dict[str, Any]],
        snapshot_md: Optional[str],
        operator_id: Optional[str] = None,
    ) -> HSAIBlueprintProgressHistoryModel:
        with get_db() as db:
            history = HSAIBlueprintProgressHistory(
                id=str(uuid.uuid4()),
                progress_id=progress_id,
                operation=operation,
                operator_id=operator_id,
                changes_json=changes_json,
                snapshot_md=snapshot_md,
                created_at=self._now(),
            )
            db.add(history)
            db.commit()
            db.refresh(history)
            return HSAIBlueprintProgressHistoryModel.model_validate(history)

    def list_history(self, progress_id: str, limit: int = 20) -> List[HSAIBlueprintProgressHistoryModel]:
        with get_db() as db:
            records = (
                db.query(HSAIBlueprintProgressHistory)
                .filter(HSAIBlueprintProgressHistory.progress_id == progress_id)
                .order_by(HSAIBlueprintProgressHistory.created_at.desc())
                .limit(limit)
                .all()
            )
            return [HSAIBlueprintProgressHistoryModel.model_validate(item) for item in records]


class HSAITaskBlueprintLinksStore:
    """Mapping between blueprint progress and tasks."""

    def _now(self) -> int:
        return int(time.time())

    def get_by_progress(
        self, progress_id: str, template_key: Optional[str] = None
    ) -> List[HSAITaskBlueprintLinkModel]:
        with get_db() as db:
            query = db.query(HSAITaskBlueprintLink).filter(
                HSAITaskBlueprintLink.progress_id == progress_id
            )
            if template_key:
                query = query.filter(HSAITaskBlueprintLink.template_key == template_key)
            records = query.all()
            return [HSAITaskBlueprintLinkModel.model_validate(item) for item in records]

    def upsert_link(
        self,
        progress_id: str,
        task_id: str,
        template_key: str,
        link_metadata: Optional[Dict[str, Any]] = None,
    ) -> HSAITaskBlueprintLinkModel:
        now_ts = self._now()
        with get_db() as db:
            existing = (
                db.query(HSAITaskBlueprintLink)
                .filter(
                    HSAITaskBlueprintLink.progress_id == progress_id,
                    HSAITaskBlueprintLink.template_key == template_key,
                )
                .one_or_none()
            )
            if existing:
                existing.task_id = task_id
                if link_metadata is not None:
                    existing.link_metadata = link_metadata or existing.link_metadata
                existing.updated_at = now_ts
                db.add(existing)
                db.commit()
                db.refresh(existing)
                return HSAITaskBlueprintLinkModel.model_validate(existing)

            record = HSAITaskBlueprintLink(
                id=str(uuid.uuid4()),
                progress_id=progress_id,
                task_id=task_id,
                template_key=template_key,
                link_metadata=link_metadata or {},
                created_at=now_ts,
                updated_at=now_ts,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return HSAITaskBlueprintLinkModel.model_validate(record)


HSAIBlueprintProgressTable = HSAIBlueprintProgressStore()
HSAITaskBlueprintLinksTable = HSAITaskBlueprintLinksStore()
