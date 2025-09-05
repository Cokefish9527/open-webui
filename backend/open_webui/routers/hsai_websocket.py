from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from open_webui.socket.hsai_chat_handler import chat_handler
from open_webui.utils.viral_learning_scheduler import viral_learning_scheduler
from open_webui.utils.auth import get_current_user as get_verified_user
from open_webui.models.users import Users

# 导入新的工作流集成模块
from open_webui.utils.n8n_workflow_manager import workflow_manager
from open_webui.utils.workflow_selector import workflow_selector, SelectionContext
from open_webui.utils.n8n_client import n8n_client, ExecutionRequest
from open_webui.utils.message_processor import message_processor

# 修改导入语句
from open_webui.env import WEBUI_SECRET_KEY as JWT_SECRET_KEY

import json
import logging
import jwt
import time
import asyncio
from typing import Dict, List, Optional

log = logging.getLogger(__name__)
router = APIRouter()

@router.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    log.info("HSAI WebSocket router starting up...")
    
    # 初始化工作流管理器
    await workflow_manager.initialize()
    log.info("Workflow manager initialized")
    
    # 初始化N8N客户端
    await n8n_client.initialize()
    log.info("N8N client initialized")
    
    # 启动爆款学习工作流定时调度器
    await viral_learning_scheduler.start()
    log.info("Viral learning scheduler started")

@router.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    log.info("HSAI WebSocket router shutting down...")
    
    # 关闭N8N客户端
    await n8n_client.close()
    log.info("N8N client closed")
    
    # 停止爆款学习工作流定时调度器
    await viral_learning_scheduler.stop()
    log.info("Viral learning scheduler stopped")

