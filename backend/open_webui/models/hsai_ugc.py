import logging
import json
import time
import uuid
from decimal import Decimal
from contextlib import contextmanager
from threading import Lock
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS, DATABASE_SCHEMA
from open_webui.internal.migrations.ugc import ensure_ugc_schema

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    BigInteger,
    Column,
    String,
    Text,
    JSON,
    ForeignKey,
    Integer,
    SmallInteger,
    DateTime,
    Numeric,
    func,
    UniqueConstraint,
    cast,
    case,
    or_,
)
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
        # Ensure pooled connections are not left in failed transactions
        # (e.g., previous errors can cause "InFailedSqlTransaction" on SET LOCAL).
        try:
            db.rollback()
        except Exception:
            pass
        _ensure_ugc_schema(db)
        yield db

####################
# UGC Video Generation DB Schema
####################

class HSAIUGCMaterialModel(Base):
    """数字人资产表 (hsai_ugc_material_models)"""
    __tablename__ = "hsai_ugc_material_models"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    model_name = Column(String(128), nullable=False)
    model_img_url = Column(String(512), nullable=False)
    voice_provider_id = Column(String(128), nullable=False)
    voice_preview_url = Column(String(512), nullable=False)
    minimax_account_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    deleted_at = Column(DateTime, nullable=True)  # 软删除标记


class HSAIUGCTask(Base):
    """主任务表 (hsai_ugc_video_tasks)"""
    __tablename__ = "hsai_ugc_video_tasks"

    id = Column(String(36), primary_key=True)
    user_id = Column(Text, nullable=False)
    # 状态机:
    # -2:已关闭, -1:失败, 0:排队(保留), 1:脚本生成中, 2:待确认脚本, 3:分镜视频生成中, 4:待合成(短暂态), 5:合成中, 6:成功
    status = Column(SmallInteger, nullable=False, default=0)
    # 当前阶段(标记)：1:脚本阶段(hs002), 2:分镜视频阶段(hs003), 3:合成阶段(hs004)
    step = Column(SmallInteger, nullable=False, default=1)
    model_id = Column(BigInteger, ForeignKey("hsai_ugc_material_models.id"), nullable=False)
    base_inputs = Column(JSON, nullable=False)  # product_url, product_name, language
    result_video_url = Column(String(512), nullable=True)
    # Billing / retry policy fields (UGC per-full-video pre-charge at hs002 stage).
    billed_credits = Column(Numeric(12, 6), nullable=True)
    billed_at = Column(DateTime, nullable=True)
    free_retry_until = Column(DateTime, nullable=True)
    # Cooldown window starts from each generate/retry request time.
    last_trigger_at = Column(DateTime, nullable=True)
    # 用于“视频库/任务列表”排序和进度还原 (0~100)
    progress_percent = Column(SmallInteger, nullable=False, default=0)
    # 仅在进度实质推进时更新，用于“无进展”判断（避免读接口刷新 updated_at）
    last_progress_at = Column(DateTime, nullable=True)
    # 用户手动关闭或超时自动关闭
    closed_at = Column(DateTime, nullable=True)
    closed_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    scenes = relationship("HSAIUGCTaskScene", back_populates="task", cascade="all, delete-orphan")


