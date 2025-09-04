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