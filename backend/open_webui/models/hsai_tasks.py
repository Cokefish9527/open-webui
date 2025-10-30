import logging
import time
import uuid
from typing import Optional, List, Dict, Any
from enum import Enum

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import BigInteger, Column, String, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from ._timestamp_utils import (
    normalize_optional_timestamp,
    normalize_required_timestamp,
    EpochTimestamp,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# HSAI Tasks DB Schema
####################


class HSAITaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HSAITaskType(str, Enum):
    """任务类型枚举"""
    VIDEO_CREATION = "video_creation"
    CONTENT_ANALYSIS = "content_analysis"
    MATERIAL_PROCESSING = "material_processing"
    PLATFORM_PUBLISHING = "platform_publishing"
    WORKFLOW_EXECUTION = "workflow_execution"


class HSAIRecurringState(str, Enum):
    """循环任务运行状态"""
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    EXTERNAL_CONTROLLED = "external_controlled"


class HSAICardType(str, Enum):
    """卡片类型枚举"""
    TASK_CARD = "task_card"
    MATERIAL_CARD = "material_card"
    WORKFLOW_CARD = "workflow_card"
    ANALYSIS_CARD = "analysis_card"
    PUBLISH_CARD = "publish_card"


class HSAITask(Base):
    """HSAI任务表"""
    __tablename__ = "hsai_tasks"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # 任务类型和状态
    task_type = Column(String, nullable=False)
    task_category = Column(String, nullable=True)  # 任务分类
    status = Column(String, nullable=False, default=HSAITaskStatus.PENDING)
    
    # 所属用户和会话
    user_id = Column(String, nullable=False)
    assignee_id = Column(String, nullable=True)  # 指派人ID
    chat_id = Column(String, nullable=True)  # 关联的聊天会话ID
    
    # 项目关联
    project_id = Column(String, ForeignKey("hsai_projects.id"), nullable=True)  # 关联的项目ID
    
    # 任务配置和参数
    config = Column(JSON, nullable=True)  # 任务配置参数
    prompt_config = Column(JSON, nullable=True)  # 提示词配置

    # 循环任务
    is_recurring = Column(Boolean, nullable=False, default=False)
    recurring_state = Column(String, nullable=True, default=HSAIRecurringState.IDLE.value)
    last_run_at = Column(EpochTimestamp(), nullable=True)
    next_run_at = Column(EpochTimestamp(), nullable=True)
    external_controller = Column(String, nullable=True)
    recurring_meta = Column(JSON, nullable=True)

    # 工作流相关
    workflow_id = Column(String, ForeignKey("hsai_workflows.id"), nullable=True)
    parent_task_id = Column(String, ForeignKey("hsai_tasks.id"), nullable=True)
    
    # 进度和时间
    progress = Column(BigInteger, default=0)  # 进度百分比(0-100)
    started_at = Column(BigInteger, nullable=True)
    completed_at = Column(EpochTimestamp(), nullable=True)
    
    # 优先级
    priority = Column(BigInteger, default=0)  # 优先级，数字越大越优先
    
    created_at = Column(EpochTimestamp())
    updated_at = Column(EpochTimestamp())


class HSAIWorkflow(Base):
    """HSAI工作流表"""
    __tablename__ = "hsai_workflows"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # 所属用户
    user_id = Column(String, nullable=False)
    
    # 工作流配置
    definition = Column(JSON, nullable=False)  # 工作流定义(节点、连接等)
    variables = Column(JSON, nullable=True)    # 工作流变量
    
    # 状态管理
    status = Column(String, default="active")  # active, inactive, archived
    version = Column(String, default="1.0")
    
    # 使用统计
    execution_count = Column(BigInteger, default=0)
    last_executed_at = Column(BigInteger, nullable=True)
    
    # 标签和分类
    category = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    
    created_at = Column(EpochTimestamp())
    updated_at = Column(EpochTimestamp())


class HSAICard(Base):
    """HSAI卡片表 - 用于对话界面的卡片展示"""
    __tablename__ = "hsai_cards"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # 卡片类型和状态
    card_type = Column(String, nullable=False)
    status = Column(String, default="active")
    
    # 所属关系
    user_id = Column(String, nullable=False)
    chat_id = Column(String, nullable=True)  # 关联的聊天会话
    task_id = Column(String, ForeignKey("hsai_tasks.id"), nullable=True)  # 关联的任务
    
    # 卡片内容和配置
    content = Column(JSON, nullable=True)     # 卡片内容数据
    config = Column(JSON, nullable=True)      # 卡片配置
    actions = Column(JSON, nullable=True)     # 可执行的操作
    
    # 布局和样式
    position = Column(JSON, nullable=True)    # 卡片位置信息
    style = Column(JSON, nullable=True)       # 卡片样式配置
    
    # 交互状态
    is_pinned = Column(Boolean, default=False)  # 是否固定
    is_collapsed = Column(Boolean, default=False)  # 是否折叠
    
    # 排序和显示
    sort_order = Column(BigInteger, default=0)
    
    created_at = Column(EpochTimestamp())
    updated_at = Column(EpochTimestamp())


class HSAIWorkflowExecution(Base):
    """HSAI工作流执行记录表"""
    __tablename__ = "hsai_workflow_executions"

    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("hsai_workflows.id"), nullable=False)
    
    # 执行信息
    user_id = Column(String, nullable=False)
    trigger_task_id = Column(String, ForeignKey("hsai_tasks.id"), nullable=True)
    
    # 执行状态
    status = Column(String, default=HSAITaskStatus.PENDING)
    progress = Column(BigInteger, default=0)
    
    # 输入输出
    inputs = Column(JSON, nullable=True)
    outputs = Column(JSON, nullable=True)
    execution_log = Column(JSON, nullable=True)  # 执行日志
    
    # 时间信息
    started_at = Column(BigInteger, nullable=True)
    completed_at = Column(EpochTimestamp(), nullable=True)
    
    # 错误处理
    error_message = Column(Text, nullable=True)
    
    created_at = Column(EpochTimestamp())
    updated_at = Column(EpochTimestamp())


