"""
n8n工作流集成测试脚本

用于测试WebSocket连接和n8n工作流调用功能
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class N8NIntegrationTester:
    """n8n集成测试器"""
    
    def __init__(self, websocket_url: str, token: str):
        self.websocket_url = websocket_url
        self.token = token
        self.websocket = None
    
    async def connect(self):
        """连接到WebSocket"""
        try:
            uri = f"{self.websocket_url}?token={self.token}"
            self.websocket = await websockets.connect(uri)
            log.info("Connected to WebSocket")
            return True
        except Exception as e:
            log.error(f"Failed to connect: {e}")
            return False
    
    async def send_message(self, message: Dict[str, Any]):
        """发送消息"""
        if not self.websocket:
            log.error("WebSocket not connected")
            return
        
        try:
            await self.websocket.send(json.dumps(message, ensure_ascii=False))
            log.info(f"Sent message: {message['type']}")
        except Exception as e:
            log.error(f"Failed to send message: {e}")
    
    async def receive_message(self):
        """接收消息"""
        if not self.websocket:
            return None
        
        try:
            message = await self.websocket.recv()
            data = json.loads(message)
            log.info(f"Received message: {data.get('type', 'unknown')}")
            return data
        except Exception as e:
            log.error(f"Failed to receive message: {e}")
            return None
    
    async def test_chat_message(self, content: str):
        """测试聊天消息"""
        message = {
            "type": "chat",
            "content": content,
            "user_id": "test_user",
            "session_id": "test_session",
            "metadata": {
                "test": True
            }
        }
        
        await self.send_message(message)
        response = await self.receive_message()
        return response
    
    async def test_workflow_trigger(self, workflow_type: str, content: str):
        """测试工作流触发"""
        message = {
            "type": "workflow_trigger",
            "content": content,
            "user_id": "test_user",
            "session_id": "test_session",
            "workflow_type": workflow_type,
            "metadata": {
                "test": True
            }
        }
        
        await self.send_message(message)
        response = await self.receive_message()
        return response
    
    async def run_tests(self):
        """运行测试套件"""
        if not await self.connect():
            return
        
        try:
            # 测试1: 基础聊天消息
            log.info("Testing basic chat message...")
            response = await self.test_chat_message("你好，请帮助我处理一个任务")
            if response:
                log.info(f"Chat response: {response.get('success', False)}")
            
            # 测试2: 爆款学习工作流
            log.info("Testing viral learning workflow...")
            response = await self.test_workflow_trigger(
                "viral_learning", 
                "请分析这个爆款内容的特点"
            )
            if response:
                log.info(f"Viral learning response: {response.get('success', False)}")
            
            # 测试3: 公司信息收集工作流
            log.info("Testing company info workflow...")
            response = await self.test_workflow_trigger(
                "company_info",
                "请收集某公司的信息并生成作战地图"
            )
            if response:
                log.info(f"Company info response: {response.get('success', False)}")
            
            # 测试4: 视频分析工作流
            log.info("Testing video analysis workflow...")
            response = await self.test_workflow_trigger(
                "video_analysis",
                "请分析这个视频的关键词"
            )
            if response:
                log.info(f"Video analysis response: {response.get('success', False)}")
            
        except Exception as e:
            log.error(f"Test failed: {e}")
        finally:
            if self.websocket:
                await self.websocket.close()
                log.info("WebSocket connection closed")

async def main():
    """主函数"""
    # 配置测试参数
    websocket_url = "ws://localhost:8080/hsai/ws/test_user"
    token = "your_test_token_here"  # 需要替换为实际的token
    
    tester = N8NIntegrationTester(websocket_url, token)
    await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())