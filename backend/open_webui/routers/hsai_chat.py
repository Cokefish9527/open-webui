import logging
import time
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel

from open_webui.models.chats import Chats, ChatForm
from open_webui.models.hsai_tasks import HSAITasks
from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.socket.main import get_event_emitter

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/chat", tags=["hsai_chat"])

############################
# 数据模型定义
############################

class ChatSessionResponse(BaseModel):
    """对话会话响应模型"""
    id: str
    title: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    message_count: int
    last_message_at: int
    created_at: int
    updated_at: int
    tags: List[str] = []
    is_pinned: bool = False
    task_id: Optional[str] = None  # 关联的任务ID

class ChatSessionForm(BaseModel):
    """对话会话创建表单"""
    title: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    tags: List[str] = []
    task_id: Optional[str] = None

class ChatMessageForm(BaseModel):
    """聊天消息表单"""
    content: str
    role: str = "user"  # user, assistant, system
    model: Optional[str] = None
    stream: bool = False

class ChatMessageResponse(BaseModel):
    """聊天消息响应模型"""
    id: str
    role: str
    content: str
    timestamp: int
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatStatsResponse(BaseModel):
    """对话统计响应模型"""
    total_sessions: int
    active_sessions: int
    total_messages: int
    avg_messages_per_session: float
    most_used_model: Optional[str] = None
    total_tokens_used: int = 0

############################
# 对话会话管理
############################

@router.get("/sessions", response_model=List[ChatSessionResponse], summary="获取对话会话列表")
async def get_chat_sessions(
    limit: int = Query(50, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    tag: Optional[str] = Query(None, description="标签过滤"),
    task_id: Optional[str] = Query(None, description="任务ID过滤"),
    user=Depends(get_verified_user)
):
    """
    获取用户的对话会话列表。
    
    返回用户的所有对话会话，支持分页和过滤。
    
    Args:
        limit (int): 返回数量限制，默认50
        offset (int): 偏移量，默认0
        tag (Optional[str]): 标签过滤
        task_id (Optional[str]): 任务ID过滤
        user: 已认证的用户对象
        
    Returns:
        List[ChatSessionResponse]: 对话会话列表
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 获取用户的所有对话
        user_chats = Chats.get_chats_by_user_id(user.id, skip=offset, limit=limit)
        
        sessions = []
        for chat in user_chats:
            # 计算消息数量
            messages = chat.chat.get("messages", []) if chat.chat else []
            message_count = len(messages)
            
            # 获取最后消息时间
            last_message_at = chat.updated_at
            if messages:
                # 如果有消息，使用最后一条消息的时间
                last_message = messages[-1]
                if isinstance(last_message, dict) and "timestamp" in last_message:
                    last_message_at = last_message["timestamp"]
            
            # 获取标签（从chat数据中提取）
            tags = []
            if chat.chat and isinstance(chat.chat, dict):
                tags = chat.chat.get("tags", [])
            
            # 检查是否关联任务
            task_id = None
            if chat.chat and isinstance(chat.chat, dict):
                task_id = chat.chat.get("task_id")
            
            # 标签过滤
            if tag and tag not in tags:
                continue
                
            # 任务过滤
            if task_id and task_id != task_id:
                continue
            
            session = ChatSessionResponse(
                id=chat.id,
                title=chat.title or "未命名对话",
                model=chat.chat.get("model") if chat.chat else None,
                system_prompt=chat.chat.get("system") if chat.chat else None,
                message_count=message_count,
                last_message_at=last_message_at,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                tags=tags,
                is_pinned=chat.chat.get("pinned", False) if chat.chat else False,
                task_id=task_id
            )
            sessions.append(session)
        
        return sessions
        
    except Exception as e:
        log.exception(f"Error getting chat sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/sessions", response_model=ChatSessionResponse, summary="创建对话会话")
async def create_chat_session(
    form_data: ChatSessionForm,
    user=Depends(get_verified_user)
):
    """
    创建新的对话会话。
    
    创建一个新的AI对话会话，可以关联到特定任务。
    
    Args:
        form_data (ChatSessionForm): 会话创建表单
        user: 已认证的用户对象
        
    Returns:
        ChatSessionResponse: 创建的会话信息
        
    Raises:
        HTTPException: 400 - 创建失败
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 生成会话标题
        title = form_data.title or f"对话 {time.strftime('%Y-%m-%d %H:%M')}"
        
        # 构建聊天数据
        chat_data = {
            "messages": [],
            "model": form_data.model,
            "system": form_data.system_prompt,
            "tags": form_data.tags,
            "task_id": form_data.task_id,
            "pinned": False,
            "created_at": int(time.time())
        }
        
        # 创建聊天表单
        chat_form = ChatForm(
            chat=chat_data,
            title=title
        )
        
        # 创建聊天会话
        chat = Chats.insert_new_chat(user.id, chat_form)
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create chat session"
            )
        
        # 如果关联了任务，更新任务的聊天ID
        if form_data.task_id:
            try:
                HSAITasks.update_task_by_id(form_data.task_id, {
                    "chat_id": chat.id,
                    "updated_at": int(time.time())
                })
            except Exception as e:
                log.warning(f"Failed to update task chat_id: {e}")
        
        return ChatSessionResponse(
            id=chat.id,
            title=chat.title,
            model=form_data.model,
            system_prompt=form_data.system_prompt,
            message_count=0,
            last_message_at=chat.created_at,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            tags=form_data.tags,
            is_pinned=False,
            task_id=form_data.task_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse, summary="获取会话详情")
