import logging
import time
import uuid
from typing import Optional, List
from enum import Enum

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# HSAI Matrix Management DB Schema
####################


class HSAIPlatformType(str, Enum):
    """平台类型枚举"""
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    WEIBO = "weibo"


class HSAIPublishStatus(str, Enum):
    """发布状态枚举"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HSAIAccountStatus(str, Enum):
    """账号状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class HSAIPlatformAccount(Base):
    """HSAI平台账号表"""
    __tablename__ = "hsai_platform_accounts"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)  # 账号显示名称
    platform_type = Column(String, nullable=False)  # 平台类型
    
    # 所属用户
    user_id = Column(String, nullable=False)
    
    # 账号信息
    platform_account_id = Column(String, nullable=False)  # 平台上的账号ID
    username = Column(String, nullable=False)  # 用户名
    display_name = Column(String, nullable=True)  # 显示名称
    avatar_url = Column(String, nullable=True)  # 头像URL
    
    # 授权信息
    access_token = Column(Text, nullable=True)  # 访问令牌
    refresh_token = Column(Text, nullable=True)  # 刷新令牌
    token_expires_at = Column(BigInteger, nullable=True)  # 令牌过期时间
    
    # 账号配置
    config = Column(JSON, nullable=True)  # 平台特定配置
    permissions = Column(JSON, nullable=True)  # 权限范围
    
    # 状态管理
    status = Column(String, default=HSAIAccountStatus.ACTIVE)
    last_sync_at = Column(BigInteger, nullable=True)  # 最后同步时间
    
    # 统计信息
    follower_count = Column(BigInteger, default=0)  # 粉丝数
    following_count = Column(BigInteger, default=0)  # 关注数
    posts_count = Column(BigInteger, default=0)  # 发布数
    
    # 标签和分组
    tags = Column(JSON, nullable=True)
    group_id = Column(String, nullable=True)  # 账号分组
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class HSAIPublishTask(Base):
    """HSAI发布任务表"""
    __tablename__ = "hsai_publish_tasks"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # 所属用户和任务
    user_id = Column(String, nullable=False)
    hsai_task_id = Column(String, nullable=True)  # 关联的HSAI任务ID
    
    # 内容信息
    content = Column(JSON, nullable=False)  # 发布内容(文本、图片、视频等)
    content_type = Column(String, nullable=False)  # video, image, carousel, story
    
    # 发布配置
    platforms = Column(JSON, nullable=False)  # 要发布的平台列表
    publish_config = Column(JSON, nullable=True)  # 发布配置(标题、标签、时间等)
    
    # 状态和进度
    status = Column(String, default=HSAIPublishStatus.DRAFT)
    progress = Column(BigInteger, default=0)  # 发布进度(0-100)
    
    # 调度信息
    scheduled_at = Column(BigInteger, nullable=True)  # 定时发布时间
    published_at = Column(BigInteger, nullable=True)  # 实际发布时间
    
    # 错误处理
    error_message = Column(Text, nullable=True)
    retry_count = Column(BigInteger, default=0)
    
    # 标签和优先级
    tags = Column(JSON, nullable=True)
    priority = Column(BigInteger, default=0)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class HSAIPublishRecord(Base):
    """HSAI发布记录表"""
    __tablename__ = "hsai_publish_records"

    id = Column(String, primary_key=True)
    publish_task_id = Column(String, ForeignKey("hsai_publish_tasks.id"), nullable=False)
    platform_account_id = Column(String, ForeignKey("hsai_platform_accounts.id"), nullable=False)
    
    # 发布结果
    platform_post_id = Column(String, nullable=True)  # 平台上的帖子ID
    platform_url = Column(String, nullable=True)  # 平台URL
    
    # 状态信息
    status = Column(String, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # 发布数据
    publish_data = Column(JSON, nullable=True)  # 发布时的数据快照
    response_data = Column(JSON, nullable=True)  # 平台返回的数据
    
    # 统计数据(需要定期更新)
    views = Column(BigInteger, default=0)
    likes = Column(BigInteger, default=0)
    comments = Column(BigInteger, default=0)
    shares = Column(BigInteger, default=0)
    
    # 时间信息
    published_at = Column(BigInteger, nullable=True)
    last_stats_update_at = Column(BigInteger, nullable=True)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class HSAIAccountGroup(Base):
    """HSAI账号分组表"""
    __tablename__ = "hsai_account_groups"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String, nullable=True)  # 分组颜色
    
    # 所属用户
    user_id = Column(String, nullable=False)
    
    # 分组配置
    config = Column(JSON, nullable=True)
    sort_order = Column(BigInteger, default=0)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class HSAIAnalytics(Base):
    """HSAI数据分析表"""
    __tablename__ = "hsai_analytics"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    
    # 分析维度
    dimension_type = Column(String, nullable=False)  # account, platform, content_type, time
    dimension_value = Column(String, nullable=False)  # 具体维度值
    
    # 时间范围
    date = Column(String, nullable=False)  # YYYY-MM-DD格式
    period_type = Column(String, nullable=False)  # daily, weekly, monthly
    
    # 指标数据
    metrics = Column(JSON, nullable=False)  # 各种指标数据
    
    # 比较数据
    previous_metrics = Column(JSON, nullable=True)  # 上一周期的数据
    growth_rate = Column(JSON, nullable=True)  # 增长率
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic Models
####################


class HSAIPlatformAccountModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    platform_type: str
    user_id: str
    platform_account_id: str
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[int] = None
    config: Optional[dict] = None
    permissions: Optional[dict] = None
    status: str = HSAIAccountStatus.ACTIVE
    last_sync_at: Optional[int] = None
    follower_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    tags: Optional[List[str]] = None
    group_id: Optional[str] = None
    created_at: int
    updated_at: int


class HSAIPublishTaskModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    user_id: str
    hsai_task_id: Optional[str] = None
    content: dict
    content_type: str
    platforms: List[str]
    publish_config: Optional[dict] = None
    status: str = HSAIPublishStatus.DRAFT
    progress: int = 0
    scheduled_at: Optional[int] = None
    published_at: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    tags: Optional[List[str]] = None
    priority: int = 0
    created_at: int
    updated_at: int


class HSAIPublishRecordModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    publish_task_id: str
    platform_account_id: str
    platform_post_id: Optional[str] = None
    platform_url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    publish_data: Optional[dict] = None
    response_data: Optional[dict] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    published_at: Optional[int] = None
    last_stats_update_at: Optional[int] = None
    created_at: int
    updated_at: int


####################
# Forms
####################


class HSAIPlatformAccountForm(BaseModel):
    name: str
    platform_type: str
    platform_account_id: str
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[int] = None
    config: Optional[dict] = None
    permissions: Optional[dict] = None
    tags: Optional[List[str]] = None
    group_id: Optional[str] = None


class HSAIPublishTaskForm(BaseModel):
    title: str
    description: Optional[str] = None
    hsai_task_id: Optional[str] = None
    content: dict
    content_type: str
    platforms: List[str]
    publish_config: Optional[dict] = None
    scheduled_at: Optional[int] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = 0