class HSAIUGCTaskScene(Base):
    """分镜明细表 (hsai_ugc_task_scenes)"""
    __tablename__ = "hsai_ugc_task_scenes"
    __table_args__ = (UniqueConstraint("task_id", "scene_index", name="uq_task_scenes_task_id_scene_index"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(36), ForeignKey("hsai_ugc_video_tasks.id", ondelete="CASCADE"), nullable=False)
    scene_index = Column(Integer, nullable=False)
    subtitle = Column(Text, nullable=True)
    script_desc = Column(Text, nullable=True)
    reference_img_url = Column(String(512), nullable=True)
    fragment_video_url = Column(String(512), nullable=True)
    # JSON string: ["url1","url2",...], used for multi-candidate per scene (hs003 output).
    fragment_video_urls = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    error_msg = Column(Text, nullable=True)
    image_prompt = Column(Text, nullable=True)

    task = relationship("HSAIUGCTask", back_populates="scenes")


class HSAIUGCProduct(Base):
    """产品库表 (hsai_ugc_products)"""
    __tablename__ = "hsai_ugc_products"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    cover_img = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class HSAIUGCCallbackLog(Base):
    """UGC 消息队列回调日志表 (hsai_ugc_callback_logs)"""
    __tablename__ = "hsai_ugc_callback_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(36), nullable=True)  # task_id might be missing
    msg_type = Column(String(64), nullable=True) # type might be missing
    payload = Column(JSON, nullable=True)        # raw message
    error_msg = Column(Text, nullable=True)      # processing error if any
    created_at = Column(DateTime, nullable=False, default=func.now())



####################
# Pydantic Models
####################

class MaterialModelData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="数字人资产ID")
    user_id: str = Field(..., description="用户ID")
    model_name: str = Field(..., description="数字人名称", example="My Avatar")
    model_img_url: str = Field(..., description="数字人形象图片URL")
    voice_provider_id: str = Field(..., description="音色ID (MiniMax)")
    voice_preview_url: str = Field(..., description="音色预览音频URL")
    minimax_account_id: Optional[int] = Field(None, description="绑定的MiniMax账号ID")
    created_at: int = Field(..., description="创建时间戳 (秒)")

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
                "minimax_account_id",
                "created_at",
            ]
            data = {key: getattr(value, key, None) for key in attr_names}
        if data.get("user_id") is not None:
            data["user_id"] = str(data["user_id"])
        if data.get("minimax_account_id") is not None:
            try:
                data["minimax_account_id"] = int(data["minimax_account_id"])
            except Exception:
                data["minimax_account_id"] = None
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
    id: str = Field(..., description="任务ID (UUID)")
    user_id: str = Field(..., description="用户ID")
    status: int = Field(..., description="任务状态: 0=排队, 1=脚本生成中, 2=待编辑, 3=分镜生成中, 4=待合成, 5=合成中, 6=成功, -1=失败, -2=已关闭")
    step: int = Field(..., description="当前步骤: 1=脚本, 2=分镜, 3=合成")
    model_id: int = Field(..., description="使用的数字人模型ID")
    base_inputs: Dict[str, Any] = Field(..., description="基础输入参数快照")
    result_video_url: Optional[str] = Field(None, description="最终合成视频URL")
    billed_credits: Optional[Decimal] = Field(None, description="预扣费积分(整条视频)")
    billed_at: Optional[int] = Field(None, description="预扣费时间戳(秒)")
    free_retry_until: Optional[int] = Field(None, description="免费重试窗口截止时间戳(秒)")
    last_trigger_at: Optional[int] = Field(None, description="最后一次触发生成/重试时间戳(秒)，用于冷却时间计算")
    progress_percent: int = Field(0, description="总体进度百分比 (0-100)")
    last_progress_at: Optional[int] = Field(None, description="最后进度更新时间戳")
    closed_at: Optional[int] = Field(None, description="关闭时间戳")
    closed_reason: Optional[str] = Field(None, description="关闭/失败原因")
    created_at: int = Field(..., description="创建时间戳")
    updated_at: int = Field(..., description="更新时间戳")

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
                "billed_credits",
                "billed_at",
                "free_retry_until",
                "last_trigger_at",
                "progress_percent",
                "last_progress_at",
                "closed_at",
                "closed_reason",
                "created_at",
                "updated_at",
            ]
            data = {key: getattr(value, key, None) for key in attr_names}
        if data.get("user_id") is not None:
            data["user_id"] = str(data["user_id"])
        for key in (
            "created_at",
            "updated_at",
            "last_progress_at",
            "closed_at",
            "billed_at",
            "free_retry_until",
            "last_trigger_at",
        ):
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
    id: int = Field(..., description="分镜ID")
    task_id: str = Field(..., description="所属任务ID")
    scene_index: int = Field(..., description="分镜索引 (0-based)")
    subtitle: Optional[str] = Field(None, description="口播字幕")
    script_desc: Optional[str] = Field(None, description="分镜脚本描述")
    reference_img_url: Optional[str] = Field(None, description="分镜参考图URL")
    fragment_video_url: Optional[str] = Field(None, description="分镜视频片段URL")
    fragment_video_urls: Optional[List[str]] = Field(None, description="分镜视频候选列表")
    image_prompt: Optional[str] = Field(None, description="图片生成提示词")

    @classmethod
    def _coerce_source(cls, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            data = dict(value)
        else:
            attr_names = [
                "id",
                "task_id",
                "scene_index",
                "subtitle",
                "script_desc",
                "reference_img_url",
                "fragment_video_url",
                "fragment_video_urls",
                "image_prompt",
            ]
            data = {key: getattr(value, key, None) for key in attr_names}

        raw = data.get("fragment_video_urls")
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    data["fragment_video_urls"] = [str(v) for v in parsed if v]
                else:
                    data["fragment_video_urls"] = None
            except Exception:
                data["fragment_video_urls"] = None
        elif isinstance(raw, list):
            data["fragment_video_urls"] = [str(v) for v in raw if v]
        else:
            data["fragment_video_urls"] = None if raw is None else raw

        return data

    @classmethod
    def model_validate(cls, value, *args, **kwargs):
        return super().model_validate(cls._coerce_source(value), *args, **kwargs)


class UGCLibraryTaskItem(BaseModel):
    """
    UGC 视频库任务列表项：包含进度快照，用于“离开页面后从视频库恢复进度”。
    """

    id: str
    user_id: str
    status: int
    step: int
    model_id: int
    product_name: Optional[str] = None
    progress_stage: str
    progress_message: str
    progress_percent: int
    scenes_total: int = 0
    scenes_done: int = 0
    is_stale: bool = False
    result_video_url: Optional[str] = None
    created_at: int
    updated_at: int
    last_progress_at: Optional[int] = None
    closed_at: Optional[int] = None
    closed_reason: Optional[str] = None


class UGCLibraryTasksResponse(BaseModel):
    items: List[UGCLibraryTaskItem]
    page: int
    page_size: int
    total: int


class UGCTaskCloseForm(BaseModel):
    reason: str = "user_abort"
    message: Optional[str] = None


class ProductData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="产品ID")
    user_id: str = Field(..., description="用户ID")
    name: str = Field(..., description="产品名称")
    description: Optional[str] = Field(None, description="产品描述")
    cover_img: Optional[str] = Field(None, description="产品封面图URL")
    created_at: int = Field(..., description="创建时间戳")
    updated_at: int = Field(..., description="更新时间戳")

    @classmethod
    def _coerce_source(cls, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            data = dict(value)
        else:
            attr_names = [
                "id",
                "user_id",
                "name",
                "description",
                "cover_img",
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

class ProductsListResponse(BaseModel):
    """产品列表分页响应"""
    items: List[ProductData]
    page: int
    page_size: int
    total: int


class ProductCreateForm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., description="产品名称")
    description: Optional[str] = Field(None, description="产品描述")
    cover_img: Optional[str] = Field(None, description="产品封面图URL")

class ProductUpdateForm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, description="产品名称")
    description: Optional[str] = Field(None, description="产品描述")
    cover_img: Optional[str] = Field(None, description="产品封面图URL")


