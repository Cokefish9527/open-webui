import enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, relationship

from open_webui.internal.db import Base


class SocialAccountStatus(str, enum.Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class SocialAccountHealth(str, enum.Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class SocialPostStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SocialRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False)
    handle = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    encrypted_credentials_ref = Column(String, nullable=False)
    playwright_profile_path = Column(String, nullable=False)
    vpn_profile_id = Column(String, nullable=False)
    device_fingerprint_hash = Column(String, nullable=True)
    status = Column(String, nullable=False, default=SocialAccountStatus.INACTIVE.value)
    health_status = Column(String, nullable=False, default=SocialAccountHealth.UNKNOWN.value)
    last_rotation_at = Column(BigInteger, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=True)

    posts: Mapped[List["SocialPost"]] = relationship(
        "SocialPost", back_populates="account", cascade="all, delete-orphan"
    )


class SocialCampaign(Base):
    __tablename__ = "social_campaigns"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    schedule_strategy = Column(String, nullable=True)
    status = Column(String, nullable=False, default="draft")
    created_by = Column(String, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=True)

    posts: Mapped[List["SocialPost"]] = relationship(
        "SocialPost", back_populates="campaign", cascade="all, delete-orphan"
    )


class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("social_campaigns.id"), nullable=True, index=True)
    account_id = Column(String, ForeignKey("social_accounts.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    caption = Column(Text, nullable=True)
    media_assets = Column(JSON, nullable=True)
    post_metadata = Column("metadata", JSON, nullable=True)
    schedule_time = Column(BigInteger, nullable=True, index=True)
    status = Column(String, nullable=False, default=SocialPostStatus.DRAFT.value, index=True)
    approval_user_id = Column(String, nullable=True)
    approval_time = Column(BigInteger, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=True)

    account: Mapped[SocialAccount] = relationship("SocialAccount", back_populates="posts")
    campaign: Mapped[Optional[SocialCampaign]] = relationship("SocialCampaign", back_populates="posts")
    runs: Mapped[List["SocialAutomationRun"]] = relationship(
        "SocialAutomationRun", back_populates="post", cascade="all, delete-orphan"
    )


class SocialAutomationRun(Base):
    __tablename__ = "social_automation_runs"

    id = Column(String, primary_key=True)
    post_id = Column(String, ForeignKey("social_posts.id"), nullable=True, index=True)
    trigger_source = Column(String, nullable=False)
    mcp_request_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default=SocialRunStatus.PENDING.value, index=True)
    result_payload = Column(JSON, nullable=True)
    screenshot_path = Column(String, nullable=True)
    har_path = Column(String, nullable=True)
    proxy_exit_ip = Column(String, nullable=True)
    duration_ms = Column(BigInteger, nullable=True)
    error_reason = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=True)

    post: Mapped[Optional[SocialPost]] = relationship("SocialPost", back_populates="runs")


class SocialAccountModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    platform: str
    handle: str
    display_name: Optional[str] = None
    status: SocialAccountStatus
    health_status: SocialAccountHealth
    vpn_profile_id: str
    last_rotation_at: Optional[int] = None
    created_at: int
    updated_at: Optional[int] = None


class SocialCampaignModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    schedule_strategy: Optional[str] = None
    status: str
    created_at: int
    updated_at: Optional[int] = None


class SocialPostModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    campaign_id: Optional[str] = None
    account_id: str
    title: Optional[str] = None
    caption: Optional[str] = None
    media_assets: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="post_metadata")
    schedule_time: Optional[int] = None
    status: SocialPostStatus
    approval_user_id: Optional[str] = None
    approval_time: Optional[int] = None
    created_at: int
    updated_at: Optional[int] = None


class SocialAutomationRunModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    post_id: Optional[str] = None
    trigger_source: str
    mcp_request_id: Optional[str] = None
    status: SocialRunStatus
    result_payload: Optional[Dict[str, Any]] = None
    screenshot_path: Optional[str] = None
    har_path: Optional[str] = None
    proxy_exit_ip: Optional[str] = None
    duration_ms: Optional[int] = None
    error_reason: Optional[str] = None
    created_at: int
    updated_at: Optional[int] = None