async def get_chat_session(
    session_id: str,
    user=Depends(get_verified_user)
):
    """
    获取指定对话会话的详细信息。
    
    Args:
        session_id (str): 会话ID
        user: 已认证的用户对象
        
    Returns:
        ChatSessionResponse: 会话详细信息
        
    Raises:
        HTTPException: 404 - 会话不存在或无权限访问
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 获取聊天会话
        chat = Chats.get_chat_by_id_and_user_id(session_id, user.id)
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # 计算消息数量
        messages = chat.chat.get("messages", []) if chat.chat else []
        message_count = len(messages)
        
        # 获取最后消息时间
        last_message_at = chat.updated_at
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, dict) and "timestamp" in last_message:
                last_message_at = last_message["timestamp"]
        
        return ChatSessionResponse(
            id=chat.id,
            title=chat.title or "未命名对话",
            model=chat.chat.get("model") if chat.chat else None,
            system_prompt=chat.chat.get("system") if chat.chat else None,
            message_count=message_count,
            last_message_at=last_message_at,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            tags=chat.chat.get("tags", []) if chat.chat else [],
            is_pinned=chat.chat.get("pinned", False) if chat.chat else False,
            task_id=chat.chat.get("task_id") if chat.chat else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.put("/sessions/{session_id}", summary="更新会话信息")
async def update_chat_session(
    session_id: str,
    title: Optional[str] = None,
    tags: Optional[List[str]] = None,
    is_pinned: Optional[bool] = None,
    user=Depends(get_verified_user)
):
    """
    更新对话会话信息。
    
    Args:
        session_id (str): 会话ID
        title (Optional[str]): 新标题
        tags (Optional[List[str]]): 新标签列表
        is_pinned (Optional[bool]): 是否置顶
        user: 已认证的用户对象
        
    Returns:
        dict: 更新结果
        
    Raises:
        HTTPException: 404 - 会话不存在或无权限访问
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 获取聊天会话
        chat = Chats.get_chat_by_id_and_user_id(session_id, user.id)
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # 准备更新数据
        update_data = {}
        
        if title is not None:
            update_data["title"] = title
        
        # 更新聊天数据中的标签和置顶状态
        if tags is not None or is_pinned is not None:
            chat_data = chat.chat or {}
            if tags is not None:
                chat_data["tags"] = tags
            if is_pinned is not None:
                chat_data["pinned"] = is_pinned
            update_data["chat"] = chat_data
        
        if update_data:
            update_data["updated_at"] = int(time.time())
            result = Chats.update_chat_by_id(session_id, update_data)
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update chat session"
                )
        
        return {"success": True, "message": "Chat session updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_chat_session(
    session_id: str,
    user=Depends(get_verified_user)
):
    """
    删除对话会话。
    
    Args:
        session_id (str): 会话ID
        user: 已认证的用户对象
        
    Returns:
        dict: 删除结果
        
    Raises:
        HTTPException: 404 - 会话不存在或无权限访问
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 验证会话所有权
        chat = Chats.get_chat_by_id_and_user_id(session_id, user.id)
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # 删除会话
        result = Chats.delete_chat_by_id_and_user_id(session_id, user.id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete chat session"
            )
        
        return {"success": True, "message": "Chat session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error deleting chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 消息管理
############################

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse], summary="获取会话消息")
async def get_chat_messages(
    session_id: str,
    limit: int = Query(50, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    user=Depends(get_verified_user)
):
    """
    获取对话会话的消息列表。
    
    Args:
        session_id (str): 会话ID
        limit (int): 返回数量限制
        offset (int): 偏移量
        user: 已认证的用户对象
        
    Returns:
        List[ChatMessageResponse]: 消息列表
        
    Raises:
        HTTPException: 404 - 会话不存在或无权限访问
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 获取聊天会话
        chat = Chats.get_chat_by_id_and_user_id(session_id, user.id)
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # 获取消息列表
        messages = chat.chat.get("messages", []) if chat.chat else []
        
        # 应用分页
        paginated_messages = messages[offset:offset + limit]
        
        # 转换为响应格式
        response_messages = []
        for i, msg in enumerate(paginated_messages):
            if isinstance(msg, dict):
                response_messages.append(ChatMessageResponse(
                    id=msg.get("id", f"msg_{offset + i}"),
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    timestamp=msg.get("timestamp", int(time.time())),
                    model=msg.get("model"),
                    metadata=msg.get("metadata")
                ))
        
        return response_messages
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting chat messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse, summary="发送消息")
async def send_chat_message(
    session_id: str,
    message_data: ChatMessageForm,
    user=Depends(get_verified_user)
):
    """
    向对话会话发送消息。
    
    Args:
        session_id (str): 会话ID
        message_data (ChatMessageForm): 消息数据
        user: 已认证的用户对象
        
    Returns:
        ChatMessageResponse: 发送的消息信息
        
    Raises:
        HTTPException: 404 - 会话不存在或无权限访问
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 获取聊天会话
        chat = Chats.get_chat_by_id_and_user_id(session_id, user.id)
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # 创建新消息
        message_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        new_message = {
            "id": message_id,
            "role": message_data.role,
            "content": message_data.content,
            "timestamp": timestamp,
            "model": message_data.model,
            "metadata": {}
        }
        
        # 更新聊天数据
        chat_data = chat.chat or {}
        messages = chat_data.get("messages", [])
        messages.append(new_message)
        chat_data["messages"] = messages
        
        # 更新数据库
        update_result = Chats.update_chat_by_id(session_id, {
            "chat": chat_data,
            "updated_at": timestamp
        })
        
        if not update_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send message"
            )
        
        # 通过WebSocket通知
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_chat_message",
                {
                    "session_id": session_id,
                    "message": new_message,
                    "user_id": user.id
                },
                to=user.id
            )
        
        return ChatMessageResponse(
            id=message_id,
            role=message_data.role,
            content=message_data.content,
            timestamp=timestamp,
            model=message_data.model,
            metadata={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error sending chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 统计接口
############################

@router.get("/stats", response_model=ChatStatsResponse, summary="获取对话统计")
async def get_chat_stats(
    user=Depends(get_verified_user)
):
    """
    获取用户的对话统计数据。
    
    Args:
        user: 已认证的用户对象
        
    Returns:
        ChatStatsResponse: 对话统计数据
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 获取用户的所有对话
        user_chats = Chats.get_chats_by_user_id(user.id)
        
        total_sessions = len(user_chats)
        active_sessions = 0
        total_messages = 0
        model_usage = {}
        
        for chat in user_chats:
            # 检查是否为活跃会话（最近7天有更新）
            if chat.updated_at > int(time.time()) - 7 * 24 * 3600:
                active_sessions += 1
            
            # 统计消息数量
            if chat.chat and "messages" in chat.chat:
                messages = chat.chat["messages"]
                total_messages += len(messages)
                
                # 统计模型使用情况
                for msg in messages:
                    if isinstance(msg, dict) and msg.get("model"):
                        model = msg["model"]
                        model_usage[model] = model_usage.get(model, 0) + 1
        
        # 计算平均消息数
        avg_messages_per_session = total_messages / total_sessions if total_sessions > 0 else 0
        
        # 找出最常用的模型
        most_used_model = None
        if model_usage:
            most_used_model = max(model_usage, key=model_usage.get)
        
        return ChatStatsResponse(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_messages=total_messages,
            avg_messages_per_session=round(avg_messages_per_session, 2),
            most_used_model=most_used_model,
            total_tokens_used=0  # 需要从实际使用记录中获取
        )
        
    except Exception as e:
        log.exception(f"Error getting chat stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 搜索接口
############################

@router.get("/search", summary="搜索对话内容")
async def search_chat_content(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, description="返回数量限制"),
    user=Depends(get_verified_user)
):
    """
    搜索用户的对话内容。
    
    Args:
        query (str): 搜索关键词
        limit (int): 返回数量限制
        user: 已认证的用户对象
        
    Returns:
        dict: 搜索结果
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 获取用户的所有对话
        user_chats = Chats.get_chats_by_user_id(user.id)
        
        search_results = []
        
        for chat in user_chats:
            # 搜索标题
            if query.lower() in (chat.title or "").lower():
                search_results.append({
                    "type": "session",
                    "session_id": chat.id,
                    "title": chat.title,
                    "match_type": "title",
                    "snippet": chat.title,
                    "timestamp": chat.updated_at
                })
            
            # 搜索消息内容
            if chat.chat and "messages" in chat.chat:
                for msg in chat.chat["messages"]:
                    if isinstance(msg, dict) and query.lower() in msg.get("content", "").lower():
                        # 生成摘要片段
                        content = msg.get("content", "")
                        start_idx = max(0, content.lower().find(query.lower()) - 50)
                        end_idx = min(len(content), start_idx + 200)
                        snippet = content[start_idx:end_idx]
                        
                        search_results.append({
                            "type": "message",
                            "session_id": chat.id,
                            "message_id": msg.get("id"),
                            "title": chat.title,
                            "match_type": "content",
                            "snippet": snippet,
                            "timestamp": msg.get("timestamp", chat.updated_at)
                        })
        
        # 按时间排序并限制数量
        search_results.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "query": query,
            "total_results": len(search_results),
            "results": search_results[:limit]
        }
        
    except Exception as e:
        log.exception(f"Error searching chat content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )