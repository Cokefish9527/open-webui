import logging
import time
import uuid
from typing import Optional, List, Dict, Any
from enum import Enum

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# HSAI Chat DB Schema
####################

class HSAIChatType(str, Enum):
    """HSAI聊天类型枚举"""
    GENERAL = "general"           # 普通对话
    TASK_ORIENTED = "task_oriented"  # 任务导向对话
    WORKFLOW = "workflow"         # 工作流对话
    ANALYSIS = "analysis"         # 分析对话
    CREATIVE = "creative"         # 创意对话

class HSAIMessageType(str, Enum):
    """HSAI消息类型枚举"""
    USER = "user"                 # 用户消息
    ASSISTANT = "assistant"       # AI助手消息
    SYSTEM = "system"            # 系统消息
    TASK_RESULT = "task_result"  # 任务结果消息
    WORKFLOW_UPDATE = "workflow_update"  # 工作流更新消息

class HSAIChat(Base):
    """HSAI聊天会话表"""
    __tablename__ = "hsai_chats"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # 聊天类型和状态
    chat_type = Column(String, nullable=False, default=HSAIChatType.GENERAL)
    status = Column(String, default="active")  # active, archived, deleted
    
    # 所属用户
    user_id = Column(String, nullable=False)
    
    # 关联信息
    related_task_id = Column(String, ForeignKey("hsai_tasks.id"), nullable=True)
    related_workflow_id = Column(String, ForeignKey("hsai_workflows.id"), nullable=True)
    parent_chat_id = Column(String, ForeignKey("hsai_chats.id"), nullable=True)
    
    # 聊天配置
    config = Column(JSON, nullable=True)      # 聊天配置参数
    context = Column(JSON, nullable=True)     # 上下文信息
    metadata = Column(JSON, nullable=True)    # 元数据
    
    # 统计信息
    message_count = Column(BigInteger, default=0)
    last_message_at = Column(BigInteger, nullable=True)
    
    # 标签和分类
    tags = Column(JSON, nullable=True)
    category = Column(String, nullable=True)
    
    # 设置选项
    is_pinned = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

class HSAIMessage(Base):
    """HSAI消息表"""
    __tablename__ = "hsai_messages"

    id = Column(String, primary_key=True)
    chat_id = Column(String, ForeignKey("hsai_chats.id"), nullable=False)
    
    # 消息内容
    content = Column(Text, nullable=False)
    message_type = Column(String, nullable=False, default=HSAIMessageType.USER)
    
    # 发送者信息
    sender_id = Column(String, nullable=False)  # 用户ID或系统标识
    sender_name = Column(String, nullable=True)
    
    # 消息元数据
    metadata = Column(JSON, nullable=True)     # 消息元数据
    attachments = Column(JSON, nullable=True)  # 附件信息
    
    # 关联信息
    related_task_id = Column(String, ForeignKey("hsai_tasks.id"), nullable=True)
    parent_message_id = Column(String, ForeignKey("hsai_messages.id"), nullable=True)
    
    # 消息状态
    status = Column(String, default="sent")    # sent, delivered, read, failed
    is_edited = Column(Boolean, default=False)
    edit_history = Column(JSON, nullable=True)
    
    # AI相关
    model_used = Column(String, nullable=True)  # 使用的AI模型
    tokens_used = Column(BigInteger, nullable=True)  # 使用的token数量
    processing_time = Column(BigInteger, nullable=True)  # 处理时间(毫秒)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

class HSAIChatSession(Base):
    """HSAI聊天会话状态表"""
    __tablename__ = "hsai_chat_sessions"

    id = Column(String, primary_key=True)
    chat_id = Column(String, ForeignKey("hsai_chats.id"), nullable=False)
    user_id = Column(String, nullable=False)
    
    # 会话状态
    status = Column(String, default="active")  # active, idle, disconnected
    last_activity_at = Column(BigInteger, nullable=True)
    
    # 连接信息
    socket_id = Column(String, nullable=True)  # WebSocket连接ID
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    
    # 会话数据
    session_data = Column(JSON, nullable=True)  # 会话临时数据
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

####################
# Pydantic Models
####################

class HSAIChatModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    title: str
    description: Optional[str] = None
    chat_type: str
    status: str
    user_id: str
    related_task_id: Optional[str] = None
    related_workflow_id: Optional[str] = None
    parent_chat_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    message_count: int
    last_message_at: Optional[int] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    is_pinned: bool
    is_shared: bool
    created_at: int
    updated_at: int

class HSAIMessageModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    chat_id: str
    content: str
    message_type: str
    sender_id: str
    sender_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    related_task_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    status: str
    is_edited: bool
    edit_history: Optional[List[Dict[str, Any]]] = None
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time: Optional[int] = None
    created_at: int
    updated_at: int

class HSAIChatSessionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    chat_id: str
    user_id: str
    status: str
    last_activity_at: Optional[int] = None
    socket_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    session_data: Optional[Dict[str, Any]] = None
    created_at: int
    updated_at: int

####################
# Form Models
####################