####################
# Pydantic Models
####################


class HSAITaskModel(BaseModel):
    """HSAI任务模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="任务唯一标识符")
    title: str = Field(description="任务标题")
    description: Optional[str] = Field(default=None, description="任务详细描述")
    task_type: str = Field(description="任务类型")
    task_category: Optional[str] = Field(default=None, description="任务分类")
    status: str = Field(default=HSAITaskStatus.PENDING, description="任务状态")
    user_id: str = Field(description="用户ID")
    assignee_id: Optional[str] = Field(default=None, description="指派人ID")
    chat_id: Optional[str] = Field(default=None, description="关联的会话ID")
    project_id: Optional[str] = Field(default=None, description="关联的项目ID")
    config: Optional[dict] = Field(default=None, description="任务配置参数")
    prompt_config: Optional[dict] = Field(default=None, description="提示词配置")
    workflow_id: Optional[str] = Field(default=None, description="关联工作流ID")
    parent_task_id: Optional[str] = Field(default=None, description="父任务ID")
    is_recurring: bool = Field(default=False, description="是否循环任务")
    recurring_state: Optional[str] = Field(default=None, description="循环任务运行状态")
    last_run_at: Optional[int] = Field(default=None, description="最近运行时间戳")
    next_run_at: Optional[int] = Field(default=None, description="下次计划运行时间戳")
    external_controller: Optional[str] = Field(default=None, description="外部控制方标识")
    recurring_meta: Optional[dict] = Field(default=None, description="循环任务扩展元数据")
    progress: int = Field(default=0, description="进度百分比(0-100)")
    started_at: Optional[int] = Field(default=None, description="开始时间戳")
    completed_at: Optional[int] = Field(default=None, description="完成时间戳")
    priority: int = Field(default=0, description="优先级，数字越大越优先")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_required_timestamps(cls, value):
        if value is None:
            raise ValueError("Timestamp value cannot be None")
        try:
            return normalize_required_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp value: {exc}") from exc

    @field_validator("started_at", "completed_at", "last_run_at", "next_run_at", mode="before")
    @classmethod
    def validate_optional_timestamps(cls, value):
        if value is None:
            return None
        try:
            return normalize_optional_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid optional timestamp value: {exc}") from exc


class HSAIWorkflowModel(BaseModel):
    """HSAI工作流模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="工作流唯一标识符")
    name: str = Field(description="工作流名称")
    description: Optional[str] = Field(default=None, description="工作流描述")
    user_id: str = Field(description="用户ID")
    definition: dict = Field(description="工作流定义(节点、连接等)")
    variables: Optional[dict] = Field(default=None, description="工作流变量")
    status: str = Field(default="active", description="状态管理")
    version: str = Field(default="1.0", description="版本号")
    execution_count: int = Field(default=0, description="执行次数")
    last_executed_at: Optional[int] = Field(default=None, description="最后执行时间戳")
    category: Optional[str] = Field(default=None, description="分类")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_workflow_required_timestamps(cls, value):
        if value is None:
            raise ValueError("Timestamp value cannot be None")
        try:
            return normalize_required_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp value: {exc}") from exc

    @field_validator("last_executed_at", mode="before")
    @classmethod
    def validate_workflow_optional_timestamp(cls, value):
        if value is None:
            return None
        try:
            return normalize_optional_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid optional timestamp value: {exc}") from exc


