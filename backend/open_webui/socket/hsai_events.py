"""
HSAI WebSocket事件处理器
"""
import logging
import asyncio
from typing import Dict, Any

log = logging.getLogger(__name__)

def register_hsai_events(sio, emitter):
    """注册HSAI相关的WebSocket事件处理器 - 统一到Socket.IO"""
    if not emitter:
        log.warning("WebSocket emitter not available for HSAI events registration")
        return
    
    # 注册HSAI消息处理事件 - 使用OpenWebUI原生事件名称
    @sio.on("message")
    async def handle_hsai_message(sid, data):
        """处理HSAI消息 - OpenWebUI原生message事件入口"""
        log.info(f"📥 HSAI MESSAGE事件 - SID: {sid}")
        log.debug(f"消息数据: {data}")
        
        try:
            # 检查是否为HSAI消息（通过消息结构判断）
            if not isinstance(data, dict) or not data.get("type") in ["chat", "workflow_trigger"]:
                log.debug("不是HSAI消息，跳过处理")
                # 不是HSAI消息，跳过处理让其他处理器处理
                return
                
            log.info(f"[HSAI统一事件] 接收到客户端sid {sid} 发送的HSAI消息: {data}")
            
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
                log.info(f"[HSAI统一事件] 识别到用户 {user_id} 的消息，使用工作流编排中心处理")
                
                # 直接使用工作流编排中心处理消息
                from open_webui.services.workflow_orchestration_center import workflow_orchestration_center
                
                # 获取或创建会话ID
                session_id = data.get("session_id") or f"session_{user_id}_{int(__import__('time').time())}"
                
                # 构建上下文信息
                context = {
                    "business_name": data.get("business_name", "HSAI"),
                    "entry_type": data.get("entry_type", "chat"),
                    "workflow_type": data.get("workflow_type"),
                    "additional_data": data.get("metadata", {}),
                    "socket_id": sid
                }
                
                log.info(f"[HSAI统一事件] 通过WOC处理请求，上下文: {context}")
                
                # 通过工作流编排中心处理请求
                result = await workflow_orchestration_center.process_request(
                    user_input=data.get("content", ""),
                    user_id=user_id,
                    session_id=session_id,
                    context=context
                )
                
                log.info(f"[HSAI统一事件] WOC处理结果: {result}")
                
                # 构建统一的Socket.IO响应格式
                if result["success"]:
                    response_data = {
                        "type": "hsai_response",
                        "success": True,
                        "execution_id": result["execution_id"],
                        "workflow_type": result["workflow_type"],
                        "workflow_name": result["workflow_name"],
                        "session_id": session_id,
                        "user_id": user_id,
                        "execution_time": result["execution_time"],
                        "timestamp": __import__('time').time()
                    }
                    
                    # 添加响应数据
                    if result.get("response_data"):
                        response_data.update(result["response_data"])
                    
                    log.info(f"[HSAI统一事件] 发送成功响应给sid {sid}")
                    await sio.emit("message", response_data, to=sid)
                else:
                    # 处理失败的响应
                    error_data = {
                        "type": "hsai_error",
                        "content": result.get("error_message", "工作流处理失败"),
                        "execution_id": result.get("execution_id"),
                        "timestamp": __import__('time').time()
                    }
                    log.error(f"[HSAI统一事件] 发送错误响应给sid {sid}: {error_data}")
                    await sio.emit("error", error_data, to=sid)
                    
            else:
                log.warning(f"[HSAI统一事件] 无法识别sid {sid} 的用户身份")
                error_data = {
                    "type": "hsai_authentication_error",
                    "content": "用户身份验证失败",
                    "timestamp": __import__('time').time()
                }
                await sio.emit("error", error_data, to=sid)
                
        except Exception as e:
            log.error(f"[HSAI统一事件] 处理消息时发生错误: {e}", exc_info=True)
            error_data = {
                "type": "hsai_processing_error",
                "content": f"消息处理失败: {str(e)}",
                "timestamp": __import__('time').time()
            }
            await sio.emit("error", error_data, to=sid)
    
    # 注册HSAI状态查询事件
    @sio.on("hsai_status")
    async def handle_hsai_status(sid, data):
        """处理HSAI状态查询"""
        try:
            log.info(f"[HSAI状态查询] 处理sid {sid} 的状态查询")
            
            # 获取用户ID
            user_id = None
            from open_webui.socket.main import SESSION_POOL
            if sid in SESSION_POOL:
                user = SESSION_POOL[sid]
                user_id = user.get("id")
            
            if user_id:
                # 获取系统状态
                from open_webui.utils.n8n_monitor import n8n_monitor
                system_health = n8n_monitor.get_system_health()
                
                status_data = {
                    "type": "hsai_status_response",
                    "user_id": user_id,
                    "system_health": system_health,
                    "timestamp": __import__('time').time()
                }
                
                await sio.emit("workflow_status", status_data, to=sid)
            else:
                error_data = {
                    "type": "hsai_authentication_error",
                    "content": "身份验证失败",
                    "timestamp": __import__('time').time()
                }
                await sio.emit("error", error_data, to=sid)
                
        except Exception as e:
            log.error(f"[HSAI状态查询] 处理状态查询时发生错误: {e}", exc_info=True)
            error_data = {
                "type": "hsai_processing_error",
                "content": f"状态查询失败: {str(e)}",
                "timestamp": __import__('time').time()
            }
            await sio.emit("error", error_data, to=sid)
    
    log.info("HSAI统一WebSocket事件处理器注册成功")

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