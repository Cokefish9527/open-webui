import logging
import time
import uuid
from contextlib import contextmanager
from threading import Lock
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS, DATABASE_SCHEMA
from open_webui.internal.migrations.ugc import ensure_ugc_schema

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, JSON, ForeignKey, Integer, SmallInteger, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship

from ._timestamp_utils import (
    normalize_optional_timestamp,
    normalize_required_timestamp,
    EpochTimestamp,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

_SCHEMA_LOCK = Lock()
_SCHEMA_READY = False


def _ensure_ugc_schema(session) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        ensure_ugc_schema(
            session.get_bind(),
            schema=DATABASE_SCHEMA,
            logger=log.debug,
        )
        _SCHEMA_READY = True


@contextmanager
def _schema_aware_db():
    with get_db() as db:
        _ensure_ugc_schema(db)
        yield db

####################
# UGC Video Generation DB Schema
####################

class HSAIUGCMaterialModel(Base):
    """数字人资产表 (Material_Models)"""
    __tablename__ = "Material_Models"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    model_name = Column(String(128), nullable=False)
    model_img_url = Column(String(512), nullable=False)
    voice_provider_id = Column(String(128), nullable=False)
    voice_preview_url = Column(String(512), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())


class HSAIUGCTask(Base):
    """主任务表 (Video_Tasks)"""
    __tablename__ = "Video_Tasks"

    id = Column(String(36), primary_key=True)
    user_id = Column(Text, nullable=False)
    # 状态机: 0:排队, 1:脚本生成, 2:待编辑, 3:视频生成, 4:待合成, 5:合成中, 6:成功, -1:失败
    status = Column(SmallInteger, nullable=False, default=0)
    # 当前步骤: 1:脚本阶段, 2:分镜视频阶段, 3:合成阶段
    step = Column(SmallInteger, nullable=False, default=1)
    model_id = Column(BigInteger, ForeignKey("Material_Models.id"), nullable=False)
    base_inputs = Column(JSON, nullable=False)  # product_url, product_name, language
    result_video_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    scenes = relationship("HSAIUGCTaskScene", back_populates="task", cascade="all, delete-orphan")


class HSAIUGCTaskScene(Base):
    """分镜明细表 (Task_Scenes)"""
    __tablename__ = "Task_Scenes"
    __table_args__ = (UniqueConstraint("task_id", "scene_index", name="uq_task_scenes_task_id_scene_index"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(36), ForeignKey("Video_Tasks.id", ondelete="CASCADE"), nullable=False)
    scene_index = Column(Integer, nullable=False)
    subtitle = Column(Text, nullable=True)
    script_desc = Column(Text, nullable=True)
    reference_img_url = Column(String(512), nullable=True)
    fragment_video_url = Column(String(512), nullable=True)

    task = relationship("HSAIUGCTask", back_populates="scenes")

####################
# Pydantic Models
####################

class MaterialModelData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: str
    model_name: str
    model_img_url: str
    voice_provider_id: str
    voice_preview_url: str
    created_at: int

    @classmethod
    def _coerce_source(cls, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            data = dict(value)
        else:
            attr_names = [
                "id",
                "user_id",
                "model_name",
                "model_img_url",
                "voice_provider_id",
                "voice_preview_url",
                "created_at",
            ]
            data = {key: getattr(value, key, None) for key in attr_names}
        if data.get("user_id") is not None:
            data["user_id"] = str(data["user_id"])
        created_at = data.get("created_at")
        if isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            data["created_at"] = int(created_at.timestamp())
        return data

    @classmethod
    def model_validate(cls, value, *args, **kwargs):
        return super().model_validate(cls._coerce_source(value), *args, **kwargs)

class VideoTaskData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    status: int
    step: int
    model_id: int
    base_inputs: Dict[str, Any]
    result_video_url: Optional[str] = None
    created_at: int
    updated_at: int

    @classmethod
    def _coerce_source(cls, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            data = dict(value)
        else:
            attr_names = [
                "id",
                "user_id",
                "status",
                "step",
                "model_id",
                "base_inputs",
                "result_video_url",
                "created_at",
                "updated_at",
            ]
            data = {key: getattr(value, key, None) for key in attr_names}
        if data.get("user_id") is not None:
            data["user_id"] = str(data["user_id"])
        for key in ("created_at", "updated_at"):
            v = data.get(key)
            if isinstance(v, datetime):
                if v.tzinfo is None:
                    v = v.replace(tzinfo=timezone.utc)
                data[key] = int(v.timestamp())
        return data

    @classmethod
    def model_validate(cls, value, *args, **kwargs):
        return super().model_validate(cls._coerce_source(value), *args, **kwargs)

class TaskSceneData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: str
    scene_index: int
    subtitle: Optional[str] = None
    script_desc: Optional[str] = None
    reference_img_url: Optional[str] = None
    fragment_video_url: Optional[str] = None

####################
# Forms
####################

class MaterialModelCreateForm(BaseModel):
    model_name: str
    model_img_url: str
    voice_provider_id: str
    voice_preview_url: str

class VideoTaskCreateForm(BaseModel):
    model_id: int
    product_url: str
    product_name: str
    language: str
    product_country: Optional[str] = None
    subtitle: Optional[str] = None
    shot_script: Optional[str] = None

class TaskSceneUpdateForm(BaseModel):
    subtitle: Optional[str] = None
    script_desc: Optional[str] = None
    reference_img_url: Optional[str] = None

####################
# DAO Classes
####################

class HSAIUGCMaterialModelsTable:
    def insert_new_model(self, user_id: str, form: MaterialModelCreateForm) -> MaterialModelData:
        with _schema_aware_db() as db:
            model = HSAIUGCMaterialModel(
                user_id=user_id,
                model_name=form.model_name,
                model_img_url=form.model_img_url,
                voice_provider_id=form.voice_provider_id,
                voice_preview_url=form.voice_preview_url,
                created_at=datetime.utcnow()
            )
            db.add(model)
            db.commit()
            db.refresh(model)
            return MaterialModelData.model_validate(model)

    def get_models_by_user_id(self, user_id: str) -> List[MaterialModelData]:
        with _schema_aware_db() as db:
            models = db.query(HSAIUGCMaterialModel).filter_by(user_id=user_id).all()
            return [MaterialModelData.model_validate(m) for m in models]

    def get_model_by_id(self, model_id: int) -> Optional[MaterialModelData]:
        with _schema_aware_db() as db:
            model = db.query(HSAIUGCMaterialModel).filter_by(id=model_id).first()
            return MaterialModelData.model_validate(model) if model else None

    def get_model_by_id_and_user_id(self, model_id: int, user_id: str) -> Optional[MaterialModelData]:
        with _schema_aware_db() as db:
            model = db.query(HSAIUGCMaterialModel).filter_by(id=model_id, user_id=user_id).first()
            return MaterialModelData.model_validate(model) if model else None


class HSAIUGCTasksTable:
    def create_task(self, user_id: str, form: VideoTaskCreateForm) -> VideoTaskData:
        with _schema_aware_db() as db:
            task_id = str(uuid.uuid4())
            now = datetime.utcnow()
            task = HSAIUGCTask(
                id=task_id,
                user_id=user_id,
                status=1,  # Generating Script
                step=1,
                model_id=form.model_id,
                base_inputs={
                    "product_url": form.product_url,
                    "product_name": form.product_name,
                    "language": form.language,
                },
                created_at=now,
                updated_at=now
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return VideoTaskData.model_validate(task)

    def get_task_by_id(self, task_id: str) -> Optional[VideoTaskData]:
        with _schema_aware_db() as db:
            task = db.query(HSAIUGCTask).filter_by(id=task_id).first()
            return VideoTaskData.model_validate(task) if task else None

    def update_task_status(self, task_id: str, status: int, step: Optional[int] = None, result_url: Optional[str] = None) -> bool:
        with _schema_aware_db() as db:
            update_data = {"status": status, "updated_at": datetime.utcnow()}
            if step is not None:
                update_data["step"] = step
            if result_url is not None:
                update_data["result_video_url"] = result_url
            
            result = db.query(HSAIUGCTask).filter_by(id=task_id).update(update_data)
            db.commit()
            return result > 0

    def get_tasks_by_user_id(self, user_id: str) -> List[VideoTaskData]:
        with _schema_aware_db() as db:
            tasks = db.query(HSAIUGCTask).filter_by(user_id=user_id).order_by(HSAIUGCTask.created_at.desc()).all()
            return [VideoTaskData.model_validate(t) for t in tasks]

    def mark_stale_tasks_failed(self, *, timeout_minutes: int = 30) -> int:
        """
        设计文档兜底：将处理中的任务（status=1/3/5）在超时后强制标记失败。
        """
        with _schema_aware_db() as db:
            now = datetime.utcnow()
            threshold = now - timedelta(minutes=max(timeout_minutes, 0))

            q = db.query(HSAIUGCTask).filter(
                HSAIUGCTask.status.in_([1, 3, 5]),
                HSAIUGCTask.updated_at < threshold,
            )
            count = q.count()
            if count <= 0:
                return 0

            q.update(
                {
                    "status": -1,
                    "updated_at": now,
                },
                synchronize_session=False,
            )
            db.commit()
            return count


class HSAIUGCTaskScenesTable:
    def batch_insert_scenes(self, task_id: str, scenes_data: List[Dict[str, Any]]):
        """
        scenes_data: list of dicts with subtitle, script_desc, reference_img_url, scene_index
        """
        with _schema_aware_db() as db:
            # Clear old scenes if any
            db.query(HSAIUGCTaskScene).filter_by(task_id=task_id).delete()
            
            for item in scenes_data:
                scene = HSAIUGCTaskScene(
                    task_id=task_id,
                    scene_index=item["scene_index"],
                    subtitle=item.get("subtitle"),
                    script_desc=item.get("script_desc"),
                    reference_img_url=item.get("reference_img_url")
                )
                db.add(scene)
            db.commit()

    def get_scenes_by_task_id(self, task_id: str) -> List[TaskSceneData]:
        with _schema_aware_db() as db:
            scenes = db.query(HSAIUGCTaskScene).filter_by(task_id=task_id).order_by(HSAIUGCTaskScene.scene_index.asc()).all()
            return [TaskSceneData.model_validate(s) for s in scenes]

    def update_scene(self, scene_id: int, form: TaskSceneUpdateForm) -> bool:
        with _schema_aware_db() as db:
            update_data = form.model_dump(exclude_unset=True)
            if not update_data:
                return True
            result = db.query(HSAIUGCTaskScene).filter_by(id=scene_id).update(update_data)
            db.commit()
            return result > 0

    def update_fragment_video_url(self, task_id: str, scene_index: int, video_url: str) -> bool:
        with _schema_aware_db() as db:
            result = db.query(HSAIUGCTaskScene).filter_by(task_id=task_id, scene_index=scene_index).update({"fragment_video_url": video_url})
            db.commit()
            return result > 0


# Singletons
MaterialModels = HSAIUGCMaterialModelsTable()
VideoTasks = HSAIUGCTasksTable()
TaskScenes = HSAIUGCTaskScenesTable()
