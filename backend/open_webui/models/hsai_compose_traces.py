import json
import logging
import time
import uuid
from contextlib import contextmanager
from threading import Lock
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, String, Text, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from open_webui.env import DATABASE_SCHEMA, SRC_LOG_LEVELS
from open_webui.internal.db import Base, get_db
from open_webui.internal.migrations import ensure_compose_trace_schema

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", "INFO"))

_SCHEMA_LOCK = Lock()
_SCHEMA_READY = False


def _ensure_schema(session) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        ensure_compose_trace_schema(
            session.get_bind(),
            schema=DATABASE_SCHEMA,
            logger=log.debug,
        )
        _SCHEMA_READY = True


@contextmanager
def _schema_aware_db():
    with get_db() as db:
        _ensure_schema(db)
        yield db


class HSAIComposeTrace(Base):
    __tablename__ = "hsai_compose_traces"

    trace_id = Column(String, primary_key=True)
    n8n_session_id = Column(String, nullable=True)
    company_id = Column(String, nullable=True)
    project_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    business_name = Column(Text, nullable=True)
    source_learned_id = Column(BigInteger, nullable=True)
    status = Column(String, nullable=False, default="running")
    last_n8n_updated_at = Column(BigInteger, nullable=True)
    last_synced_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    steps = relationship(
        "HSAIComposeStep",
        back_populates="trace",
        cascade="all, delete-orphan",
        lazy="select",
    )
    artifacts = relationship(
        "HSAIComposeArtifact",
        back_populates="trace",
        cascade="all, delete-orphan",
        lazy="select",
    )


class HSAIComposeStep(Base):
    __tablename__ = "hsai_compose_steps"
    __table_args__ = (UniqueConstraint("trace_id", "step_key", name="uq_hsai_compose_step"),)

    id = Column(String, primary_key=True)
    trace_id = Column(String, ForeignKey("hsai_compose_traces.trace_id"), nullable=False)
    step_key = Column(String, nullable=False)
    stage_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="captured")
    raw_stage_json = Column(Text, nullable=True)
    extracted_json = Column(Text, nullable=True)
    started_at = Column(BigInteger, nullable=True)
    finished_at = Column(BigInteger, nullable=True)
    updated_at = Column(BigInteger, nullable=False)

    trace = relationship("HSAIComposeTrace", back_populates="steps", lazy="joined")


class HSAIComposeArtifact(Base):
    __tablename__ = "hsai_compose_artifacts"
    __table_args__ = (
        UniqueConstraint("trace_id", "artifact_type", "oss_url", name="uq_hsai_compose_artifact"),
    )

    id = Column(String, primary_key=True)
    trace_id = Column(String, ForeignKey("hsai_compose_traces.trace_id"), nullable=False)
    step_id = Column(String, nullable=True)
    artifact_type = Column(String, nullable=False)
    oss_url = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)

    trace = relationship("HSAIComposeTrace", back_populates="artifacts", lazy="joined")


class HSAIComposeTraceModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trace_id: str
    n8n_session_id: Optional[str] = None
    company_id: Optional[str] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    business_name: Optional[str] = None
    source_learned_id: Optional[int] = None
    status: str
    last_n8n_updated_at: Optional[int] = None
    last_synced_at: Optional[int] = None
    created_at: int
    updated_at: int


class HSAIComposeStepModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trace_id: str
    step_key: str
    stage_name: Optional[str] = None
    status: str
    raw_stage_json: Optional[Dict[str, Any]] = None
    extracted_json: Optional[Dict[str, Any]] = None
    started_at: Optional[int] = None
    finished_at: Optional[int] = None
    updated_at: int


class HSAIComposeArtifactModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trace_id: str
    step_id: Optional[str] = None
    artifact_type: str
    oss_url: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: int