class HSAIAccountGroupForm(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    config: Optional[dict] = None
    sort_order: Optional[int] = 0


####################
# Response Models
####################


class HSAIPlatformAccountResponse(BaseModel):
    id: str = Field(description="账号唯一标识符")
    name: str = Field(description="账号名称")
    platform_type: str = Field(description="平台类型")
    username: str = Field(description="用户名")
    display_name: Optional[str] = Field(default=None, description="显示名称")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    status: str = Field(description="账号状态")
    follower_count: int = Field(default=0, description="粉丝数量")
    following_count: int = Field(default=0, description="关注数量")
    posts_count: int = Field(default=0, description="发布数量")
    last_sync_at: Optional[int] = Field(default=None, description="最后同步时间戳")
    is_token_valid: bool = Field(default=True, description="令牌是否有效")
    group_name: Optional[str] = Field(default=None, description="分组名称")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class HSAIPublishTaskResponse(BaseModel):
    id: str = Field(description="发布任务唯一标识符")
    title: str = Field(description="任务标题")
    description: Optional[str] = Field(default=None, description="任务描述")
    content_type: str = Field(description="内容类型")
    status: str = Field(description="任务状态")
    progress: int = Field(default=0, description="任务进度百分比 (0-100)")
    platforms: List[str] = Field(description="目标平台列表")
    scheduled_at: Optional[int] = Field(default=None, description="计划发布时间戳")
    published_at: Optional[int] = Field(default=None, description="实际发布时间戳")
    success_count: int = Field(default=0, description="成功发布的平台数")
    total_count: int = Field(default=0, description="总平台数")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class HSAIPublishStatsResponse(BaseModel):
    """发布统计响应"""
    total_posts: int = Field(default=0, description="总发布数")
    published_posts: int = Field(default=0, description="已发布数")
    scheduled_posts: int = Field(default=0, description="计划发布数")
    failed_posts: int = Field(default=0, description="失败发布数")
    total_views: int = Field(default=0, description="总浏览量")
    total_likes: int = Field(default=0, description="总点赞数")
    total_comments: int = Field(default=0, description="总评论数")
    total_shares: int = Field(default=0, description="总分享数")
    engagement_rate: float = Field(default=0.0, description="互动率")


####################
# Database Tables
####################


class HSAIPlatformAccountsTable:
    def insert_new_account(
        self, user_id: str, form_data: HSAIPlatformAccountForm
    ) -> Optional[HSAIPlatformAccountModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            account = HSAIPlatformAccountModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = HSAIPlatformAccount(**account.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return HSAIPlatformAccountModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating platform account: {e}")
                return None

    def get_accounts_by_user_id(
        self, user_id: str, platform_type: Optional[str] = None, status: Optional[str] = None
    ) -> List[HSAIPlatformAccountModel]:
        with get_db() as db:
            try:
                query = db.query(HSAIPlatformAccount).filter_by(user_id=user_id)
                
                if platform_type:
                    query = query.filter_by(platform_type=platform_type)
                if status:
                    query = query.filter_by(status=status)
                
                accounts = query.order_by(HSAIPlatformAccount.created_at.desc()).all()
                return [HSAIPlatformAccountModel.model_validate(account) for account in accounts]
            except Exception as e:
                log.exception(f"Error getting platform accounts: {e}")
                return []

    def get_account_by_id(self, account_id: str) -> Optional[HSAIPlatformAccountModel]:
        with get_db() as db:
            try:
                account = db.get(HSAIPlatformAccount, account_id)
                return HSAIPlatformAccountModel.model_validate(account) if account else None
            except Exception:
                return None

    def update_account_token(
        self, account_id: str, access_token: str, refresh_token: Optional[str] = None,
        expires_at: Optional[int] = None
    ) -> bool:
        """更新账号令牌"""
        with get_db() as db:
            try:
                account = db.get(HSAIPlatformAccount, account_id)
                if account:
                    account.access_token = access_token
                    if refresh_token:
                        account.refresh_token = refresh_token
                    if expires_at:
                        account.token_expires_at = expires_at
                    account.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error updating account token: {e}")
                return False

    def update_account_stats(
        self, account_id: str, follower_count: int, following_count: int, posts_count: int
    ) -> bool:
        """更新账号统计数据"""
        with get_db() as db:
            try:
                account = db.get(HSAIPlatformAccount, account_id)
                if account:
                    account.follower_count = follower_count
                    account.following_count = following_count
                    account.posts_count = posts_count
                    account.last_sync_at = int(time.time())
                    account.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error updating account stats: {e}")
                return False


class HSAIPublishTasksTable:
    def insert_new_publish_task(
        self, user_id: str, form_data: HSAIPublishTaskForm
    ) -> Optional[HSAIPublishTaskModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            task = HSAIPublishTaskModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = HSAIPublishTask(**task.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return HSAIPublishTaskModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating publish task: {e}")
                return None

    def get_publish_tasks_by_user_id(
        self, user_id: str, status: Optional[str] = None
    ) -> List[HSAIPublishTaskModel]:
        with get_db() as db:
            try:
                query = db.query(HSAIPublishTask).filter_by(user_id=user_id)
                
                if status:
                    query = query.filter_by(status=status)
                
                tasks = query.order_by(
                    HSAIPublishTask.priority.desc(),
                    HSAIPublishTask.created_at.desc()
                ).all()
                
                return [HSAIPublishTaskModel.model_validate(task) for task in tasks]
            except Exception as e:
                log.exception(f"Error getting publish tasks: {e}")
                return []

    def update_publish_task_status(
        self, task_id: str, status: str, progress: Optional[int] = None, 
        error_message: Optional[str] = None
    ) -> bool:
        """更新发布任务状态"""
        with get_db() as db:
            try:
                task = db.get(HSAIPublishTask, task_id)
                if task:
                    task.status = status
                    if progress is not None:
                        task.progress = max(0, min(100, progress))
                    if error_message is not None:
                        task.error_message = error_message
                    if status == HSAIPublishStatus.PUBLISHED:
                        task.published_at = int(time.time())
                    task.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error updating publish task status: {e}")
                return False


class HSAIAccountGroupModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    user_id: str
    config: Optional[dict] = None
    sort_order: int = 0
    created_at: int
    updated_at: int


# 全局实例
HSAIPlatformAccounts = HSAIPlatformAccountsTable()
HSAIPublishTasks = HSAIPublishTasksTable()
