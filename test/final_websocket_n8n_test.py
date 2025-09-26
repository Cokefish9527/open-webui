"""
最终版HSAI WebSocket与n8n集成测试脚本
解决HTTP 403错误问题
"""

import asyncio
import json
import time
import requests
import websockets
import logging
from datetime import datetime
from typing import Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinalWebSocketN8NTester:
    """最终版WebSocket与n8n测试器"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.websocket: Any = None
        self.n8n_test_url = "http://localhost:5678/webhook"
        self.test_results = {
            "connection": False,
            "authentication": False,
            "message_sent": False,
            "response_received": False,
            "workflow_triggered": False,
            "response_formatted": False
        }
        
    async def login(self) -> bool:
        """用户登录获取token"""
        try:
            logger.info("🔐 用户登录获取认证信息...")
            
            login_data = {
                "email": "saiter2306@163.com",
                "password": "123456"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/auths/signin",
                json=login_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.token = result.get("token")
                self.user_id = result.get("id")
                
                logger.info(f"✅ 登录成功！用户ID: {self.user_id}")
                return True
            else:
                logger.error(f"❌ 登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 登录异常: {e}")
            return False
            
    async def connect_websocket(self) -> bool:
        """建立WebSocket连接 - 使用正确的路径和认证方式"""
        try:
            logger.info("🌐 建立WebSocket连接...")
            
            # 使用正确的Socket.IO路径 - 根据后端配置应该是 /ws/socket.io/
            # 后端挂载了 app.mount("/ws", socket_app) 并且 SOCKETIO_PATH=/ws/socket.io
            # 所以完整路径应该是 /ws/socket.io/
            ws_url = f"ws://localhost:8080/ws/socket.io/?EIO=4&transport=websocket"
            logger.info(f"📍 连接地址: {ws_url}")
            
            # 连接WebSocket，不使用extra_headers参数以避免版本兼容性问题
            self.websocket = await websockets.connect(
                ws_url
            )
            
            # 处理初始连接消息 (Engine.IO handshake)
            initial_msg = await self.websocket.recv()
            logger.info(f"🔗 初始连接消息: {initial_msg}")
            
            # 发送Socket.IO连接消息，包含认证信息
            # 格式: 40<namespace>,<auth_data>
            # 对于默认命名空间，格式为: 40{"token":"<token>"} 或 40"","{"token":"<token>"}
            # 修复认证消息格式，使用正确的Socket.IO格式
            auth_msg = f'40{{"token":"{self.token}"}}'
            logger.info(f"📤 发送认证消息: {auth_msg}")
            await self.websocket.send(auth_msg)
            
            # 等待连接确认消息
            try:
                confirm_msg = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
                logger.info(f"✅ 认证确认: {confirm_msg}")
                
                # 检查是否连接成功
                if str(confirm_msg).startswith('40'):  # Socket.IO CONNECT事件
                    self.test_results["connection"] = True
                    self.test_results["authentication"] = True
                    logger.info("✅ WebSocket连接和认证成功")
                    return True
                elif str(confirm_msg).startswith('41'):  # Socket.IO CONNECT_ERROR事件
                    logger.error(f"❌ 认证失败: {confirm_msg}")
                    return False
                else:
                    logger.info(f"ℹ️  收到其他消息: {confirm_msg}")
                    # 继续尝试接收连接确认
                    start_time = time.time()
                    while time.time() - start_time < 10:
                        try:
                            msg = await asyncio.wait_for(self.websocket.recv(), timeout=2.0)
                            logger.info(f"📥 收到消息: {msg}")
                            if str(msg).startswith('40'):  # 连接成功
                                self.test_results["connection"] = True
                                self.test_results["authentication"] = True
                                logger.info("✅ WebSocket连接和认证成功")
                                return True
                            elif str(msg).startswith('41'):  # 连接错误
                                logger.error(f"❌ 认证失败: {msg}")
                                return False
                        except asyncio.TimeoutError:
                            continue
                            
            except asyncio.TimeoutError:
                logger.warning("⏰ 等待认证确认消息超时")
                # 即使超时，如果连接建立成功也算部分成功
                if self.websocket and hasattr(self.websocket, 'open') and self.websocket.open:
                    self.test_results["connection"] = True
                    logger.info("✅ WebSocket连接建立成功（认证状态待确认）")
                    return True
                
        except Exception as e:
            logger.error(f"❌ WebSocket连接异常: {e}")
            return False
            
        return False  # 确保所有路径都有返回值
    
    async def send_test_message(self) -> bool:
        """发送测试消息"""
        if not self.websocket:
            logger.error("❌ WebSocket连接未建立")
            return False
            
        try:
            # 构造测试消息
            import uuid
            test_message = {
                "type": "chat",
                "content": "测试WebSocket与n8n集成",
                "user_id": self.user_id,
                "entry_type": "chat",
                "session_id": f"test_{uuid.uuid4().hex[:8]}",  # 使用UUID而不是时间戳
                "timestamp": int(time.time()),
                "test_mode": True,
                "n8n_webhook_url": self.n8n_test_url
            }
            
            logger.info("📤 发送测试消息到WebSocket...")
            
            # 使用Socket.IO协议格式发送消息
            # 42表示MESSAGE事件，["message", data]是事件名和数据
            # 注意：必须使用"message"事件名，因为HSAI事件处理器注册的就是这个事件
            socketio_msg = f'42["message",{json.dumps(test_message, ensure_ascii=False)}]'
            logger.info(f"📤 发送Socket.IO消息: {socketio_msg[:100]}...")
            await self.websocket.send(socketio_msg)
            
            self.test_results["message_sent"] = True
            logger.info("✅ 测试消息发送成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 发送消息异常: {e}")
            return False
    
    async def listen_for_workflow_response(self, timeout: int = 30) -> bool:
        """监听工作流响应"""
        if not self.websocket:
            logger.error("❌ WebSocket连接未建立")
            return False
            
        logger.info(f"👂 监听工作流响应 (超时: {timeout}秒)...")
        
        start_time = time.time()
        workflow_response_received = False
        
        try:
            while time.time() - start_time < timeout and not workflow_response_received:
                try:
                    # 接收消息
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    response_str = str(response)
                    
                    # 处理Socket.IO协议消息
                    if response_str.startswith('42'):
                        # Socket.IO MESSAGE事件
                        json_part = response_str[2:]  # 移除'42'前缀
                        try:
                            data = json.loads(json_part)
                            if isinstance(data, list) and len(data) >= 2:
                                event_name = data[0]
                                event_data = data[1]
                                
                                logger.info(f"📨 收到事件: {event_name}")
                                
                                # 检查是否为HSAI响应
                                if event_name == "message" and isinstance(event_data, dict):
                                    msg_type = event_data.get("type", "")
                                    logger.info(f"📄 消息类型: {msg_type}")
                                    
                                    # 检查是否为HSAI响应消息
                                    if msg_type in ["hsai_response", "workflow_completed"]:
                                        logger.info("✅ 检测到工作流响应")
                                        logger.info(f"📊 响应数据: {json.dumps(event_data, ensure_ascii=False)[:200]}...")
                                        
                                        self.test_results["response_received"] = True
                                        self.test_results["workflow_triggered"] = True
                                        
                                        # 检查响应是否被正确格式化
                                        required_fields = ["success", "execution_id", "workflow_type", "session_id"]
                                        if all(field in event_data for field in required_fields):
                                            self.test_results["response_formatted"] = True
                                            logger.info("✅ 响应数据格式正确")
                                        
                                        workflow_response_received = True
                                        return True
                                        
                                elif event_name == "error" and isinstance(event_data, dict):
                                    error_type = event_data.get("type", "")
                                    logger.error(f"❌ 收到错误响应: {error_type} - {event_data.get('content', '')}")
                                    workflow_response_received = True
                                    return False
                                    
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️  无法解析JSON: {json_part[:100]}")
                            
                    elif response_str.startswith('2'):
                        # Socket.IO PING消息，需要回复PONG
                        logger.debug("🏓 收到PING消息，发送PONG")
                        await self.websocket.send('3')
                        
                    elif response_str.startswith('3'):
                        # Socket.IO PONG消息
                        logger.debug("🏓 收到PONG消息")
                        
                    elif response_str.startswith('0'):
                        # Socket.IO CONNECT消息
                        logger.info("🔗 收到连接消息")
                        
                    elif response_str.startswith('1'):
                        # Socket.IO DISCONNECT消息
                        logger.info("🔗 收到断开连接消息")
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"⚠️  接收消息时异常: {e}")
                    continue
                    
            if not workflow_response_received:
                logger.warning("⏰ 监听超时，未收到工作流响应")
                return False
                
        except Exception as e:
            logger.error(f"❌ 监听响应异常: {e}")
            return False
            
        return workflow_response_received
    
    async def run_test(self) -> dict:
        """运行完整测试"""
        logger.info("🚀 开始WebSocket与n8n集成测试...")
        
        try:
            # 1. 登录获取认证信息
            if not await self.login():
                logger.error("❌ 登录失败，无法继续测试")
                return self.test_results
                
            # 2. 建立WebSocket连接
            if not await self.connect_websocket():
                logger.error("❌ WebSocket连接失败")
                return self.test_results
                
            # 3. 发送测试消息
            if not await self.send_test_message():
                logger.error("❌ 发送测试消息失败")
                return self.test_results
                
            # 4. 监听工作流响应
            await self.listen_for_workflow_response(timeout=30)
            
            # 5. 关闭连接
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
                logger.info("🔒 WebSocket连接已关闭")
                
        except Exception as e:
            logger.error(f"❌ 测试执行异常: {e}")
            
        # 输出测试结果
        logger.info("📊 测试结果:")
        for test_name, result in self.test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"   {test_name}: {status}")
            
        overall_success = all(self.test_results.values())
        logger.info(f"🎯 总体结果: {'✅ 成功' if overall_success else '❌ 失败'}")
        
        return self.test_results

async def main():
    """主函数"""
    tester = FinalWebSocketN8NTester()
    
    try:
        results = await tester.run_test()
        overall_success = all(results.values())
        
        if overall_success:
            logger.info("🎉 WebSocket与n8n集成测试成功!")
            return 0
        else:
            logger.error("❌ WebSocket与n8n集成测试失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"❌ 测试执行异常: {e}")
        return 1

if __name__ == "__main__":
    import sys
    result = asyncio.run(main())
    sys.exit(result)