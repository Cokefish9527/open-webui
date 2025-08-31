"""
HSAI WebSocket事件处理器
"""
import logging
from typing import Dict, Any
from open_webui.socket.main import get_event_emitter

log = logging.getLogger(__name__)

def register_hsai_events():
    """注册HSAI相关的WebSocket事件处理器"""
    emitter = get_event_emitter()
    if not emitter:
        log.warning("WebSocket emitter not available for HSAI events registration")
        return
    
    @emitter.on("hsai_task_subscribe")
    async def handle_task_subscribe(sid, data):
        """处理任务订阅事件"""
        try:
            task_id = data.get("task_id")
            user_id = data.get("user_id")
            
            if task_id and user_id:
                # 将用户加入任务房间
                await emitter.enter_room(sid, f"task_{task_id}")
                log.info(f"User {user_id} subscribed to task {task_id}")
                
                # 发送订阅确认
                await emitter.emit("hsai_task_subscribed", {
                    "task_id": task_id,
                    "status": "subscribed"
                }, to=sid)
            
        except Exception as e:
            log.error(f"Error handling task subscribe: {e}")
    
    @emitter.on("hsai_task_unsubscribe")
    async def handle_task_unsubscribe(sid, data):
        """处理任务取消订阅事件"""
        try:
            task_id = data.get("task_id")
            user_id = data.get("user_id")
            
            if task_id and user_id:
                # 将用户从任务房间移除
                await emitter.leave_room(sid, f"task_{task_id}")
                log.info(f"User {user_id} unsubscribed from task {task_id}")
                
                # 发送取消订阅确认
                await emitter.emit("hsai_task_unsubscribed", {
                    "task_id": task_id,
                    "status": "unsubscribed"
                }, to=sid)
            
        except Exception as e:
            log.error(f"Error handling task unsubscribe: {e}")
    
    @emitter.on("hsai_dashboard_subscribe")
    async def handle_dashboard_subscribe(sid, data):
        """处理工作台订阅事件"""
        try:
            user_id = data.get("user_id")
            
            if user_id:
                # 将用户加入工作台房间
                await emitter.enter_room(sid, f"dashboard_{user_id}")
                log.info(f"User {user_id} subscribed to dashboard updates")
                
                # 发送订阅确认
                await emitter.emit("hsai_dashboard_subscribed", {
                    "status": "subscribed"
                }, to=sid)
            
        except Exception as e:
            log.error(f"Error handling dashboard subscribe: {e}")
    
    @emitter.on("hsai_chat_join")
    async def handle_chat_join(sid, data):
        """处理加入聊天房间事件"""
        try:
            chat_id = data.get("chat_id")
            user_id = data.get("user_id")
            
            if chat_id and user_id:
                # 将用户加入聊天房间
                await emitter.enter_room(sid, f"chat_{chat_id}")
                log.info(f"User {user_id} joined chat {chat_id}")
                
                # 通知其他用户
                await emitter.emit("hsai_user_joined", {
                    "user_id": user_id,
                    "chat_id": chat_id
                }, room=f"chat_{chat_id}", skip_sid=sid)
            
        except Exception as e:
            log.error(f"Error handling chat join: {e}")
    
    @emitter.on("hsai_chat_leave")
    async def handle_chat_leave(sid, data):
        """处理离开聊天房间事件"""
        try:
            chat_id = data.get("chat_id")
            user_id = data.get("user_id")
            
            if chat_id and user_id:
                # 将用户从聊天房间移除
                await emitter.leave_room(sid, f"chat_{chat_id}")
                log.info(f"User {user_id} left chat {chat_id}")
                
                # 通知其他用户
                await emitter.emit("hsai_user_left", {
                    "user_id": user_id,
                    "chat_id": chat_id
                }, room=f"chat_{chat_id}")
            
        except Exception as e:
            log.error(f"Error handling chat leave: {e}")
    
    @emitter.on("hsai_workflow_subscribe")
    async def handle_workflow_subscribe(sid, data):
        """处理工作流订阅事件"""
        try:
            workflow_id = data.get("workflow_id")
            execution_id = data.get("execution_id")
            user_id = data.get("user_id")
            
            if workflow_id and user_id:
                # 将用户加入工作流房间
                room_name = f"workflow_{workflow_id}"
                if execution_id:
                    room_name = f"workflow_{workflow_id}_{execution_id}"
                
                await emitter.enter_room(sid, room_name)
                log.info(f"User {user_id} subscribed to workflow {workflow_id}")
                
                # 发送订阅确认
                await emitter.emit("hsai_workflow_subscribed", {
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "status": "subscribed"
                }, to=sid)
            
        except Exception as e:
            log.error(f"Error handling workflow subscribe: {e}")
    
    @emitter.on("disconnect")
    async def handle_disconnect(sid):
        """处理用户断开连接"""
        try:
            log.info(f"User disconnected: {sid}")
            # 清理用户的所有房间订阅
            # 这里可以添加更多的清理逻辑
            
        except Exception as e:
            log.error(f"Error handling disconnect: {e}")
    
    log.info("HSAI WebSocket events registered successfully")

# WebSocket事件类型定义
HSAI_WEBSOCKET_EVENTS = {
    # 任务相关事件
    "TASK_STARTED": "hsai_task_started",
    "TASK_PROGRESS": "hsai_task_progress", 
    "TASK_COMPLETED": "hsai_task_completed",
    "TASK_FAILED": "hsai_task_failed",
    "TASK_CANCELLED": "hsai_task_cancelled",
    
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