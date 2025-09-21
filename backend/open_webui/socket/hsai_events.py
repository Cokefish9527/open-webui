import logging
import asyncio
import json
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
            if not isinstance(data, dict) or not data.get("type") in ["chat", "workflow_trigger", "welcome"]:
                log.debug("不是HSAI消息，跳过处理")
                # 不是HSAI消息，跳过处理让其他处理器处理
                return
                
            # 处理welcome消息类型
            if data.get("type") == "welcome":
                log.info(f"[HSAI统一事件] 接收到客户端sid {sid} 发送的welcome消息")
                
                # 获取用户ID
                user_id = None
                from open_webui.socket.main import SESSION_POOL
                if sid in SESSION_POOL:
                    user = SESSION_POOL[sid]
                    user_id = user.get("id")
                
                # 如果没有用户ID，尝试从数据中获取
                if not user_id and isinstance(data, dict):
                    user_id = data.get("user_id")
                
                # 发送欢迎语
                welcome_message = {
                    "type": "welcome_response",
                    "success": True,
                    "content": "欢迎使用华商AI系统！我们致力于为您提供最优质的服务体验。",
                    "displayText": "欢迎使用华商AI系统！我们致力于为您提供最优质的服务体验。有任何问题都可以随时向我提问。",
                    "timestamp": int(__import__('time').time()),
                    "messageType": "assistant",
                    "user_id": user_id
                }
                
                await sio.emit("hsai_response", welcome_message, to=sid)
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
                session_id = f"session_{user_id}_{int(__import__('time').time())}"
                
                # 构建上下文信息
                context = {
                    "entry_type": data.get("entry_type", "chat"),
                    "additional_data": data.get("metadata", {}),
                    "socket_id": sid
                }
                
                # 移除重复的工作流类型选择逻辑，让WOC内部处理
                # 原来的代码：
                # from open_webui.config.n8n_workflows import get_workflow_by_entry_type
                # workflow_type = get_workflow_by_entry_type(context["entry_type"])
                # log.info(f"[HSAI统一事件] 通过WOC处理请求，上下文: {context}, 工作流类型: {workflow_type}")
                
                log.info(f"[HSAI统一事件] 通过WOC处理请求，上下文: {context}")
                
                # 通过工作流编排中心处理请求
                # 注意：工作流编排中心内部会通过_notify_socket_event发送相应的事件
                # 这里只需要调用处理方法，不需要再发送重复的事件
                await workflow_orchestration_center.process_request(
                    user_input=data.get("content", ""),
                    user_id=user_id,
                    session_id=session_id,
                    context=context
                )
                    
            else:
                log.warning(f"[HSAI统一事件] 无法识别sid {sid} 的用户身份")
                error_data = {
                    "type": "authentication_error",
                    "success": False,
                    "content": "用户身份验证失败",
                    "timestamp": int(__import__('time').time()),
                    "messageType": "error",
                    "displayText": "用户身份验证失败"
                }
                await sio.emit("hsai_error", error_data, to=sid)
                
        except Exception as e:
            log.error(f"[HSAI统一事件] 处理消息时发生错误: {e}", exc_info=True)
            error_data = {
                "type": "processing_error",
                "success": False,
                "content": f"消息处理失败: {str(e)}",
                "timestamp": int(__import__('time').time()),
                "messageType": "error",
                "displayText": f"消息处理失败: {str(e)}"
            }
            await sio.emit("hsai_error", error_data, to=sid)
    
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
                
                # 构建标准的HSAI响应消息体结构
                status_data = {
                    "type": "status_response",
                    "success": True,
                    "user_id": user_id,
                    "system_health": system_health,
                    "timestamp": int(__import__('time').time()),
                    "messageType": "assistant",
                    "displayText": "系统状态查询完成"
                }
                
                await sio.emit("hsai_response", status_data, to=sid)
            else:
                error_data = {
                    "type": "authentication_error",
                    "success": False,
                    "content": "身份验证失败",
                    "timestamp": int(__import__('time').time()),
                    "messageType": "error",
                    "displayText": "身份验证失败"
                }
                await sio.emit("hsai_error", error_data, to=sid)
                
        except Exception as e:
            log.error(f"[HSAI状态查询] 处理状态查询时发生错误: {e}", exc_info=True)
            error_data = {
                "type": "processing_error",
                "success": False,
                "content": f"状态查询失败: {str(e)}",
                "timestamp": int(__import__('time').time()),
                "messageType": "error",
                "displayText": f"状态查询失败: {str(e)}"
            }
            await sio.emit("hsai_error", error_data, to=sid)
    
    log.info("HSAI统一WebSocket事件处理器注册成功")

# WebSocket事件类型定义
HSAI_WEBSOCKET_EVENTS = {
    # 核心事件（已实现）
    "RESPONSE": "hsai_response",      # 成功响应事件
    "ERROR": "hsai_error",            # 错误响应事件
    
    # 工作流相关事件（已合并到核心事件中）
    # "WORKFLOW_STARTED": "hsai_workflow_started",     # 已合并到hsai_response，通过subtype区分
    # "WORKFLOW_PROGRESS": "hsai_workflow_progress",   # 已合并到hsai_response，通过subtype区分
    # "WORKFLOW_COMPLETED": "hsai_workflow_completed", # 已合并到hsai_response，通过subtype区分
    # "WORKFLOW_FAILED": "hsai_workflow_failed",       # 已合并到hsai_error，通过subtype区分
    
    # 状态和系统事件（已合并到核心事件中）
    # "WORKFLOW_STATUS": "workflow_status",  # 已合并到hsai_response，通过subtype区分
    # "GENERIC_ERROR": "error",              # 已合并到hsai_error，通过subtype区分
    
    # 预留事件（暂未实现）
    # "CHAT_MESSAGE": "hsai_chat_message",        # 预留事件名，暂未实现
    # "CHAT_TYPING": "hsai_chat_typing",          # 预留事件名，暂未实现
    # "USER_JOINED": "hsai_user_joined",          # 预留事件名，暂未实现
    # "USER_LEFT": "hsai_user_left",              # 预留事件名，暂未实现
    # "DASHBOARD_UPDATE": "hsai_dashboard_update",# 预留事件名，暂未实现
    # "KPI_UPDATE": "hsai_kpi_update",            # 预留事件名，暂未实现
    # "ACTIVITY_UPDATE": "hsai_activity_update",  # 预留事件名，暂未实现
    # "SYSTEM_ALERT": "hsai_system_alert",        # 预留事件名，暂未实现
    # "SYSTEM_MAINTENANCE": "hsai_system_maintenance",# 预留事件名，暂未实现
    # "SYSTEM_STATUS": "hsai_system_status"       # 预留事件名，暂未实现
}