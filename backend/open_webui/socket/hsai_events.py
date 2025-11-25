import logging
import asyncio
import json
import random
from typing import Dict, Any

# 导入用户模型
from open_webui.models.users import Users
# 导入文件模型
from open_webui.models.files import Files
# 导入附件描述对象
from open_webui.models.attachments import AttachmentDescriptor

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
                    "timestamp": int(__import__('time').time() * 1000),
                    "messageType": "assistant",
                    "user_id": user_id,
                    "status": "FINISHED"
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
                
                # 构建上下文信息，包含socket_id用于后续消息发送
                context = {
                    "entry_type": data.get("entry_type", "chat"),
                    "business_name": "HSAI",  # 默认值为"HSAI"
                    "additional_data": data.get("metadata", {}),
                    "socket_id": sid  # 传递socket_id用于后续消息发送
                }
                
                # 解析附件信息
                attachment = None
                files_data = data.get("files") or data.get("attachments")
                if files_data and isinstance(files_data, list) and len(files_data) > 0:
                    # 仅保留首个条目
                    file_info = files_data[0]
                    if isinstance(file_info, dict) and "id" in file_info:
                        file_id = file_info["id"]
                        # 校验文件是否存在且属于当前用户
                        file_model = Files.get_file_by_id(file_id)
                        if file_model and file_model.user_id == user_id:
                            # 创建附件描述对象
                            attachment = AttachmentDescriptor(
                                file_id=file_model.id,
                                filename=file_model.filename,
                                mime_type=file_model.meta.get("content_type") if file_model.meta else None,
                                local_path=file_model.path or "",
                                size=file_model.meta.get("size", 0) if file_model.meta else 0
                            )
                            # 写入context["attachment"]
                            context["attachment"] = attachment
                            log.info(f"[HSAI统一事件] 成功解析附件: {attachment.filename}")
                            log.info(f"[HSAI统一事件] 附件详情: file_id={attachment.file_id}, mime_type={attachment.mime_type}, size={attachment.size}")
                        else:
                            log.warning(f"[HSAI统一事件] 附件校验失败: file_id={file_id}, user_id={user_id}")
                            # 返回错误给客户端
                            error_data = {
                                "type": "attachment_validation_failed",
                                "success": False,
                                "content": "附件校验失败，请确保文件存在且属于当前用户",
                                "timestamp": int(__import__('time').time() * 1000),
                                "messageType": "error",
                                "displayText": "附件校验失败，请确保文件存在且属于当前用户"
                            }
                            await sio.emit("hsai_error", error_data, to=sid)
                            return
                    else:
                        log.warning(f"[HSAI统一事件] 附件信息格式不正确: {file_info}")
                elif files_data and isinstance(files_data, list) and len(files_data) > 1:
                    log.warning(f"[HSAI统一事件] 超过一个附件，仅处理第一个附件")
                    # 返回错误给客户端
                    error_data = {
                        "type": "attachment_validation_failed",
                        "success": False,
                        "content": "单条消息仅支持一个附件",
                        "timestamp": int(__import__('time').time() * 1000),
                        "messageType": "error",
                        "displayText": "单条消息仅支持一个附件"
                    }
                    await sio.emit("hsai_error", error_data, to=sid)
                    return
                
                # 尝试从用户信息中获取business_name
                if user_id:
                    user = Users.get_user_by_id(user_id)
                    if user and hasattr(user, 'business_name') and user.business_name:
                        context["business_name"] = user.business_name
                        log.info(f"[HSAI统一事件] 使用用户设置的business_name: {user.business_name}")
                    elif user and hasattr(user, 'info') and user.info and isinstance(user.info, dict):
                        # 如果用户模型中没有business_name，则从info字段中获取
                        info_business_name = user.info.get('business_name')
                        if info_business_name:
                            context["business_name"] = info_business_name
                            log.info(f"[HSAI统一事件] 使用用户info中的business_name: {info_business_name}")
                
                # 检查用户信息收集状态，决定使用哪个工作流
                is_info_collected = Users.is_user_info_collection_completed(user_id)
                log.info(f"[HSAI统一事件] 用户 {user_id} 信息收集状态: {'已完成' if is_info_collected else '未完成'}")
                
                # 根据信息收集状态设置入口类型
                if not is_info_collected:
                    # 如果信息未收集完成，强制使用公司信息收集工作流
                    context["entry_type"] = "company_info"
                    log.info(f"[HSAI统一事件] 用户信息未收集完成，强制使用公司信息收集工作流")
                else:
                    # 如果信息已收集完成，使用主对话工作流
                    context["entry_type"] = "chat"
                    log.info(f"[HSAI统一事件] 用户信息已收集完成，使用主对话工作流")
                
                # 直接使用工作流编排中心处理消息
                from open_webui.services.workflow_orchestration_center import workflow_orchestration_center
                
                # 直接使用前端传递的会话ID，而不是重新生成
                session_id = data.get("session_id")
                if not session_id:
                    # 如果前端没有传递session_id，则生成一个
                    import uuid
                    session_id = f"session_{user_id}_{uuid.uuid4().hex[:8]}"
                    log.info(f"[HSAI统一事件] 前端未传递session_id，生成新的session_id: {session_id}")
                else:
                    log.info(f"[HSAI统一事件] 使用前端传递的session_id: {session_id}")
                
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
                    "timestamp": int(__import__('time').time() * 1000),
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
                "timestamp": int(__import__('time').time() * 1000),
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
                    "timestamp": int(__import__('time').time() * 1000),
                    "messageType": "assistant",
                    "displayText": "系统状态查询完成"
                }
                
                await sio.emit("hsai_response", status_data, to=sid)
            else:
                error_data = {
                    "type": "authentication_error",
                    "success": False,
                    "content": "身份验证失败",
                    "timestamp": int(__import__('time').time() * 1000),
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
                "timestamp": int(__import__('time').time() * 1000),
                "messageType": "error",
                "displayText": f"状态查询失败: {str(e)}"
            }
            await sio.emit("hsai_error", error_data, to=sid)
    
    # 注册ping_msg事件处理器
    @sio.on("ping_msg")
    async def handle_ping_msg(sid, data):
        """处理ping_msg事件并返回pong_rsp响应"""
        log.info(f"[HSAI ping_msg事件] 接收到客户端sid {sid} 发送的ping_msg消息")
        
        # 定义随机回复消息列表
        random_responses = [
            "pong! 系统运行正常。",
            "pong! 连接稳定。",
            "pong! 服务在线。",
            "pong! 响应迅速。",
            "pong! 一切就绪。",
            "pong! 系统健康。",
            "pong! 连接成功。",
            "pong! 服务可用。",
            "pong! 状态良好。",
            "pong! 系统响应中。"
        ]
        
        # 获取用户ID
        user_id = None
        from open_webui.socket.main import SESSION_POOL
        if sid in SESSION_POOL:
            user = SESSION_POOL[sid]
            user_id = user.get("id")
        
        # 选择随机回复
        response_text = random.choice(random_responses)
        
        # 构建pong_rsp响应消息
        pong_response = {
            "type": "pong_rsp",
            "success": True,
            "content": response_text,
            "displayText": response_text,
            "timestamp": int(__import__('time').time() * 1000),
            "messageType": "assistant",
            "user_id": user_id
        }
        
        # 发送pong_rsp响应
        await sio.emit("pong_rsp", pong_response, to=sid)
        log.info(f"[HSAI ping_msg事件] 已发送pong_rsp响应: {response_text}")
    
    log.info("HSAI统一WebSocket事件处理器注册成功")

# WebSocket事件类型定义
HSAI_WEBSOCKET_EVENTS = {
    # 核心事件（已实现）
    "RESPONSE": "hsai_response",      # 成功响应事件
    "ERROR": "hsai_error",            # 错误响应事件
    "BLUEPRINT_TASK_UPDATE": "hsai_task_blueprint_update",
    
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
