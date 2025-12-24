import logging
import time
from typing import Optional, List, Dict, Any

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import BigInteger, Column, String, Text, Integer
from sqlalchemy import func

from ._timestamp_utils import normalize_required_timestamp

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", "INFO"))

####################
# HSAI TikTok Publish Log DB Schema
####################


class HSAITikTokPublishLog(Base):
    """TikTok 视频发布日志表"""

    __tablename__ = "hsai_tiktok_publish_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(String, nullable=False)
    project_id = Column(String, nullable=True)
    social_account_id = Column(BigInteger, nullable=False)
    mode = Column(String, nullable=False)  # INBOX / DIRECT
    video_url = Column(Text, nullable=False)
    caption = Column(Text, nullable=True)
    status = Column(String, nullable=False)  # success / failed
    error_message = Column(Text, nullable=True)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


####################
# Pydantic Models
####################


class HSAITikTokPublishLogModel(BaseModel):
    """TikTok 发布日志记录"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Auto-increment primary key")
    company_id: str = Field(description="业务公司 ID")
    project_id: Optional[str] = Field(default=None, description="项目 ID（可为空）")
    social_account_id: int = Field(description="social_accounts 主键 ID")
    mode: str = Field(description="发布模式：INBOX / DIRECT")
    video_url: str = Field(description="被 TikTok PULL_FROM_URL 访问的 HTTPS 视频地址")
    caption: Optional[str] = Field(default=None, description="视频文案 / 描述")
    status: str = Field(description="发布状态：success / failed")
    error_message: Optional[str] = Field(default=None, description="错误信息（如有）")

    created_at: int = Field(description="创建时间戳（秒）")
    updated_at: int = Field(description="更新时间戳（秒）")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_required_timestamps(cls, value: Any):
        if value is None:
            raise ValueError("Timestamp value cannot be None")
        try:
            return normalize_required_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp value: {exc}") from exc


class HSAITikTokPublishLogForm(BaseModel):
    """TikTok 发布日志插入表单"""

    company_id: str
    project_id: Optional[str] = None
    social_account_id: int
    mode: str
    video_url: str
    caption: Optional[str] = None
    status: str
    error_message: Optional[str] = None


####################
# Table Helper
####################


class HSAITikTokPublishLogsTable:
    """TikTok 发布日志表操作类"""

    def _now(self) -> int:
        return int(time.time())

    def insert_log(self, form: HSAITikTokPublishLogForm) -> Optional[HSAITikTokPublishLogModel]:
        """插入新的 TikTok 发布日志记录"""
        payload = form.model_dump(exclude_unset=True)
        now_ts = self._now()
        with get_db() as db:
            try:
                record = HSAITikTokPublishLog(
                    **payload,
                    created_at=now_ts,
                    updated_at=now_ts,
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                return HSAITikTokPublishLogModel.model_validate(record)
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed inserting TikTok publish log: %s", exc, exc_info=True)
                db.rollback()
                return None

    def record_publish(
        self,
        *,
        company_id: str,
        project_id: Optional[str],
        social_account_id: int,
        mode: str,
        video_url: str,
        caption: Optional[str],
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[HSAITikTokPublishLogModel]:
        """便捷方法：根据发布参数记录一次日志"""
        form = HSAITikTokPublishLogForm(
            company_id=company_id,
            project_id=project_id,
            social_account_id=social_account_id,
            mode=mode,
            video_url=video_url,
            caption=caption,
            status=status,
            error_message=error_message,
        )
        return self.insert_log(form)

    def list_logs(
        self,
        *,
        company_id: Optional[str] = None,
        project_id: Optional[str] = None,
        mode: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[HSAITikTokPublishLogModel]:
        """按条件筛选 TikTok 发布日志"""
        with get_db() as db:
            try:
                query = db.query(HSAITikTokPublishLog)
                if company_id:
                    query = query.filter(HSAITikTokPublishLog.company_id == company_id)
                if project_id:
                    query = query.filter(HSAITikTokPublishLog.project_id == project_id)
                if mode:
                    query = query.filter(HSAITikTokPublishLog.mode == mode)
                if status:
                    query = query.filter(HSAITikTokPublishLog.status == status)

                total = query.count()
                rows = (
                    query.order_by(HSAITikTokPublishLog.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                models: List[HSAITikTokPublishLogModel] = [
                    HSAITikTokPublishLogModel.model_validate(row) for row in rows
                ]
                # 将总数挂到模型列表的自定义属性上，方便调用方复用
                for m in models:
                    setattr(m, "_total_count", total)
                return models
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed listing TikTok publish logs: %s", exc, exc_info=True)
                return []

    def count_logs(
        self,
        *,
        company_id: Optional[str] = None,
        project_id: Optional[str] = None,
        mode: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """统计满足条件的日志总数"""
        with get_db() as db:
            try:
                query = db.query(HSAITikTokPublishLog)
                if company_id:
                    query = query.filter(HSAITikTokPublishLog.company_id == company_id)
                if project_id:
                    query = query.filter(HSAITikTokPublishLog.project_id == project_id)
                if mode:
                    query = query.filter(HSAITikTokPublishLog.mode == mode)
                if status:
                    query = query.filter(HSAITikTokPublishLog.status == status)
                return query.count()
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed counting TikTok publish logs: %s", exc, exc_info=True)
                return 0

    def get_last_publish_at(
        self,
        *,
        company_id: str,
        project_id: str,
        status: str = "success",
    ) -> Optional[int]:
        """获取某项目最近一次发布的时间戳（秒），默认仅统计 success。"""
        if not company_id or not project_id:
            return None
        with get_db() as db:
            try:
                query = db.query(func.max(HSAITikTokPublishLog.created_at)).filter(
                    HSAITikTokPublishLog.company_id == company_id,
                    HSAITikTokPublishLog.project_id == project_id,
                )
                if status:
                    query = query.filter(HSAITikTokPublishLog.status == status)
                value = query.scalar()
                return int(value) if value is not None else None
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed getting last TikTok publish time: %s", exc, exc_info=True)
                return None

    def count_publishes_since(
        self,
        *,
        company_id: str,
        project_id: str,
        since_ts: int,
        status: str = "success",
        mode: Optional[str] = None,
    ) -> int:
        """统计某项目从某时间点以来的发布次数（默认仅 success），可按 mode 过滤。"""
        if not company_id or not project_id:
            return 0
        with get_db() as db:
            try:
                query = db.query(func.count(HSAITikTokPublishLog.id)).filter(
                    HSAITikTokPublishLog.company_id == company_id,
                    HSAITikTokPublishLog.project_id == project_id,
                    HSAITikTokPublishLog.created_at >= int(since_ts),
                )
                if status:
                    query = query.filter(HSAITikTokPublishLog.status == status)
                if mode:
                    query = query.filter(HSAITikTokPublishLog.mode == mode)
                return int(query.scalar() or 0)
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed counting TikTok publishes since=%s: %s", since_ts, exc, exc_info=True)
                return 0


HSAITikTokPublishLogs = HSAITikTokPublishLogsTable()