####################
# Forms
####################

class MaterialModelCreateForm(BaseModel):
    model_name: str = Field(..., description="数字人名称")
    model_img_url: str = Field(..., description="数字人形象图片OSS URL")
    voice_provider_id: str = Field(..., description="音色ID")
    voice_preview_url: str = Field(..., description="音色预览音频OSS URL")
    minimax_account_id: Optional[int] = Field(None, description="绑定的MiniMax账号ID")

class VideoTaskCreateForm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: int = Field(..., description="选择的数字人模型ID")
    # 产品库支持(优先)
    product_id: Optional[int] = Field(None, description="产品库ID (推荐)")
    # 兼容旧接口(降级为可选)
    product_url: Optional[str] = Field(None, description="产品图片URL (兼容旧模式)")
    product_name: Optional[str] = Field(None, description="产品名称 (兼容旧模式)")
    # 其他参数
    language: str = Field(..., description="目标语言 (zh-CN/en-US)", example="zh-CN")
    product_country: Optional[str] = Field(None, description="产品目标国家/地区")
    subtitle: Optional[str] = Field(None, description="自定义字幕内容")
    shot_script: Optional[str] = Field(None, description="自定义脚本大纲")
    creative_bias: Optional[str] = Field(None, description="创意偏好描述")

class TaskSceneUpdateForm(BaseModel):
    subtitle: Optional[str] = Field(None, description="更新口播字幕")
    script_desc: Optional[str] = Field(None, description="更新分镜脚本描述")
    reference_img_url: Optional[str] = Field(None, description="更新分镜参考图URL")
    image_prompt: Optional[str] = Field(None, description="更新图片生成提示词")

# --- WebSocket Documentation Schemas ---

class UGCTaskUpdateEvent(BaseModel):
    """
    WebSocket 'hsai_ugc_update' 事件负载结构
    
    设计说明:
    - 推送完整的任务信息结构,包括任务状态、分镜列表、最终结果
    - 对于单一分镜重试,scenes 数组只包含该分镜信息
    - 对于全量更新(如脚本生成完成),scenes 包含所有分镜
    - 前端可直接用此结构更新本地状态,无需额外 API 调用
    """
    task_id: str = Field(..., description="任务ID")
    status: int = Field(..., description="任务状态: 0=排队, 1=脚本生成中, 2=待编辑, 3=分镜生成中, 4=待合成, 5=合成中, 6=成功, -1=失败, -2=已关闭")
    step: int = Field(..., description="当前步骤: 1=脚本, 2=分镜, 3=合成")
    progress_percent: Optional[int] = Field(None, description="总体进度百分比 (0-100)")
    result_video_url: Optional[str] = Field(None, description="最终合成视频URL (status=6时有值)")
    scenes: Optional[List[TaskSceneData]] = Field(None, description="分镜列表 (全量或增量)")
    error_msg: Optional[str] = Field(None, description="错误信息 (status=-1时有值)")

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
                minimax_account_id=form.minimax_account_id,
                created_at=datetime.utcnow()
            )
            db.add(model)
            db.commit()
            db.refresh(model)
            return MaterialModelData.model_validate(model)

    def get_models_by_user_id(self, user_id: str) -> List[MaterialModelData]:
        with _schema_aware_db() as db:
            models = db.query(HSAIUGCMaterialModel).filter_by(user_id=user_id).filter(HSAIUGCMaterialModel.deleted_at.is_(None)).all()
            return [MaterialModelData.model_validate(m) for m in models]

    def get_model_by_id(self, model_id: int) -> Optional[MaterialModelData]:
        with _schema_aware_db() as db:
            model = db.query(HSAIUGCMaterialModel).filter_by(id=model_id).filter(HSAIUGCMaterialModel.deleted_at.is_(None)).first()
            return MaterialModelData.model_validate(model) if model else None

    def get_model_by_id_and_user_id(self, model_id: int, user_id: str) -> Optional[MaterialModelData]:
        with _schema_aware_db() as db:
            model = db.query(HSAIUGCMaterialModel).filter_by(id=model_id, user_id=user_id).filter(HSAIUGCMaterialModel.deleted_at.is_(None)).first()
            return MaterialModelData.model_validate(model) if model else None

    def delete_model(self, model_id: int) -> bool:
        """
        软删除:标记 deleted_at 而不是物理删除,以保留历史任务的引用完整性。
        """
        with _schema_aware_db() as db:
            model = db.query(HSAIUGCMaterialModel).filter_by(id=model_id).filter(HSAIUGCMaterialModel.deleted_at.is_(None)).first()
            if not model:
                return False
            model.deleted_at = datetime.utcnow()
            db.commit()
            return True


class HSAIUGCTasksTable:
    @staticmethod
    def _status_to_stage(status: int) -> str:
        return {
            -2: "CLOSED",
            -1: "FAILED",
            0: "QUEUED",
            1: "SCRIPTING",
            2: "PENDING_EDIT",
            3: "RENDERING",
            4: "PENDING_MERGE",
            5: "MERGING",
            6: "SUCCESS",
        }.get(status, "UNKNOWN")

    @staticmethod
    def _status_to_message(status: int, *, scenes_done: int = 0, scenes_total: int = 0) -> str:
        if status == -2:
            return "已关闭"
        if status == -1:
            return "失败"
        if status == 0:
            return "排队中"
        if status == 1:
            return "脚本生成中"
        if status == 2:
            return "待编辑/待确认"
        if status == 3:
            if scenes_total > 0:
                return f"分镜视频生成中（{scenes_done}/{scenes_total}）"
            return "分镜视频生成中"
        if status == 4:
            return "待合成"
        if status == 5:
            return "合成中"
        if status == 6:
            return "已完成"
        return "未知状态"

    @classmethod
    def _status_to_percent(cls, status: int, *, scenes_done: int = 0, scenes_total: int = 0) -> int:
        if status in (-2, -1):
            return 0
        if status == 0:
            return 5
        if status == 1:
            return 20
        if status == 2:
            return 35
        if status == 3:
            if scenes_total > 0:
                ratio = max(min(scenes_done / max(scenes_total, 1), 1.0), 0.0)
                return int(35 + ratio * 45)  # 35~80
            return 50
        if status == 4:
            return 85
        if status == 5:
            return 90
        if status == 6:
            return 100
        return 0

    def create_task(
        self,
        user_id: str,
        form: VideoTaskCreateForm,
        *,
        task_id: Optional[str] = None,
        billed_credits: Optional[Decimal] = None,
        billed_at: Optional[datetime] = None,
        free_retry_until: Optional[datetime] = None,
        last_trigger_at: Optional[datetime] = None,
    ) -> VideoTaskData:
        with _schema_aware_db() as db:
            now = datetime.utcnow()
            resolved_task_id = task_id or str(uuid.uuid4())
            task = HSAIUGCTask(
                id=resolved_task_id,
                user_id=user_id,
                status=1,  # Generating Script
                step=1,
                model_id=form.model_id,
                progress_percent=self._status_to_percent(1),
                last_progress_at=now,
                base_inputs={
                    "product_url": form.product_url,
                    "product_name": form.product_name,
                    "language": form.language,
                    # 设计对齐：用于可追溯/可重试（即使后续 n8n/workflow 失败也能还原输入）
                    "product_country": form.product_country or "",
                    "subtitle": form.subtitle or "",
                    "shot_script": form.shot_script or "",
                    "creative_bias": form.creative_bias or "",
                },
                billed_credits=billed_credits,
                billed_at=billed_at,
                free_retry_until=free_retry_until,
                last_trigger_at=last_trigger_at or now,
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

    def get_user_last_trigger_at(self, user_id: str) -> Optional[datetime]:
        """
        User-level cooldown anchor: the most recent trigger time among all tasks.
        """
        with _schema_aware_db() as db:
            try:
                return db.query(func.max(HSAIUGCTask.last_trigger_at)).filter_by(user_id=user_id).scalar()
            except Exception:
                return None

    def patch_base_inputs(self, task_id: str, patch: Dict[str, Any]) -> bool:
        """
        Merge patch into task.base_inputs (JSON).
        This is used to persist step-level metadata (e.g. hs003 scene_index mapping) for callback handling.
        """
        if not isinstance(patch, dict) or not patch:
            return True
        with _schema_aware_db() as db:
            task = db.query(HSAIUGCTask).filter_by(id=task_id).first()
            if not task:
                return False
            current = getattr(task, "base_inputs", None) or {}
            if not isinstance(current, dict):
                current = {}
            merged = dict(current)
            merged.update(patch)
            now = datetime.utcnow()
            result = (
                db.query(HSAIUGCTask)
                .filter_by(id=task_id)
                .update({"base_inputs": merged, "updated_at": now}, synchronize_session=False)
            )
            db.commit()
            return result > 0

    def touch_last_trigger_at(self, task_id: str, when: Optional[datetime] = None) -> bool:
        """
        Update last_trigger_at for cooldown window calculation.
        """
        with _schema_aware_db() as db:
            now = when or datetime.utcnow()
            result = (
                db.query(HSAIUGCTask)
                .filter_by(id=task_id)
                .update({"last_trigger_at": now, "updated_at": now}, synchronize_session=False)
            )
            db.commit()
            return result > 0

    def close_expired_free_retry_tasks(self, *, now: Optional[datetime] = None) -> int:
        """
        Close tasks whose free retry window has expired.
        We only close tasks that are not already closed/success.
        """
        with _schema_aware_db() as db:
            now_dt = now or datetime.utcnow()
            q = db.query(HSAIUGCTask).filter(
                HSAIUGCTask.status.notin_([-2, 6]),
                HSAIUGCTask.free_retry_until.isnot(None),
                HSAIUGCTask.free_retry_until < now_dt,
            )
            count = int(q.count() or 0)
            if count <= 0:
                return 0
            q.update(
                {
                    "status": -2,
                    "progress_percent": 0,
                    "closed_at": now_dt,
                    "closed_reason": "free_retry_window_expired",
                    "updated_at": now_dt,
                    "last_progress_at": now_dt,
                },
                synchronize_session=False,
            )
            db.commit()
            return count

    def update_task_status(self, task_id: str, status: int, step: Optional[int] = None, result_url: Optional[str] = None) -> bool:
        with _schema_aware_db() as db:
            current_status = db.query(HSAIUGCTask.status).filter_by(id=task_id).scalar()
            if current_status == -2:
                return False

            now = datetime.utcnow()
            update_data = {
                "status": status,
                "updated_at": now,
                "last_progress_at": now,
                "progress_percent": self._status_to_percent(status),
            }
            if step is not None:
                update_data["step"] = step
            if result_url is not None:
                update_data["result_video_url"] = result_url
            
            result = db.query(HSAIUGCTask).filter_by(id=task_id).update(update_data)
            db.commit()
            return result > 0

    def close_task(self, task_id: str, *, closed_reason: str) -> bool:
        with _schema_aware_db() as db:
            now = datetime.utcnow()
            result = (
                db.query(HSAIUGCTask)
                .filter(HSAIUGCTask.id == task_id, HSAIUGCTask.status != -2)
                .update(
                    {
                        "status": -2,
                        "progress_percent": 0,
                        "closed_at": now,
                        "closed_reason": closed_reason,
                        "updated_at": now,
                        "last_progress_at": now,
                    },
                    synchronize_session=False,
                )
            )
            db.commit()
            return result > 0

    def get_tasks_by_user_id(self, user_id: str) -> List[VideoTaskData]:
        with _schema_aware_db() as db:
            tasks = db.query(HSAIUGCTask).filter_by(user_id=user_id).order_by(HSAIUGCTask.created_at.desc()).all()
            return [VideoTaskData.model_validate(t) for t in tasks]

    def mark_stale_tasks_closed(self, *, timeout_minutes: int = 60, statuses: Optional[List[int]] = None) -> int:
        """
        进度还原兜底：将长时间无进展的任务自动关闭 (status=-2)。
        默认只处理 status=1/3/5，避免用户长时间不编辑的 status=2 被误关闭。
        """
        with _schema_aware_db() as db:
            now = datetime.utcnow()
            threshold = now - timedelta(minutes=max(timeout_minutes, 0))

            effective_statuses = statuses or [1, 3, 5]
            q = db.query(HSAIUGCTask).filter(
                HSAIUGCTask.status.in_(effective_statuses),
                func.coalesce(HSAIUGCTask.last_progress_at, HSAIUGCTask.updated_at) < threshold,
            )
            count = q.count()
            if count <= 0:
                return 0

            q.update(
                {
                    "status": -2,
                    "progress_percent": 0,
                    "closed_at": now,
                    "closed_reason": "timeout",
                    "updated_at": now,
                    "last_progress_at": now,
                },
                synchronize_session=False,
            )
            db.commit()
            return count

    def mark_stale_tasks_failed(self, *, timeout_minutes: int = 30) -> int:
        """
        兼容旧接口：历史实现为超时标记失败(-1)。
        新实现已迁移为“超时关闭(-2)”，这里保留方法名以避免调用方崩溃。
        """
        return self.mark_stale_tasks_closed(timeout_minutes=timeout_minutes)

    def get_stale_retryable_tasks(self, *, timeout_minutes: int = 10) -> List[VideoTaskData]:
        """
        Get tasks that are stale but potentially retryable (e.g., status=3 with incomplete scenes).
        Phase 3: Watchdog will attempt to retry these instead of closing them immediately.
        """
        with _schema_aware_db() as db:
            now = datetime.utcnow()
            threshold = now - timedelta(minutes=max(timeout_minutes, 0))
            
            # Status 3 = Rendering (Generating Scenes)
            tasks = db.query(HSAIUGCTask).filter(
                HSAIUGCTask.status == 3,
                func.coalesce(HSAIUGCTask.last_progress_at, HSAIUGCTask.updated_at) < threshold
            ).limit(20).all() # Process in batches to avoid thundering herd
            
            return [VideoTaskData.model_validate(t) for t in tasks]

    def get_library_tasks(
        self,
        user_id: str,
        *,
        q: Optional[str] = None,
        status: Optional[List[int]] = None,
        model_id: Optional[int] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        order_by: str = "updated_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
        stale_timeout_minutes: int = 60,
    ) -> UGCLibraryTasksResponse:
        def _to_epoch(value: Any) -> int:
            if isinstance(value, datetime):
                dt = value
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
            return 0

        with _schema_aware_db() as db:
            page = max(int(page or 1), 1)
            page_size = max(min(int(page_size or 20), 100), 1)

            base_q = db.query(HSAIUGCTask).filter(HSAIUGCTask.user_id == user_id)
            if model_id is not None:
                base_q = base_q.filter(HSAIUGCTask.model_id == int(model_id))
            if status:
                base_q = base_q.filter(HSAIUGCTask.status.in_(status))
            if created_from is not None:
                base_q = base_q.filter(HSAIUGCTask.created_at >= created_from)
            if created_to is not None:
                base_q = base_q.filter(HSAIUGCTask.created_at <= created_to)
            if q:
                q_like = f"%{q.strip()}%"
                base_q = base_q.filter(
                    or_(
                        HSAIUGCTask.id.ilike(q_like),
                        cast(HSAIUGCTask.base_inputs, Text).ilike(q_like),
                    )
                )

            total = int(base_q.count() or 0)

            scenes_agg = (
                db.query(
                    HSAIUGCTaskScene.task_id.label("task_id"),
                    func.count(HSAIUGCTaskScene.id).label("scenes_total"),
                    func.sum(case((HSAIUGCTaskScene.fragment_video_url.isnot(None), 1), else_=0)).label("scenes_done"),
                )
                .group_by(HSAIUGCTaskScene.task_id)
                .subquery()
            )

            order_key = {
                "created_at": HSAIUGCTask.created_at,
                "updated_at": HSAIUGCTask.updated_at,
                "progress_percent": HSAIUGCTask.progress_percent,
            }.get(order_by, HSAIUGCTask.updated_at)
            order_expr = order_key.asc() if str(order).lower() == "asc" else order_key.desc()

            rows = (
                base_q.outerjoin(scenes_agg, scenes_agg.c.task_id == HSAIUGCTask.id)
                .add_columns(scenes_agg.c.scenes_total, scenes_agg.c.scenes_done)
                .order_by(order_expr)
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            threshold = datetime.utcnow() - timedelta(minutes=max(int(stale_timeout_minutes or 0), 0))

            items: List[UGCLibraryTaskItem] = []
            for task, scenes_total, scenes_done in rows:
                scenes_total_i = int(scenes_total or 0)
                scenes_done_i = int(scenes_done or 0)

                stage = self._status_to_stage(int(task.status or 0))
                message = self._status_to_message(int(task.status or 0), scenes_done=scenes_done_i, scenes_total=scenes_total_i)

                computed = self._status_to_percent(int(task.status or 0), scenes_done=scenes_done_i, scenes_total=scenes_total_i)
                stored = int(getattr(task, "progress_percent", 0) or 0)
                percent = max(stored, computed)

                in_progress = int(task.status or 0) not in (-2, -1, 6)
                lp_dt = getattr(task, "last_progress_at", None) or getattr(task, "updated_at", None)
                is_stale = bool(in_progress and isinstance(lp_dt, datetime) and lp_dt < threshold)

                base_inputs = getattr(task, "base_inputs", {}) or {}
                product_name = base_inputs.get("product_name") if isinstance(base_inputs, dict) else None

                items.append(
                    UGCLibraryTaskItem(
                        id=task.id,
                        user_id=str(task.user_id),
                        status=int(task.status or 0),
                        step=int(task.step or 0),
                        model_id=int(task.model_id or 0),
                        product_name=str(product_name) if product_name is not None else None,
                        progress_stage=stage,
                        progress_message=message,
                        progress_percent=int(max(min(percent, 100), 0)),
                        scenes_total=scenes_total_i,
                        scenes_done=scenes_done_i,
                        is_stale=is_stale,
                        result_video_url=getattr(task, "result_video_url", None),
                        created_at=_to_epoch(getattr(task, "created_at", None)),
                        updated_at=_to_epoch(getattr(task, "updated_at", None)),
                        last_progress_at=_to_epoch(getattr(task, "last_progress_at", None)) or None,
                        closed_at=_to_epoch(getattr(task, "closed_at", None)) or None,
                        closed_reason=getattr(task, "closed_reason", None),
                    )
                )

            return UGCLibraryTasksResponse(items=items, page=page, page_size=page_size, total=total)


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
                    reference_img_url=item.get("reference_img_url"),
                    image_prompt=item.get("image_prompt")
                )
                db.add(scene)
            db.commit()

    def get_scenes_by_task_id(self, task_id: str) -> List[TaskSceneData]:
        with _schema_aware_db() as db:
            scenes = db.query(HSAIUGCTaskScene).filter_by(task_id=task_id).order_by(HSAIUGCTaskScene.scene_index.asc()).all()
            return [TaskSceneData.model_validate(s) for s in scenes]

    def get_scene_by_index(self, task_id: str, scene_index: int) -> Optional[TaskSceneData]:
        """
        Get a single scene by (task_id, scene_index).
        """
        with _schema_aware_db() as db:
            scene = (
                db.query(HSAIUGCTaskScene)
                .filter_by(task_id=task_id, scene_index=scene_index)
                .first()
            )
            return TaskSceneData.model_validate(scene) if scene else None

    def update_scene(self, scene_id: int, form: TaskSceneUpdateForm) -> bool:
        with _schema_aware_db() as db:
            update_data = form.model_dump(exclude_unset=True)
            if not update_data:
                return True
            result = db.query(HSAIUGCTaskScene).filter_by(id=scene_id).update(update_data)
            db.commit()
            return result > 0

    def update_scene_by_index(self, task_id: str, scene_index: int, form: TaskSceneUpdateForm) -> bool:
        """
        Update a scene by (task_id, scene_index) instead of primary key id.
        """
        with _schema_aware_db() as db:
            update_data = form.model_dump(exclude_unset=True)
            if not update_data:
                return True
            result = (
                db.query(HSAIUGCTaskScene)
                .filter_by(task_id=task_id, scene_index=scene_index)
                .update(update_data)
            )
            db.commit()
            return result > 0

    def delete_scenes_except_indices(self, task_id: str, keep_indices: List[int]) -> int:
        """
        Delete scenes for a task except those whose scene_index is in keep_indices.
        This enables "selected scenes only" workflows while keeping original scene_index (can be non-contiguous).
        """
        keep = [int(v) for v in (keep_indices or []) if v is not None]
        with _schema_aware_db() as db:
            q = db.query(HSAIUGCTaskScene).filter_by(task_id=task_id)
            if keep:
                q = q.filter(~HSAIUGCTaskScene.scene_index.in_(keep))
            deleted = q.delete(synchronize_session=False)
            db.commit()
            return int(deleted or 0)

    def update_fragment_video_url(self, task_id: str, scene_index: int, video_url: str) -> bool:
        with _schema_aware_db() as db:
            result = (
                db.query(HSAIUGCTaskScene)
                .filter_by(task_id=task_id, scene_index=scene_index)
                .update({"fragment_video_url": video_url})
            )

            # 同步任务进度（主要用于 status=3 的“分镜视频生成中”场景）。
            # 注意：进度同步失败不影响主流程。
            try:
                current_status = db.query(HSAIUGCTask.status).filter_by(id=task_id).scalar()
                if current_status != -2:
                    total = db.query(func.count(HSAIUGCTaskScene.id)).filter_by(task_id=task_id).scalar() or 0
                    done = (
                        db.query(func.sum(case((HSAIUGCTaskScene.fragment_video_url.isnot(None), 1), else_=0)))
                        .filter_by(task_id=task_id)
                        .scalar()
                        or 0
                    )
                    percent = HSAIUGCTasksTable._status_to_percent(
                        int(current_status or 0),
                        scenes_done=int(done),
                        scenes_total=int(total),
                    )
                    now = datetime.utcnow()
                    db.query(HSAIUGCTask).filter_by(id=task_id).update(
                        {
                            "progress_percent": int(max(min(percent, 100), 0)),
                            "updated_at": now,
                            "last_progress_at": now,
                        }
                    )
            except Exception:
                pass
            db.commit()
            return result > 0

    def update_fragment_video_candidates(
        self,
        task_id: str,
        scene_index: int,
        candidates: List[str],
        *,
        selected_url: Optional[str] = None,
    ) -> bool:
        cleaned = [str(v) for v in (candidates or []) if v]
        if not cleaned:
            return False
        selected = selected_url or cleaned[0]
        with _schema_aware_db() as db:
            result = (
                db.query(HSAIUGCTaskScene)
                .filter_by(task_id=task_id, scene_index=scene_index)
                .update(
                    {
                        "fragment_video_urls": json.dumps(cleaned, ensure_ascii=False),
                        "fragment_video_url": selected,
                    }
                )
            )
            # 同步任务进度（主要用于 status=3 的“分镜视频生成中”场景）。
            try:
                current_status = db.query(HSAIUGCTask.status).filter_by(id=task_id).scalar()
                if current_status != -2:
                    total = db.query(func.count(HSAIUGCTaskScene.id)).filter_by(task_id=task_id).scalar() or 0
                    done = (
                        db.query(func.sum(case((HSAIUGCTaskScene.fragment_video_url.isnot(None), 1), else_=0)))
                        .filter_by(task_id=task_id)
                        .scalar()
                        or 0
                    )
                    percent = HSAIUGCTasksTable._status_to_percent(
                        int(current_status or 0),
                        scenes_done=int(done),
                        scenes_total=int(total),
                    )
                    now = datetime.utcnow()
                    db.query(HSAIUGCTask).filter_by(id=task_id).update(
                        {
                            "progress_percent": int(max(min(percent, 100), 0)),
                            "updated_at": now,
                            "last_progress_at": now,
                        }
                    )
            except Exception:
                pass
            db.commit()
            db.commit()
            return result > 0

    def increment_retry_count(self, task_id: str, scene_index: int, error_msg: Optional[str] = None) -> int:
        with _schema_aware_db() as db:
            scene = db.query(HSAIUGCTaskScene).filter_by(task_id=task_id, scene_index=scene_index).first()
            if not scene:
                return -1
            current = int(scene.retry_count or 0)
            scene.retry_count = current + 1
            if error_msg:
                scene.error_msg = error_msg
            db.commit()
            return scene.retry_count


class HSAIUGCProductsTable:
    def create_product(self, user_id: str, form: ProductCreateForm) -> ProductData:
        with _schema_aware_db() as db:
            prod = HSAIUGCProduct(
                user_id=user_id,
                name=form.name,
                description=form.description,
                cover_img=form.cover_img,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(prod)
            db.commit()
            db.refresh(prod)
            return ProductData.model_validate(prod)

    def get_product(self, product_id: int) -> Optional[ProductData]:
        with _schema_aware_db() as db:
            prod = db.query(HSAIUGCProduct).filter_by(id=product_id).first()
            return ProductData.model_validate(prod) if prod else None

    def get_products(
        self,
        user_id: str,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> "ProductsListResponse":
        with _schema_aware_db() as db:
            query = db.query(HSAIUGCProduct).filter_by(user_id=user_id)
            if q:
                # Simple name filter
                query = query.filter(HSAIUGCProduct.name.ilike(f"%{q}%"))
            
            # Get total count
            total = query.count()
            
            query = query.order_by(HSAIUGCProduct.updated_at.desc())
            
            offset = (max(1, page) - 1) * max(1, page_size)
            products = query.offset(offset).limit(max(1, page_size)).all()
            items = [ProductData.model_validate(p) for p in products]
            
            # Import at function level to avoid circular import
            from open_webui.models.hsai_ugc import ProductsListResponse
            return ProductsListResponse(items=items, page=page, page_size=page_size, total=total)

    def get_products_count(self, user_id: str, q: Optional[str] = None) -> int:
        with _schema_aware_db() as db:
            query = db.query(HSAIUGCProduct).filter_by(user_id=user_id)
            if q:
                query = query.filter(HSAIUGCProduct.name.ilike(f"%{q}%"))
            return query.count()

    def update_product(self, product_id: int, form: ProductUpdateForm) -> Optional[ProductData]:
        with _schema_aware_db() as db:
            prod = db.query(HSAIUGCProduct).filter_by(id=product_id).first()
            if not prod:
                return None
            
            update_data = form.model_dump(exclude_unset=True)
            for k, v in update_data.items():
                setattr(prod, k, v)
            
            prod.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(prod)
            return ProductData.model_validate(prod)

    def delete_product(self, product_id: int) -> bool:
        with _schema_aware_db() as db:
            prod = db.query(HSAIUGCProduct).filter_by(id=product_id).first()
            if not prod:
                return False
            db.delete(prod)
            db.commit()
            return True

class HSAIUGCCallbackLogsTable:
    def insert_log(
        self,
        message: Dict[str, Any],
        task_id: Optional[str] = None,
        msg_type: Optional[str] = None,
        error_msg: Optional[str] = None
    ) -> HSAIUGCCallbackLog:
        with _schema_aware_db() as db:
            log_entry = HSAIUGCCallbackLog(
                task_id=task_id,
                msg_type=msg_type,
                payload=message,
                error_msg=error_msg,
                created_at=datetime.utcnow(),
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return log_entry


# Singletons
MaterialModels = HSAIUGCMaterialModelsTable()
VideoTasks = HSAIUGCTasksTable()
TaskScenes = HSAIUGCTaskScenesTable()
Products = HSAIUGCProductsTable()
CallbackLogs = HSAIUGCCallbackLogsTable()