async def get_user_from_token(token: str):
    """从token获取用户信息"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("id")
        if user_id:
            user = Users.get_user_by_id(user_id)
            return user
    except Exception as e:
        log.error(f"Token validation failed: {e}")
    return None

# 连接管理器
class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        
    async def connect(self, websocket: WebSocket, user_id: str, session_id: str = None):
        """建立连接"""
        await websocket.accept()
        connection_key = f"{user_id}_{session_id}" if session_id else user_id
        self.active_connections[connection_key] = websocket
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        if session_id and session_id not in self.user_sessions[user_id]:
            self.user_sessions[user_id].append(session_id)
            
        log.info(f"WebSocket connected: {connection_key}")
        
    def disconnect(self, user_id: str, session_id: str = None):
        """断开连接"""
        connection_key = f"{user_id}_{session_id}" if session_id else user_id
        if connection_key in self.active_connections:
            del self.active_connections[connection_key]
            
        if session_id and user_id in self.user_sessions:
            if session_id in self.user_sessions[user_id]:
                self.user_sessions[user_id].remove(session_id)
                
        log.info(f"WebSocket disconnected: {connection_key}")
        
    async def send_personal_message(self, message: dict, user_id: str, session_id: str = None):
        """发送个人消息"""
        connection_key = f"{user_id}_{session_id}" if session_id else user_id
        websocket = self.active_connections.get(connection_key)
        
        if websocket:
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
                return True
            except Exception as e:
                log.error(f"Error sending message to {connection_key}: {e}")
                self.disconnect(user_id, session_id)
                return False
        return False
        
    async def broadcast_to_user(self, message: dict, user_id: str):
        """向用户的所有会话广播消息"""
        sent_count = 0
        if user_id in self.user_sessions:
            for session_id in self.user_sessions[user_id]:
                if await self.send_personal_message(message, user_id, session_id):
                    sent_count += 1
        return sent_count

# 全局连接管理器
connection_manager = ConnectionManager()

@router.websocket("/hsai/ws/{user_id}")
async def hsai_websocket_endpoint(
    websocket: WebSocket, 
    user_id: str,
    token: str = Query(...),
    session_id: str = Query(None)
):
    """
    HSAI WebSocket端点 - OpenWebUI与n8n协同核心
    
    实现客户端 ←→ WebSocket ←→ OpenWebUI ←→ n8n webhook 的完整协同流程
    
    Args:
        websocket: WebSocket连接对象
        user_id: 用户ID
        token: 认证token (通过query参数传递)
    
    协同流程:
        1. 客户端通过WebSocket连接到OpenWebUI
        2. 客户端发送对话消息
        3. OpenWebUI转发消息到n8n webhook
        4. n8n处理后返回结构化响应
        5. OpenWebUI处理响应并通过WebSocket返回客户端
    """
    
    # 验证用户身份
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return
    
    try:
        # 验证token并获取用户信息
        user = await get_user_from_token(token)
        if not user or user.id != user_id:
            await websocket.close(code=4003, reason="Invalid authentication")
            return
            
        log.info(f"User {user.name} ({user_id}) attempting WebSocket connection")
        
    except Exception as e:
        log.error(f"Authentication failed for user {user_id}: {e}")
        await websocket.close(code=4003, reason="Authentication failed")
        return
    
    # 建立WebSocket连接
    await chat_handler.connect(websocket, user_id)
    
    try:
        while True:
            # 接收客户端消息
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                log.debug(f"Received message from user {user_id}: {message_data.get('type', 'unknown')}")
                
                # 处理消息（包含完整的n8n协同逻辑）
                await chat_handler.handle_message(user_id, message_data)
                
            except json.JSONDecodeError as e:
                log.error(f"Invalid JSON from user {user_id}: {e}")
                await chat_handler._send_error(user_id, "Invalid JSON format")
                
            except Exception as e:
                log.error(f"Error processing message from user {user_id}: {e}")
                await chat_handler._send_error(user_id, f"Message processing failed: {str(e)}")
                
    except WebSocketDisconnect:
        log.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        log.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await chat_handler.disconnect(user_id)

@router.get("/hsai/ws/status")
async def websocket_status():
    """获取WebSocket服务状态"""
    from open_webui.utils.n8n_monitor import n8n_monitor
    
    active_users = chat_handler.get_active_users()
    system_health = n8n_monitor.get_system_health()
    
    return {
        "status": "running",
        "active_connections": len(active_users),
        "active_users": active_users,
        "total_sessions": len(chat_handler.user_sessions),
        "n8n_health": system_health
    }

@router.get("/hsai/ws/sessions/{session_id}/users")
async def get_session_users(session_id: str):
    """获取指定会话的活跃用户"""
    users = chat_handler.get_session_users(session_id)
    return {
        "session_id": session_id,
        "active_users": users,
        "user_count": len(users)
    }

@router.post("/hsai/ws/broadcast/{session_id}")
async def broadcast_to_session(
    session_id: str,
    message: dict,
    user=Depends(get_verified_user)
):
    """向指定会话广播消息"""
    try:
        # 添加发送者信息
        broadcast_message = {
            **message,
            "sender_id": user.id,
            "sender_name": user.name,
            "timestamp": time.time()
        }
        
        await chat_handler.broadcast_to_session(session_id, broadcast_message)
        
        return {
            "status": "success",
            "session_id": session_id,
            "message_sent": True
        }
        
    except Exception as e:
        log.error(f"Broadcast failed for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Broadcast failed: {str(e)}"
        )

@router.get("/hsai/ws/health")
async def get_n8n_health():
    """获取n8n工作流健康状态"""
    from open_webui.utils.n8n_monitor import n8n_monitor
    
    return n8n_monitor.get_system_health()

@router.get("/hsai/ws/health/{workflow_type}")
async def get_workflow_health(workflow_type: str):
    """获取特定工作流健康状态"""
    from open_webui.utils.n8n_monitor import n8n_monitor
    from open_webui.config.n8n_workflows import N8NWorkflowType
    
    try:
        wf_type = N8NWorkflowType(workflow_type)
        return n8n_monitor.get_workflow_health(wf_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workflow type: {workflow_type}"
        )

@router.post("/hsai/ws/cleanup")
async def cleanup_monitoring_data(
    max_age_hours: int = 24,
    user=Depends(get_verified_user)
):
    """清理监控数据（需要管理员权限）"""
    from open_webui.utils.n8n_monitor import n8n_monitor
    
    # 这里可以添加管理员权限检查
    # if not user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    n8n_monitor.cleanup_old_data(max_age_hours)
    
    return {
        "status": "success",
        "message": f"Cleaned up monitoring data older than {max_age_hours} hours"
    }