class HSAICardModel(BaseModel):
    """HSAI卡片模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="卡片唯一标识符")
    title: str = Field(description="卡片标题")
    description: Optional[str] = Field(default=None, description="卡片描述")
    card_type: str = Field(description="卡片类型")
    status: str = Field(default="active", description="卡片状态")
    user_id: str = Field(description="用户ID")
    chat_id: Optional[str] = Field(default=None, description="关联的聊天会话")
    task_id: Optional[str] = Field(default=None, description="关联的任务")
    content: Optional[dict] = Field(default=None, description="卡片内容数据")
    config: Optional[dict] = Field(default=None, description="卡片配置")
    actions: Optional[dict] = Field(default=None, description="可执行的操作")
    position: Optional[dict] = Field(default=None, description="卡片位置信息")
    style: Optional[dict] = Field(default=None, description="卡片样式配置")
    is_pinned: bool = Field(default=False, description="是否固定")
    is_collapsed: bool = Field(default=False, description="是否折叠")
    sort_order: int = Field(default=0, description="排序和显示")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_card_required_timestamps(cls, value):
        if value is None:
            raise ValueError("Timestamp value cannot be None")
        try:
            return normalize_required_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp value: {exc}") from exc


####################
# Forms
####################


class HSAITaskForm(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: str
    task_category: Optional[str] = None
    assignee_id: Optional[str] = None
    chat_id: Optional[str] = None
    project_id: Optional[str] = None
    config: Optional[dict] = None
    prompt_config: Optional[dict] = None
    workflow_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    is_recurring: Optional[bool] = False
    recurring_state: Optional[str] = None
    last_run_at: Optional[int] = None
    next_run_at: Optional[int] = None
    external_controller: Optional[str] = None
    recurring_meta: Optional[dict] = None
    priority: Optional[int] = 0


class HSAIWorkflowForm(BaseModel):
    name: str
    description: Optional[str] = None
    definition: dict
    variables: Optional[dict] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class HSAICardForm(BaseModel):
    title: str
    description: Optional[str] = None
    card_type: str
    chat_id: Optional[str] = None
    task_id: Optional[str] = None
    content: Optional[dict] = None
    config: Optional[dict] = None
    actions: Optional[dict] = None
    position: Optional[dict] = None
    style: Optional[dict] = None
    is_pinned: Optional[bool] = False
    is_collapsed: Optional[bool] = False
    sort_order: Optional[int] = 0


class HSAITaskUpdateForm(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    task_category: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    project_id: Optional[str] = None
    config: Optional[dict] = None
    prompt_config: Optional[dict] = None
    workflow_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurring_state: Optional[str] = None
    last_run_at: Optional[int] = None
    next_run_at: Optional[int] = None
    external_controller: Optional[str] = None
    recurring_meta: Optional[dict] = None
    progress: Optional[int] = None
    priority: Optional[int] = None


####################
# Response Models
####################


class HSAITaskResponse(BaseModel):
    id: str = Field(description="任务唯一标识符")
    title: str = Field(description="任务标题")
    description: Optional[str] = Field(default=None, description="任务详细描述")
    task_type: str = Field(description="任务类型")
    task_category: Optional[str] = Field(default=None, description="任务分类")
    status: str = Field(description="任务状态")
    assignee_id: Optional[str] = Field(default=None, description="任务指派人ID")
    project_id: Optional[str] = Field(default=None, description="关联的项目ID")
    workflow_id: Optional[str] = Field(default=None, description="关联工作流ID")
    parent_task_id: Optional[str] = Field(default=None, description="父任务ID")
    is_recurring: bool = Field(default=False, description="是否循环任务")
    recurring_state: Optional[str] = Field(default=None, description="循环任务运行状态")
    last_run_at: Optional[int] = Field(default=None, description="最近运行时间戳")
    next_run_at: Optional[int] = Field(default=None, description="下次计划运行时间戳")
    external_controller: Optional[str] = Field(default=None, description="外部控制方标识")
    recurring_meta: Optional[dict] = Field(default=None, description="循环任务扩展元数据")
    progress: int = Field(default=0, description="任务进度百分比(0-100)")
    priority: int = Field(default=0, description="任务优先级")
    started_at: Optional[int] = Field(default=None, description="任务开始时间戳")
    completed_at: Optional[int] = Field(default=None, description="任务完成时间戳")
    config: Optional[dict] = Field(default=None, description="任务配置参数")
    prompt_config: Optional[dict] = Field(default=None, description="提示词配置")
    estimated_duration: Optional[int] = Field(default=None, description="预估耗时(秒)")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class HSAICardResponse(BaseModel):
    id: str = Field(description="卡片唯一标识符")
    title: str = Field(description="卡片标题")
    description: Optional[str] = Field(default=None, description="卡片描述")
    card_type: str = Field(description="卡片类型")
    content: Optional[dict] = Field(default=None, description="卡片内容数据")
    actions: Optional[dict] = Field(default=None, description="卡片操作配置")
    position: Optional[dict] = Field(default=None, description="卡片位置信息")
    style: Optional[dict] = Field(default=None, description="卡片样式配置")
    is_pinned: bool = Field(default=False, description="是否置顶")
    is_collapsed: bool = Field(default=False, description="是否折叠")
    task_status: Optional[str] = Field(default=None, description="关联任务的状态")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class PaginationData(BaseModel):
    """分页数据模型"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")


