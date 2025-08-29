import logging
import time
import uuid
from typing import Optional, List
from enum import Enum

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship

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
    status = Column(String, nullable=False, default=HSAITaskStatus.PENDING)
    
    # 所属用户和会话
    user_id = Column(String, nullable=False)
    chat_id = Column(String, nullable=True)  # 关联的聊天会话ID
    
    # 任务配置和参数
    config = Column(JSON, nullable=True)  # 任务配置参数
    inputs = Column(JSON, nullable=True)  # 输入参数
    outputs = Column(JSON, nullable=True)  # 输出结果
    
    # 工作流相关
    workflow_id = Column(String, ForeignKey("hsai_workflows.id"), nullable=True)
    parent_task_id = Column(String, ForeignKey("hsai_tasks.id"), nullable=True)
    
    # 进度和时间
    progress = Column(BigInteger, default=0)  # 进度百分比(0-100)
    started_at = Column(BigInteger, nullable=True)
    completed_at = Column(BigInteger, nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    retry_count = Column(BigInteger, default=0)
    
    # 优先级和标签
    priority = Column(BigInteger, default=0)  # 优先级，数字越大越优先
    tags = Column(JSON, nullable=True)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


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
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


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
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


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
    completed_at = Column(BigInteger, nullable=True)
    
    # 错误处理
    error_message = Column(Text, nullable=True)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic Models
####################


class HSAITaskModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    task_type: str
    status: str = HSAITaskStatus.PENDING
    user_id: str
    chat_id: Optional[str] = None
    config: Optional[dict] = None
    inputs: Optional[dict] = None
    outputs: Optional[dict] = None
    workflow_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    progress: int = 0
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    priority: int = 0
    tags: Optional[List[str]] = None
    created_at: int
    updated_at: int


class HSAIWorkflowModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    user_id: str
    definition: dict
    variables: Optional[dict] = None
    status: str = "active"
    version: str = "1.0"
    execution_count: int = 0
    last_executed_at: Optional[int] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: int
    updated_at: int


class HSAICardModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    card_type: str
    status: str = "active"
    user_id: str
    chat_id: Optional[str] = None
    task_id: Optional[str] = None
    content: Optional[dict] = None
    config: Optional[dict] = None
    actions: Optional[dict] = None
    position: Optional[dict] = None
    style: Optional[dict] = None
    is_pinned: bool = False
    is_collapsed: bool = False
    sort_order: int = 0
    created_at: int
    updated_at: int


####################
# Forms
####################


class HSAITaskForm(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: str
    chat_id: Optional[str] = None
    config: Optional[dict] = None
    inputs: Optional[dict] = None
    workflow_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    priority: Optional[int] = 0
    tags: Optional[List[str]] = None


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
    status: Optional[str] = None
    config: Optional[dict] = None
    inputs: Optional[dict] = None
    outputs: Optional[dict] = None
    progress: Optional[int] = None
    error_message: Optional[str] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None


####################
# Response Models
####################


class HSAITaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    task_type: str
    status: str
    progress: int = 0
    priority: int = 0
    tags: Optional[List[str]] = None
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    error_message: Optional[str] = None
    estimated_duration: Optional[int] = None  # 预估耗时(秒)
    created_at: int
    updated_at: int


class HSAICardResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    card_type: str
    content: Optional[dict] = None
    actions: Optional[dict] = None
    position: Optional[dict] = None
    style: Optional[dict] = None
    is_pinned: bool = False
    is_collapsed: bool = False
    task_status: Optional[str] = None  # 关联任务的状态
    created_at: int
    updated_at: int


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
        chat_id: Optional[str] = None
    ) -> List[HSAITaskModel]:
        with get_db() as db:
            try:
                query = db.query(HSAITask).filter_by(user_id=user_id)
                
                if status:
                    query = query.filter_by(status=status)
                if task_type:
                    query = query.filter_by(task_type=task_type)
                if chat_id:
                    query = query.filter_by(chat_id=chat_id)
                    
                tasks = query.order_by(
                    HSAITask.priority.desc(),
                    HSAITask.updated_at.desc()
                ).all()
                
                return [HSAITaskModel.model_validate(task) for task in tasks]
            except Exception as e:
                log.exception(f"Error getting tasks: {e}")
                return []

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
                    task.updated_at = int(time.time())
                    
                    # 自动设置时间戳
                    if form_data.status == HSAITaskStatus.IN_PROGRESS and not task.started_at:
                        task.started_at = int(time.time())
                    elif form_data.status in [HSAITaskStatus.COMPLETED, HSAITaskStatus.FAILED]:
                        task.completed_at = int(time.time())
                    
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
                    task.progress = max(0, min(100, progress))  # 确保进度在0-100之间
                    task.updated_at = int(time.time())
                    
                    if progress == 100 and task.status != HSAITaskStatus.COMPLETED:
                        task.status = HSAITaskStatus.COMPLETED
                        task.completed_at = int(time.time())
                    
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error updating task progress: {e}")
                return False


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

    def get_cards_by_chat_id(self, chat_id: str) -> List[HSAICardModel]:
        with get_db() as db:
            try:
                cards = db.query(HSAICard).filter_by(
                    chat_id=chat_id, status="active"
                ).order_by(HSAICard.sort_order.asc()).all()
                
                return [HSAICardModel.model_validate(card) for card in cards]
            except Exception as e:
                log.exception(f"Error getting cards: {e}")
                return []

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
                    card.updated_at = int(time.time())
                    db.commit()
                    db.refresh(card)
                    return HSAICardModel.model_validate(card)
                return None
            except Exception as e:
                log.exception(f"Error updating card: {e}")
                return None


# 全局实例
HSAITasks = HSAITasksTable()
HSAICards = HSAICardsTable()