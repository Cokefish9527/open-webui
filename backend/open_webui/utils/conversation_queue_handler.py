"""
对话消息队列处理器
处理来自n8n工作流的对话消息，通过Socket.IO通知客户端
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from open_webui.env import SRC_LOG_LEVELS
# 延迟导入，在函数内部导入Socket.IO相关模块
# from open_webui.socket.main import sio, SESSION_POOL, USER_POOL
# 延迟导入，在函数内部导入Redis客户端
# from open_webui.utils.redis_queue_listener import get_redis_client

# 配置日志
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("CONFIG", logging.INFO))


def get_redis_client():
    """获取Redis客户端实例"""
    # 延迟导入Redis模块
    import redis
    # 使用默认的Redis连接信息
    redis_url = "redis://localhost:6379/0"
    return redis.from_url(redis_url)


async def handle_conversation_agent_message(message: Dict[str, Any], db_session: Session) -> None:
    """
    处理对话代理消息队列中的消息
    根据消息的status字段判断是流式传输还是完整消息
    
    Args:
        message: 从Redis队列中获取的消息数据
        db_session: 数据库会话
    """
    try:
        # 延迟导入Socket.IO相关模块
        from open_webui.socket.main import SESSION_POOL
        
        log.info(f"处理对话代理消息: session_id={message.get('session_id')}, status={message.get('status')}")
        log.debug(f"完整消息内容: {message}")
        
        # 获取消息关键字段
        session_id = message.get("session_id")
        status = message.get("status", "FINISHED")
        reply_id = message.get("reply_id")
        operate_id = message.get("operate_id")
        
        if not session_id:
            log.warning("消息缺少session_id字段，无法关联到客户端会话")
            return
            
        # 根据status字段判断消息类型
        if status == "RUNNING":
            # 流式传输消息
            await _handle_streaming_message(message, session_id, reply_id, operate_id)
        elif status == "FINISHED":
            # 完整消息
            await _handle_complete_message(message, session_id, reply_id, operate_id)
        else:
            log.warning(f"未知的消息状态: {status}")
            # 默认按完整消息处理
            await _handle_complete_message(message, session_id, reply_id, operate_id)
            
    except Exception as e:
        log.error(f"处理对话代理消息时发生错误: {e}", exc_info=True)
        raise

async def _handle_streaming_message(message: Dict[str, Any], session_id: str, reply_id: Optional[str], operate_id: Optional[str]) -> None:
    """
    处理流式传输消息
    通过agent_message_chunk事件逐块发送消息内容
    """
    try:
        # 延迟导入Socket.IO相关模块
        from open_webui.socket.main import sio, SESSION_POOL
        
        content = message.get("content", {})
        text_content = content.get("text", "")
        
        log.info(f"处理流式消息: session_id={session_id}, text_length={len(text_content)}")
        
        # 查找对应的Socket.IO连接
        target_sid = _find_socket_by_session_id(session_id, SESSION_POOL)
        if not target_sid:
            log.warning(f"未找到session_id {session_id} 对应的Socket.IO连接")
            return
            
        # 如果有文本内容，分块发送
        if text_content:
            # 按适当大小分块（例如每块100个字符）
            chunk_size = 100
            for i in range(0, len(text_content), chunk_size):
                chunk_text = text_content[i:i + chunk_size]
                is_final = (i + chunk_size >= len(text_content))
                
                chunk_message = {
                    "session_id": session_id,
                    "reply_id": reply_id,
                    "reply_seq": message.get("reply_seq", 1),
                    "chunk_text": chunk_text,
                    "is_final": is_final,
                    "create_ts": message.get("create_ts")
                }
                
                # 发送消息块
                await sio.emit("agent_message_chunk", chunk_message, to=target_sid)
                log.debug(f"发送消息块: session_id={session_id}, chunk_length={len(chunk_text)}")
                
                # 短暂休眠以确保客户端能及时处理
                await asyncio.sleep(0.05)
                
        # 发送状态更新
        status_message = {
            "session_id": session_id,
            "reply_id": reply_id,
            "status": "RUNNING",
            "message": "消息传输中...",
            "create_ts": message.get("create_ts")
        }
        await sio.emit("agent_message_status", status_message, to=target_sid)
        log.info(f"流式消息处理完成: session_id={session_id}")
        
    except Exception as e:
        log.error(f"处理流式消息时发生错误: {e}", exc_info=True)
        raise

async def _handle_complete_message(message: Dict[str, Any], session_id: str, reply_id: Optional[str], operate_id: Optional[str]) -> None:
    """
    处理完整消息
    通过agent_message事件发送完整消息内容
    """
    try:
        # 延迟导入Socket.IO相关模块
        from open_webui.socket.main import sio, SESSION_POOL
        
        log.info(f"处理完整消息: session_id={session_id}")
        
        # 查找对应的Socket.IO连接
        target_sid = _find_socket_by_session_id(session_id, SESSION_POOL)
        if not target_sid:
            log.warning(f"未找到session_id {session_id} 对应的Socket.IO连接")
            return
            
        # 发送完整消息
        await sio.emit("agent_message", message, to=target_sid)
        log.info(f"完整消息发送完成: session_id={session_id}, reply_id={reply_id}")
        
        # 发送状态更新
        status_message = {
            "session_id": session_id,
            "reply_id": reply_id,
            "status": "FINISHED",
            "message": "消息传输完成",
            "create_ts": message.get("create_ts")
        }
        await sio.emit("agent_message_status", status_message, to=target_sid)
        log.info(f"完整消息状态更新发送完成: session_id={session_id}")
        
    except Exception as e:
        log.error(f"处理完整消息时发生错误: {e}", exc_info=True)
        raise

def _find_socket_by_session_id(session_id: str, SESSION_POOL) -> Optional[str]:
    """
    根据session_id查找对应的Socket.IO连接ID
    通过遍历SESSION_POOL查找匹配的session_id
    """
    try:
        # 遍历SESSION_POOL查找匹配的session_id
        for sid, session_data in SESSION_POOL.items():
            # 检查session_data中是否包含session_id字段
            if isinstance(session_data, dict) and session_data.get("session_id") == session_id:
                return sid
                
        # 如果在SESSION_POOL中没找到，尝试通过用户关联查找
        # 这种情况适用于session_id是用户会话ID的情况
        for sid, session_data in SESSION_POOL.items():
            if isinstance(session_data, dict) and session_data.get("id"):
                user_id = session_data.get("id")
                # 检查用户是否有关联的session_id
                # 这里假设session_id格式为"session_{user_id}_{timestamp}"
                if session_id.startswith(f"session_{user_id}_"):
                    return sid
                    
        log.debug(f"未找到session_id {session_id} 对应的Socket.IO连接")
        return None
        
    except Exception as e:
        log.error(f"查找Socket.IO连接时发生错误: {e}", exc_info=True)
        return None

def register_conversation_queue_handler(redis_queue_listener) -> None:
    """
    注册对话消息队列处理器
    
    Args:
        redis_queue_listener: Redis队列监听器实例
    """
    # 注册对话代理消息队列处理器
    redis_queue_listener.register_handler(
        "ai-conversation-agent-message-queue", 
        handle_conversation_agent_message,
        {
            "timeout": 30,
            "max_retry": 3,
            "dead_letter_queue": "conversation_agent_dead_letter"
        }
    )
    
    log.info("已注册对话消息队列处理器")