class PaginatedHSAITaskResponse(BaseModel):
    """分页的任务响应模型"""
    data: List[HSAITaskResponse] = Field(description="任务数据列表")
    pagination: PaginationData = Field(description="分页信息")


class PaginatedHSAICardResponse(BaseModel):
    """分页的卡片响应模型"""
    data: List[HSAICardResponse] = Field(description="卡片数据列表")
    pagination: PaginationData = Field(description="分页信息")


class HSAITaskStateLog(Base):
    """循环任务状态日志"""
    __tablename__ = "hsai_task_state_logs"

    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("hsai_tasks.id"), nullable=False)
    from_state = Column(String, nullable=True)
    to_state = Column(String, nullable=False)
    operator_id = Column(String, nullable=True)
    operator_name = Column(String, nullable=True)
    source = Column(String, nullable=True)  # admin_console / api / automation
    message = Column(Text, nullable=True)
    snapshot_json = Column(JSON, nullable=True)
    created_at = Column(EpochTimestamp(), nullable=False)


class HSAITaskStateLogModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    from_state: Optional[str] = None
    to_state: str
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    source: Optional[str] = None
    message: Optional[str] = None
    snapshot_json: Optional[Dict[str, Any]] = None
    created_at: int


####################
# Database Tables
####################


class HSAITasksTable:
    def insert_new_task(
        self, user_id: str, form_data: HSAITaskForm
    ) -> Optional[HSAITaskModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            task = HSAITaskModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = HSAITask(**task.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return HSAITaskModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating task: {e}")
                return None

    def get_tasks_by_user_id(
        self,
        user_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        assignee_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        project_id: Optional[str] = None,
        task_category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[HSAITaskModel]:
        with get_db() as db:
            try:
                query = db.query(HSAITask).filter_by(user_id=user_id)
                
                if status:
                    query = query.filter_by(status=status)
                if task_type:
                    query = query.filter_by(task_type=task_type)
                if assignee_id:
                    query = query.filter_by(assignee_id=assignee_id)
                if chat_id:
                    query = query.filter_by(chat_id=chat_id)
                if project_id:
                    query = query.filter_by(project_id=project_id)
                if task_category:
                    query = query.filter_by(task_category=task_category)
                
                tasks = query.order_by(
                    HSAITask.priority.desc(),
                    HSAITask.updated_at.desc()
                ).limit(limit).offset(offset).all()
                
                return [HSAITaskModel.model_validate(task) for task in tasks]
            except Exception as e:
                log.exception(f"Error getting tasks: {e}")
                return []

    def get_tasks_count(
        self,
        user_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        assignee_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        project_id: Optional[str] = None,
        task_category: Optional[str] = None,
    ) -> int:
        """获取任务总数"""
        with get_db() as db:
            try:
                query = db.query(HSAITask).filter_by(user_id=user_id)
                
                if status:
                    query = query.filter_by(status=status)
                if task_type:
                    query = query.filter_by(task_type=task_type)
                if assignee_id:
                    query = query.filter_by(assignee_id=assignee_id)
                if chat_id:
                    query = query.filter_by(chat_id=chat_id)
                if project_id:
                    query = query.filter_by(project_id=project_id)
                if task_category:
                    query = query.filter_by(task_category=task_category)
                
                return query.count()
            except Exception as e:
                log.exception(f"Error counting tasks: {e}")
                return 0

    def get_task_by_id(self, task_id: str) -> Optional[HSAITaskModel]:
        with get_db() as db:
            try:
                task = db.get(HSAITask, task_id)
                return HSAITaskModel.model_validate(task) if task else None
            except Exception:
                return None

    def update_task_by_id(
        self, task_id: str, form_data: HSAITaskUpdateForm
    ) -> Optional[HSAITaskModel]:
        with get_db() as db:
            try:
                task = db.get(HSAITask, task_id)
                if task:
                    for key, value in form_data.model_dump(exclude_unset=True).items():
                        setattr(task, key, value)
                    setattr(task, 'updated_at', int(time.time()))
                    
                    # 自动设置时间戳
                    if form_data.status == HSAITaskStatus.IN_PROGRESS and not getattr(task, 'started_at'):
                        setattr(task, 'started_at', int(time.time()))
                    elif form_data.status in [HSAITaskStatus.COMPLETED, HSAITaskStatus.FAILED]:
                        setattr(task, 'completed_at', int(time.time()))
                    
                    db.commit()
                    db.refresh(task)
                    return HSAITaskModel.model_validate(task)
                return None
            except Exception as e:
                log.exception(f"Error updating task: {e}")
                return None

    def update_task_progress(self, task_id: str, progress: int) -> bool:
        """更新任务进度"""
        with get_db() as db:
            try:
                task = db.get(HSAITask, task_id)
                if task:
                    setattr(task, 'progress', max(0, min(100, progress)))  # 确保进度在0-100之间
                    setattr(task, 'updated_at', int(time.time()))
                    
                    if progress == 100 and getattr(task, 'status') != HSAITaskStatus.COMPLETED:
                        setattr(task, 'status', HSAITaskStatus.COMPLETED)
                        setattr(task, 'completed_at', int(time.time()))
                    
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.exception(f"Error updating task progress: {e}")
            return False


class HSAITaskStateLogsTable:
    def append_log(
        self,
        task_id: str,
        to_state: str,
        from_state: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        source: Optional[str] = None,
        message: Optional[str] = None,
        snapshot_json: Optional[Dict[str, Any]] = None,
    ) -> HSAITaskStateLogModel:
        with get_db() as db:
            log_entry = HSAITaskStateLog(
                id=str(uuid.uuid4()),
                task_id=task_id,
                from_state=from_state,
                to_state=to_state,
                operator_id=operator_id,
                operator_name=operator_name,
                source=source,
                message=message,
                snapshot_json=snapshot_json,
                created_at=int(time.time()),
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return HSAITaskStateLogModel.model_validate(log_entry)

    def list_logs(self, task_id: str, limit: int = 50) -> List[HSAITaskStateLogModel]:
        with get_db() as db:
            records = (
                db.query(HSAITaskStateLog)
                .filter_by(task_id=task_id)
                .order_by(HSAITaskStateLog.created_at.desc())
                .limit(limit)
                .all()
            )
            return [HSAITaskStateLogModel.model_validate(item) for item in records]


class HSAICardsTable:
    def insert_new_card(
        self, user_id: str, form_data: HSAICardForm
    ) -> Optional[HSAICardModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            card = HSAICardModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = HSAICard(**card.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return HSAICardModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating card: {e}")
                return None

    def get_cards_by_chat_id(
        self, chat_id: str, limit: int = 20, offset: int = 0
    ) -> List[HSAICardModel]:
        with get_db() as db:
            try:
                cards = db.query(HSAICard).filter_by(
                    chat_id=chat_id, status="active"
                ).order_by(HSAICard.sort_order.asc()).limit(limit).offset(offset).all()
                
                return [HSAICardModel.model_validate(card) for card in cards]
            except Exception as e:
                log.exception(f"Error getting cards: {e}")
                return []

    def get_cards_count(self, chat_id: str) -> int:
        """获取卡片总数"""
        with get_db() as db:
            try:
                return db.query(HSAICard).filter_by(
                    chat_id=chat_id, status="active"
                ).count()
            except Exception as e:
                log.exception(f"Error counting cards: {e}")
                return 0

    def update_card_by_id(
        self, card_id: str, updates: dict
    ) -> Optional[HSAICardModel]:
        with get_db() as db:
            try:
                card = db.get(HSAICard, card_id)
                if card:
                    for key, value in updates.items():
                        if hasattr(card, key):
                            setattr(card, key, value)
                    setattr(card, 'updated_at', int(time.time()))
                    db.commit()
                    db.refresh(card)
                    return HSAICardModel.model_validate(card)
                return None
            except Exception as e:
                log.exception(f"Error updating card: {e}")
                return None


# 全局实例
HSAITasks = HSAITasksTable()
HSAITaskStateLogs = HSAITaskStateLogsTable()
HSAICards = HSAICardsTable()