def _loads_json(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _dumps_json(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if payload is None:
        return None
    try:
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return None


class ComposeTraceCreateForm(BaseModel):
    trace_id: str = Field(description="追溯主键（建议等于 task_id）")
    n8n_session_id: str = Field(description="n8n_workflow 会话 session_id（uuid）")
    company_id: Optional[str] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    business_name: Optional[str] = None
    source_learned_id: Optional[int] = None


class HSAIComposeTraceStore:
    def _now(self) -> int:
        return int(time.time())

    def upsert_trace(self, form: ComposeTraceCreateForm) -> HSAIComposeTraceModel:
        now = self._now()
        with _schema_aware_db() as db:
            existing = db.get(HSAIComposeTrace, form.trace_id)
            if existing:
                existing.n8n_session_id = form.n8n_session_id or existing.n8n_session_id
                existing.company_id = form.company_id or existing.company_id
                existing.project_id = form.project_id or existing.project_id
                existing.user_id = form.user_id or existing.user_id
                existing.business_name = form.business_name or existing.business_name
                if form.source_learned_id is not None:
                    existing.source_learned_id = form.source_learned_id
                existing.updated_at = now
                db.add(existing)
                db.commit()
                db.refresh(existing)
                return HSAIComposeTraceModel.model_validate(existing)

            record = HSAIComposeTrace(
                trace_id=form.trace_id,
                n8n_session_id=form.n8n_session_id,
                company_id=form.company_id,
                project_id=form.project_id,
                user_id=form.user_id,
                business_name=form.business_name,
                source_learned_id=form.source_learned_id,
                status="running",
                created_at=now,
                updated_at=now,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return HSAIComposeTraceModel.model_validate(record)

    def set_trace_sync_state(
        self,
        trace_id: str,
        *,
        status: Optional[str] = None,
        last_n8n_updated_at: Optional[int] = None,
    ) -> Optional[HSAIComposeTraceModel]:
        now = self._now()
        with _schema_aware_db() as db:
            record = db.get(HSAIComposeTrace, trace_id)
            if not record:
                return None
            if status:
                record.status = status
            if last_n8n_updated_at is not None:
                record.last_n8n_updated_at = last_n8n_updated_at
            record.last_synced_at = now
            record.updated_at = now
            db.add(record)
            db.commit()
            db.refresh(record)
            return HSAIComposeTraceModel.model_validate(record)

    def list_traces(
        self,
        *,
        company_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[HSAIComposeTraceModel]:
        with _schema_aware_db() as db:
            query = db.query(HSAIComposeTrace)
            if company_id:
                query = query.filter(HSAIComposeTrace.company_id == company_id)
            if project_id:
                query = query.filter(HSAIComposeTrace.project_id == project_id)
            if status:
                query = query.filter(HSAIComposeTrace.status == status)
            records = (
                query.order_by(HSAIComposeTrace.updated_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return [HSAIComposeTraceModel.model_validate(item) for item in records]

    def count_traces(
        self,
        *,
        company_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        with _schema_aware_db() as db:
            query = db.query(HSAIComposeTrace)
            if company_id:
                query = query.filter(HSAIComposeTrace.company_id == company_id)
            if project_id:
                query = query.filter(HSAIComposeTrace.project_id == project_id)
            if status:
                query = query.filter(HSAIComposeTrace.status == status)
            return query.count()

    def get_trace(self, trace_id: str) -> Optional[HSAIComposeTraceModel]:
        with _schema_aware_db() as db:
            record = db.get(HSAIComposeTrace, trace_id)
            return HSAIComposeTraceModel.model_validate(record) if record else None

    def list_steps(self, trace_id: str) -> List[HSAIComposeStepModel]:
        with _schema_aware_db() as db:
            rows = (
                db.query(HSAIComposeStep)
                .filter(HSAIComposeStep.trace_id == trace_id)
                .order_by(HSAIComposeStep.updated_at.asc())
                .all()
            )
            models: List[HSAIComposeStepModel] = []
            for row in rows:
                models.append(
                    HSAIComposeStepModel(
                        id=row.id,
                        trace_id=row.trace_id,
                        step_key=row.step_key,
                        stage_name=row.stage_name,
                        status=row.status,
                        raw_stage_json=_loads_json(row.raw_stage_json),
                        extracted_json=_loads_json(row.extracted_json),
                        started_at=row.started_at,
                        finished_at=row.finished_at,
                        updated_at=row.updated_at,
                    )
                )
            return models

    def upsert_step(
        self,
        trace_id: str,
        *,
        step_key: str,
        stage_name: Optional[str],
        status: str,
        raw_stage_json: Optional[Dict[str, Any]],
        extracted_json: Optional[Dict[str, Any]],
        updated_at: int,
    ) -> HSAIComposeStepModel:
        with _schema_aware_db() as db:
            existing = (
                db.query(HSAIComposeStep)
                .filter(
                    HSAIComposeStep.trace_id == trace_id,
                    HSAIComposeStep.step_key == step_key,
                )
                .one_or_none()
            )
            if existing:
                existing.stage_name = stage_name
                existing.status = status
                existing.raw_stage_json = _dumps_json(raw_stage_json)
                existing.extracted_json = _dumps_json(extracted_json)
                existing.updated_at = updated_at
                db.add(existing)
                db.commit()
                db.refresh(existing)
                return HSAIComposeStepModel(
                    id=existing.id,
                    trace_id=existing.trace_id,
                    step_key=existing.step_key,
                    stage_name=existing.stage_name,
                    status=existing.status,
                    raw_stage_json=_loads_json(existing.raw_stage_json),
                    extracted_json=_loads_json(existing.extracted_json),
                    started_at=existing.started_at,
                    finished_at=existing.finished_at,
                    updated_at=existing.updated_at,
                )

            step_id = str(uuid.uuid4())
            record = HSAIComposeStep(
                id=step_id,
                trace_id=trace_id,
                step_key=step_key,
                stage_name=stage_name,
                status=status,
                raw_stage_json=_dumps_json(raw_stage_json),
                extracted_json=_dumps_json(extracted_json),
                updated_at=updated_at,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return HSAIComposeStepModel(
                id=record.id,
                trace_id=record.trace_id,
                step_key=record.step_key,
                stage_name=record.stage_name,
                status=record.status,
                raw_stage_json=_loads_json(record.raw_stage_json),
                extracted_json=_loads_json(record.extracted_json),
                started_at=record.started_at,
                finished_at=record.finished_at,
                updated_at=record.updated_at,
            )

    def list_artifacts(self, trace_id: str) -> List[HSAIComposeArtifactModel]:
        with _schema_aware_db() as db:
            rows = (
                db.query(HSAIComposeArtifact)
                .filter(HSAIComposeArtifact.trace_id == trace_id)
                .order_by(HSAIComposeArtifact.created_at.asc())
                .all()
            )
            results: List[HSAIComposeArtifactModel] = []
            for row in rows:
                results.append(
                    HSAIComposeArtifactModel(
                        id=row.id,
                        trace_id=row.trace_id,
                        step_id=row.step_id,
                        artifact_type=row.artifact_type,
                        oss_url=row.oss_url,
                        metadata_json=_loads_json(row.metadata_json),
                        created_at=row.created_at,
                    )
                )
            return results

    def insert_artifact(
        self,
        trace_id: str,
        *,
        step_id: Optional[str],
        artifact_type: str,
        oss_url: Optional[str],
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> Optional[HSAIComposeArtifactModel]:
        now = self._now()
        with _schema_aware_db() as db:
            try:
                record = HSAIComposeArtifact(
                    id=str(uuid.uuid4()),
                    trace_id=trace_id,
                    step_id=step_id,
                    artifact_type=artifact_type,
                    oss_url=oss_url,
                    metadata_json=_dumps_json(metadata_json),
                    created_at=now,
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                return HSAIComposeArtifactModel(
                    id=record.id,
                    trace_id=record.trace_id,
                    step_id=record.step_id,
                    artifact_type=record.artifact_type,
                    oss_url=record.oss_url,
                    metadata_json=_loads_json(record.metadata_json),
                    created_at=record.created_at,
                )
            except Exception as exc:  # pylint: disable=broad-except
                try:
                    db.rollback()
                except Exception:  # pragma: no cover
                    pass
                log.error("Failed inserting compose artifact trace_id=%s err=%s", trace_id, exc, exc_info=True)
                return None

    def get_final_video_url(self, trace_id: str) -> Optional[str]:
        with _schema_aware_db() as db:
            row = (
                db.query(HSAIComposeArtifact)
                .filter(
                    HSAIComposeArtifact.trace_id == trace_id,
                    HSAIComposeArtifact.artifact_type == "final_video",
                )
                .order_by(HSAIComposeArtifact.created_at.desc())
                .first()
            )
            return str(row.oss_url) if row and row.oss_url else None


HSAIComposeTraces = HSAIComposeTraceStore()