class HSAIChatForm(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    chat_type: HSAIChatType = Field(default=HSAIChatType.GENERAL)
    related_task_id: Optional[str] = None
    related_workflow_id: Optional[str] = None
    parent_chat_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    is_pinned: bool = Field(default=False)
    is_shared: bool = Field(default=False)

class HSAIChatUpdateForm(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    chat_type: Optional[HSAIChatType] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_shared: Optional[bool] = None

class HSAIMessageForm(BaseModel):
    content: str = Field(..., min_length=1)
    message_type: HSAIMessageType = Field(default=HSAIMessageType.USER)
    sender_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    related_task_id: Optional[str] = None
    parent_message_id: Optional[str] = None

class HSAIMessageUpdateForm(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

####################
# Database Operations
####################

class HSAIChatsTable:
    def __init__(self, db):
        self.db = db

    def insert_new_chat(
        self, user_id: str, form_data: HSAIChatForm
    ) -> Optional[HSAIChatModel]:
        try:
            chat_id = str(uuid.uuid4())
            chat = HSAIChat(
                **{
                    "id": chat_id,
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    **form_data.model_dump(),
                }
            )
            self.db.add(chat)
            self.db.commit()
            self.db.refresh(chat)
            return HSAIChatModel.model_validate(chat)
        except Exception as e:
            log.exception(f"Error creating HSAI chat: {e}")
            self.db.rollback()
            return None

    def get_chat_by_id(self, chat_id: str) -> Optional[HSAIChatModel]:
        try:
            chat = self.db.query(HSAIChat).filter_by(id=chat_id).first()
            return HSAIChatModel.model_validate(chat) if chat else None
        except Exception as e:
            log.exception(f"Error getting HSAI chat by id: {e}")
            return None

    def get_chats_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> List[HSAIChatModel]:
        try:
            chats = (
                self.db.query(HSAIChat)
                .filter_by(user_id=user_id)
                .filter(HSAIChat.status != "deleted")
                .order_by(HSAIChat.updated_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [HSAIChatModel.model_validate(chat) for chat in chats]
        except Exception as e:
            log.exception(f"Error getting HSAI chats by user id: {e}")
            return []

    def update_chat_by_id(
        self, chat_id: str, form_data: HSAIChatUpdateForm
    ) -> Optional[HSAIChatModel]:
        try:
            chat = self.db.query(HSAIChat).filter_by(id=chat_id).first()
            if not chat:
                return None

            update_data = form_data.model_dump(exclude_unset=True)
            update_data["updated_at"] = int(time.time())

            for key, value in update_data.items():
                setattr(chat, key, value)

            self.db.commit()
            self.db.refresh(chat)
            return HSAIChatModel.model_validate(chat)
        except Exception as e:
            log.exception(f"Error updating HSAI chat: {e}")
            self.db.rollback()
            return None

    def delete_chat_by_id(self, chat_id: str) -> bool:
        try:
            chat = self.db.query(HSAIChat).filter_by(id=chat_id).first()
            if not chat:
                return False

            chat.status = "deleted"
            chat.updated_at = int(time.time())
            self.db.commit()
            return True
        except Exception as e:
            log.exception(f"Error deleting HSAI chat: {e}")
            self.db.rollback()
            return False

class HSAIMessagesTable:
    def __init__(self, db):
        self.db = db

    def insert_new_message(
        self, chat_id: str, sender_id: str, form_data: HSAIMessageForm
    ) -> Optional[HSAIMessageModel]:
        try:
            message_id = str(uuid.uuid4())
            message = HSAIMessage(
                **{
                    "id": message_id,
                    "chat_id": chat_id,
                    "sender_id": sender_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    **form_data.model_dump(),
                }
            )
            self.db.add(message)
            
            # 更新聊天的消息计数和最后消息时间
            chat = self.db.query(HSAIChat).filter_by(id=chat_id).first()
            if chat:
                chat.message_count += 1
                chat.last_message_at = int(time.time())
                chat.updated_at = int(time.time())
            
            self.db.commit()
            self.db.refresh(message)
            return HSAIMessageModel.model_validate(message)
        except Exception as e:
            log.exception(f"Error creating HSAI message: {e}")
            self.db.rollback()
            return None

    def get_messages_by_chat_id(
        self, chat_id: str, skip: int = 0, limit: int = 50
    ) -> List[HSAIMessageModel]:
        try:
            messages = (
                self.db.query(HSAIMessage)
                .filter_by(chat_id=chat_id)
                .order_by(HSAIMessage.created_at.asc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [HSAIMessageModel.model_validate(msg) for msg in messages]
        except Exception as e:
            log.exception(f"Error getting HSAI messages by chat id: {e}")
            return []

    def update_message_by_id(
        self, message_id: str, form_data: HSAIMessageUpdateForm
    ) -> Optional[HSAIMessageModel]:
        try:
            message = self.db.query(HSAIMessage).filter_by(id=message_id).first()
            if not message:
                return None

            update_data = form_data.model_dump(exclude_unset=True)
            update_data["updated_at"] = int(time.time())

            # 如果内容被修改，记录编辑历史
            if "content" in update_data and update_data["content"] != message.content:
                edit_history = message.edit_history or []
                edit_history.append({
                    "old_content": message.content,
                    "edited_at": int(time.time())
                })
                update_data["edit_history"] = edit_history
                update_data["is_edited"] = True

            for key, value in update_data.items():
                setattr(message, key, value)

            self.db.commit()
            self.db.refresh(message)
            return HSAIMessageModel.model_validate(message)
        except Exception as e:
            log.exception(f"Error updating HSAI message: {e}")
            self.db.rollback()
            return None

####################
# Global instances
####################

HSAIChats = HSAIChatsTable(get_db())
HSAIMessages = HSAIMessagesTable(get_db())