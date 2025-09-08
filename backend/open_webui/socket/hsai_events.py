"""
HSAI WebSocket事件处理器
"""
import logging
import asyncio
from typing import Dict, Any

log = logging.getLogger(__name__)

def register_hsai_events(sio, emitter):
    """注册HSAI相关的WebSocket事件处理器"""
    if not emitter:
        log.warning("WebSocket emitter not available for HSAI events registration")
        return
    
    # 注意：emitter 是一个函数，不是具有 .on() 方法的对象
    # 所以我们不能为 emitter 注册事件处理器
    # 我们只注册 sio 事件处理器
    
    # 添加处理客户端发送消息的事件处理器
    @sio.on("send_message")
    async def handle_send_message(sid, data):
        """处理客户端发送的消息"""
        try:
            log.info(f"[HSAI事件处理器] 接收到客户端sid {sid} 发送的消息: {data}")
            
            # 获取用户ID
            user_id = None
            from open_webui.socket.main import SESSION_POOL
            if sid in SESSION_POOL:
                user = SESSION_POOL[sid]
                user_id = user.get("id")
            
            # 如果没有用户ID，尝试从数据中获取
            if not user_id and isinstance(data, dict):
                user_id = data.get("user_id")
            
            if user_id:
                log.info(f"[HSAI事件处理器] 识别到用户 {user_id} 的消息，准备转发给HSAI聊天处理器")
                
                # 将消息转发给HSAI聊天处理器进行n8n工作流处理
                from open_webui.socket.hsai_chat_handler import chat_handler
                
                # 构造符合ChatMessage格式的消息
                message_data = {
                    "type": "chat",
                    "content": data.get("content", ""),
                    "user_id": user_id,
                    "session_id": data.get("session_id"),
                    "workflow_type": data.get("workflow_type"),
                    "entry_type": data.get("entry_type"),
                    "metadata": data.get("metadata", {})
                }
                
                log.info(f"[HSAI事件处理器] 构造的消息数据: {message_data}")
                
                # 异步处理消息
                log.info(f"[HSAI事件处理器] 启动异步任务处理用户 {user_id} 的消息")
                asyncio.create_task(chat_handler.handle_message(user_id, message_data))
                
                # 不再发送确认消息给客户端，让工作流处理完成后直接返回结果
            else:
                log.warning(f"[HSAI事件处理器] 无法识别sid {sid} 的用户身份")
                error_data = {
                    "type": "authentication_error",
                    "content": "用户身份验证失败",
                    "timestamp": __import__('time').time()
                }
                log.warning(f"[HSAI事件处理器] 发送身份验证错误消息给客户端sid {sid}: {error_data}")
                await sio.emit("error", error_data, to=sid)
                
        except Exception as e:
            log.error(f"[HSAI事件处理器] 处理消息时发生错误: {e}", exc_info=True)
            error_data = {
                "type": "processing_error",
                "content": f"消息处理失败: {str(e)}",
                "timestamp": __import__('time').time()
            }
            log.error(f"[HSAI事件处理器] 发送处理错误消息给客户端sid {sid}: {error_data}")
            await sio.emit("error", error_data, to=sid)
    
    log.info("HSAI WebSocket事件处理器注册成功")

# WebSocket事件类型定义
HSAI_WEBSOCKET_EVENTS = {
    # 工作流相关事件
    "WORKFLOW_STARTED": "hsai_workflow_started",
    "WORKFLOW_PROGRESS": "hsai_workflow_progress",
    "WORKFLOW_COMPLETED": "hsai_workflow_completed",
    "WORKFLOW_FAILED": "hsai_workflow_failed",
    
    # 聊天相关事件
    "CHAT_MESSAGE": "hsai_chat_message",
    "CHAT_TYPING": "hsai_chat_typing",
    "USER_JOINED": "hsai_user_joined",
    "USER_LEFT": "hsai_user_left",
    
    # 工作台相关事件
    "DASHBOARD_UPDATE": "hsai_dashboard_update",
    "KPI_UPDATE": "hsai_kpi_update",
    "ACTIVITY_UPDATE": "hsai_activity_update",
    
    # 系统相关事件
    "SYSTEM_ALERT": "hsai_system_alert",
    "SYSTEM_MAINTENANCE": "hsai_system_maintenance",
    "SYSTEM_STATUS": "hsai_system_status"
}