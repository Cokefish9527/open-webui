"""
HSAI WebSocket通知机制测试和验证工具
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from open_webui.socket.main import get_event_emitter

log = logging.getLogger(__name__)

class HSAIWebSocketNotifier:
    """HSAI WebSocket通知管理器"""
    
    def __init__(self):
        self.emitter = get_event_emitter()
    
    async def notify_task_started(self, task_id: str, task_type: str, user_id: str, data: Optional[Dict[str, Any]] = None):
        """通知任务开始"""
        if not self.emitter:
            log.warning("WebSocket emitter not available")
            return False
        
        try:
            payload = {
                "task_id": task_id,
                "task_type": task_type,
                "user_id": user_id,
                "timestamp": asyncio.get_event_loop().time(),
                "data": data or {}
            }
            
            await self.emitter.emit(
                "hsai_task_started",
                payload,
                to=user_id
            )
            
            log.info(f"Task started notification sent: {task_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to send task started notification: {e}")
            return False
    
    async def notify_task_progress(self, task_id: str, progress: int, user_id: str, message: Optional[str] = None):
        """通知任务进度更新"""
        if not self.emitter:
            log.warning("WebSocket emitter not available")
            return False
        
        try:
            payload = {
                "task_id": task_id,
                "progress": progress,
                "user_id": user_id,
                "message": message,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await self.emitter.emit(
                "hsai_task_progress",
                payload,
                to=user_id
            )
            
            log.info(f"Task progress notification sent: {task_id} - {progress}%")
            return True
            
        except Exception as e:
            log.error(f"Failed to send task progress notification: {e}")
            return False
    
    async def notify_task_completed(self, task_id: str, result: Dict[str, Any], user_id: str):
        """通知任务完成"""
        if not self.emitter:
            log.warning("WebSocket emitter not available")
            return False
        
        try:
            payload = {
                "task_id": task_id,
                "result": result,
                "user_id": user_id,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await self.emitter.emit(
                "hsai_task_completed",
                payload,
                to=user_id
            )
            
            log.info(f"Task completed notification sent: {task_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to send task completed notification: {e}")
            return False
    
    async def notify_task_failed(self, task_id: str, error: str, user_id: str):
        """通知任务失败"""
        if not self.emitter:
            log.warning("WebSocket emitter not available")
            return False
        
        try:
            payload = {
                "task_id": task_id,
                "error": error,
                "user_id": user_id,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await self.emitter.emit(
                "hsai_task_failed",
                payload,
                to=user_id
            )
            
            log.info(f"Task failed notification sent: {task_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to send task failed notification: {e}")
            return False
    
    async def notify_workflow_status(self, workflow_id: str, execution_id: str, status: str, user_id: str, data: Optional[Dict[str, Any]] = None):
        """通知工作流状态变更"""
        if not self.emitter:
            log.warning("WebSocket emitter not available")
            return False
        
        try:
            payload = {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "status": status,
                "user_id": user_id,
                "timestamp": asyncio.get_event_loop().time(),
                "data": data or {}
            }
            
            await self.emitter.emit(
                "hsai_workflow_status",
                payload,
                to=user_id
            )
            
            log.info(f"Workflow status notification sent: {workflow_id} - {status}")
            return True
            
        except Exception as e:
            log.error(f"Failed to send workflow status notification: {e}")
            return False
    
    async def notify_chat_message(self, chat_id: str, message: Dict[str, Any], user_id: str):
        """通知新的聊天消息"""
        if not self.emitter:
            log.warning("WebSocket emitter not available")
            return False
        
        try:
            payload = {
                "chat_id": chat_id,
                "message": message,
                "user_id": user_id,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await self.emitter.emit(
                "hsai_chat_message",
                payload,
                to=user_id
            )
            
            log.info(f"Chat message notification sent: {chat_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to send chat message notification: {e}")
            return False
    
    async def notify_system_alert(self, alert_type: str, message: str, user_id: Optional[str] = None, broadcast: bool = False):
        """发送系统警告通知"""
        if not self.emitter:
            log.warning("WebSocket emitter not available")
            return False
        
        try:
            payload = {
                "alert_type": alert_type,
                "message": message,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            if broadcast:
                # 广播给所有用户
                await self.emitter.emit("hsai_system_alert", payload)
            elif user_id:
                # 发送给特定用户
                await self.emitter.emit("hsai_system_alert", payload, to=user_id)
            else:
                log.warning("No target specified for system alert")
                return False
            
            log.info(f"System alert notification sent: {alert_type}")
            return True
            
        except Exception as e:
            log.error(f"Failed to send system alert notification: {e}")
            return False

# 全局通知器实例
hsai_notifier = HSAIWebSocketNotifier()

async def test_websocket_notifications():
    """测试WebSocket通知功能"""
    test_user_id = "test_user_123"
    test_task_id = "test_task_456"
    
    print("开始WebSocket通知机制测试...")
    
    # 测试任务开始通知
    result1 = await hsai_notifier.notify_task_started(
        task_id=test_task_id,
        task_type="video_script_generation",
        user_id=test_user_id,
        data={"estimated_duration": 30}
    )
    print(f"任务开始通知: {'成功' if result1 else '失败'}")
    
    # 测试进度通知
    for progress in [25, 50, 75]:
        result2 = await hsai_notifier.notify_task_progress(
            task_id=test_task_id,
            progress=progress,
            user_id=test_user_id,
            message=f"处理进度 {progress}%"
        )
        print(f"进度通知 {progress}%: {'成功' if result2 else '失败'}")
        await asyncio.sleep(1)
    
    # 测试任务完成通知
    result3 = await hsai_notifier.notify_task_completed(
        task_id=test_task_id,
        result={"script": "测试脚本内容", "duration": 60},
        user_id=test_user_id
    )
    print(f"任务完成通知: {'成功' if result3 else '失败'}")
    
    # 测试系统警告
    result4 = await hsai_notifier.notify_system_alert(
        alert_type="info",
        message="WebSocket通知机制测试完成",
        user_id=test_user_id
    )
    print(f"系统警告通知: {'成功' if result4 else '失败'}")
    
    print("WebSocket通知机制测试完成")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_websocket_notifications())