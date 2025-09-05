"""
WebSocket工作流测试脚本

测试服务端通过WebSocket转发工作流信息并将返回的信息结构化返回的功能
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Any, Optional
import time

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class WebSocketWorkflowTester:
    """WebSocket工作流测试器"""
    
    def __init__(self, websocket_url: str, token: str):
        self.websocket_url = websocket_url
        self.token = token
        self.websocket = None
        self.received_messages = []
        self.is_connected = False
        self.receive_task = None
    
    async def connect(self) -> bool:
        """连接到WebSocket"""
        try:
            uri = f"{self.websocket_url}?token={self.token}"
            self.websocket = await websockets.connect(uri)
            self.is_connected = True
            log.info("Connected to WebSocket")
            
            # 启动消息接收任务
            self.receive_task = asyncio.create_task(self._receive_messages())
            # 等待一点时间让连接建立完成
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            log.error(f"Failed to connect: {e}")
            return False
    
    async def _receive_messages(self):
        """接收消息的后台任务"""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    self.received_messages.append(data)
                    log.info(f"Received message: {data.get('type', 'unknown')}")
                    
                    # 打印详细信息
                    if data.get('type') == 'workflow_response':
                        log.info(f"Workflow response: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    elif data.get('type') == 'status':
                        log.info(f"Status update: {data.get('content')}")
                    elif data.get('type') == 'error':
                        log.error(f"Error received: {data.get('content')}")
                        
                except websockets.exceptions.ConnectionClosed:
                    log.info("WebSocket connection closed")
                    break
                except Exception as e:
                    log.error(f"Error receiving message: {e}")
        except Exception as e:
            log.error(f"Error in receive task: {e}")
    
    async def send_message(self, message: Dict[str, Any]):
        """发送消息"""
        if not self.websocket or not self.is_connected:
            log.error("WebSocket not connected")
            return False
        
        try:
            await self.websocket.send(json.dumps(message, ensure_ascii=False))
            log.info(f"Sent message: {message['type']}")
            return True
        except Exception as e:
            log.error(f"Failed to send message: {e}")
            return False
    
    async def wait_for_response(self, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """等待响应消息"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.received_messages:
                return self.received_messages.pop(0)
            await asyncio.sleep(0.1)
        return None
    
    async def clear_messages(self):
        """清空消息队列"""
        self.received_messages.clear()
    
    async def test_chat_message(self, content: str, entry_type: str = "chat") -> Optional[Dict[str, Any]]:
        """测试聊天消息场景"""
        message = {
            "type": "chat",
            "content": content,
            "user_id": "test_user",
            "session_id": f"test_session_{int(time.time())}",
            "entry_type": entry_type,
            "metadata": {
                "test": True,
                "scenario": "chat_message"
            }
        }
        
        await self.clear_messages()
        if await self.send_message(message):
            return await self.wait_for_response()
        return None
    
    async def test_workflow_trigger(self, workflow_type: str, content: str) -> Optional[Dict[str, Any]]:
        """测试工作流触发场景"""
        message = {
            "type": "workflow_trigger",
            "content": content,
            "user_id": "test_user",
            "session_id": f"test_session_{int(time.time())}",
            "workflow_type": workflow_type,
            "metadata": {
                "test": True,
                "scenario": "workflow_trigger"
            }
        }
        
        await self.clear_messages()
        if await self.send_message(message):
            return await self.wait_for_response()
        return None
    
    async def test_company_info_collection(self) -> Optional[Dict[str, Any]]:
        """测试公司信息收集场景"""
        message = {
            "type": "chat",
            "content": "请收集阿里巴巴公司的信息并生成作战地图",
            "user_id": "test_user",
            "session_id": f"test_session_{int(time.time())}",
            "entry_type": "company",
            "metadata": {
                "test": True,
                "scenario": "company_info_collection"
            }
        }
        
        await self.clear_messages()
        if await self.send_message(message):
            return await self.wait_for_response(60)  # 公司信息收集可能需要更长时间
        return None
    
    async def test_viral_learning_analysis(self) -> Optional[Dict[str, Any]]:
        """测试爆款学习分析场景"""
        message = {
            "type": "workflow_trigger",
            "content": "请分析最近的爆款内容特点",
            "user_id": "test_user",
            "session_id": f"test_session_{int(time.time())}",
            "workflow_type": "viral_learning",
            "metadata": {
                "test": True,
                "scenario": "viral_learning_analysis"
            }
        }
        
        await self.clear_messages()
        if await self.send_message(message):
            return await self.wait_for_response(60)  # 爆款学习可能需要更长时间
        return None
    
    async def test_error_handling(self) -> Optional[Dict[str, Any]]:
        """测试错误处理场景"""
        message = {
            "type": "workflow_trigger",
            "content": "测试错误处理",
            "user_id": "test_user",
            "session_id": f"test_session_{int(time.time())}",
            "workflow_type": "nonexistent_workflow",  # 不存在的工作流类型
            "metadata": {
                "test": True,
                "scenario": "error_handling"
            }
        }
        
        await self.clear_messages()
        if await self.send_message(message):
            return await self.wait_for_response()
        return None
    
    async def run_all_tests(self):
        """运行所有测试场景"""
        if not await self.connect():
            log.error("Failed to connect to WebSocket")
            return
        
        try:
            log.info("=== 开始WebSocket工作流测试 ===")
            
            # 测试场景1: 基础聊天消息
            log.info("\n--- 测试场景1: 基础聊天消息 ---")
            response = await self.test_chat_message("你好，请帮助我处理一个任务")
            if response:
                log.info(f"✓ 基础聊天消息测试通过")
                log.info(f"  响应类型: {response.get('type')}")
                log.info(f"  响应内容: {response.get('content', '')[:100]}...")
            else:
                log.error("✗ 基础聊天消息测试失败")
            
            # 等待一段时间
            await asyncio.sleep(2)
            
            # 测试场景2: 明确指定工作流类型
            log.info("\n--- 测试场景2: 明确指定工作流类型 ---")
            response = await self.test_workflow_trigger("main", "请执行一个通用任务")
            if response:
                log.info(f"✓ 明确指定工作流类型测试通过")
                log.info(f"  响应类型: {response.get('type')}")
                log.info(f"  工作流类型: {response.get('workflow_type', 'N/A')}")
            else:
                log.error("✗ 明确指定工作流类型测试失败")
            
            # 等待一段时间
            await asyncio.sleep(2)
            
            # 测试场景3: 公司信息收集（基于入口类型）
            log.info("\n--- 测试场景3: 公司信息收集 ---")
            response = await self.test_company_info_collection()
            if response:
                log.info(f"✓ 公司信息收集测试通过")
                log.info(f"  响应类型: {response.get('type')}")
                log.info(f"  是否成功: {response.get('success', False)}")
            else:
                log.error("✗ 公司信息收集测试失败")
            
            # 等待一段时间
            await asyncio.sleep(2)
            
            # 测试场景4: 爆款学习分析
            log.info("\n--- 测试场景4: 爆款学习分析 ---")
            response = await self.test_viral_learning_analysis()
            if response:
                log.info(f"✓ 爆款学习分析测试通过")
                log.info(f"  响应类型: {response.get('type')}")
                log.info(f"  是否成功: {response.get('success', False)}")
            else:
                log.error("✗ 爆款学习分析测试失败")
            
            # 等待一段时间
            await asyncio.sleep(2)
            
            # 测试场景5: 错误处理
            log.info("\n--- 测试场景5: 错误处理 ---")
            response = await self.test_error_handling()
            if response:
                log.info(f"✓ 错误处理测试通过")
                log.info(f"  响应类型: {response.get('type')}")
                if response.get('type') == 'error':
                    log.info(f"  正确捕获错误: {response.get('content')}")
            else:
                log.error("✗ 错误处理测试失败")
            
            log.info("\n=== 所有测试完成 ===")
            
        except Exception as e:
            log.error(f"Test suite failed: {e}")
        finally:
            await self.disconnect()
    
    async def disconnect(self):
        """断开连接"""
        self.is_connected = False
        if self.receive_task:
            self.receive_task.cancel()
        if self.websocket:
            await self.websocket.close()
            log.info("WebSocket connection closed")

async def main():
    """主函数"""
    # 配置测试参数
    websocket_url = "ws://localhost:8080/hsai/ws/test_user"
    token = "your_test_token_here"  # 需要替换为实际的token
    
    tester = WebSocketWorkflowTester(websocket_url, token)
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())