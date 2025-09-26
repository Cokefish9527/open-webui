"""
综合HSAI事件处理器测试脚本
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

class ComprehensiveHSAITest:
    """综合HSAI测试器"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.websocket: Any = None
        self.sid: Optional[str] = None  # Socket.IO会话ID
        
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
        """建立WebSocket连接"""
        try:
            logger.info("🌐 建立WebSocket连接...")
            
            # 使用正确的Socket.IO路径
            ws_url = f"ws://localhost:8080/ws/socket.io/?EIO=4&transport=websocket"
            logger.info(f"📍 连接地址: {ws_url}")
            
            # 连接WebSocket，不使用extra_headers参数以避免版本兼容性问题
            self.websocket = await websockets.connect(
                ws_url
            )
            
            # 处理初始连接消息 (Engine.IO handshake)
            initial_msg = await self.websocket.recv()
            logger.info(f"🔗 初始连接消息: {initial_msg}")
            
            # 解析Socket.IO会话ID
            if str(initial_msg).startswith('0'):
                try:
                    handshake_data = json.loads(str(initial_msg)[1:])
                    self.sid = handshake_data.get('sid')
                    logger.info(f"🆔 Socket.IO会话ID: {self.sid}")
                except Exception as e:
                    logger.warning(f"⚠️  解析会话ID失败: {e}")
            
            # 发送Socket.IO连接消息，包含认证信息
            # 格式: 40<namespace>,<auth_data>
            # 对于默认命名空间，格式为: 40{"token":"<token>"} 或 40"","{"token":"<token>"}
            # 修复认证消息格式，使用正确的Socket.IO格式
            auth_msg = f'40{{"token":"{self.token}"}}'
            logger.info(f"📤 发送认证消息: {auth_msg}")
            await self.websocket.send(auth_msg)
            
            # 等待连接确认消息
            start_time = time.time()
            while time.time() - start_time < 10:
                try:
                    confirm_msg = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    logger.info(f"📥 收到消息: {confirm_msg}")
                    
                    if str(confirm_msg).startswith('40'):  # Socket.IO CONNECT事件
                        logger.info("✅ WebSocket连接和认证成功")
                        return True
                    elif str(confirm_msg).startswith('41'):  # Socket.IO CONNECT_ERROR事件
                        logger.error(f"❌ 认证失败: {confirm_msg}")
                        return False
                        
                except asyncio.TimeoutError:
                    continue
                    
            logger.warning("⏰ 等待认证确认消息超时")
            return False
            
        except Exception as e:
            logger.error(f"❌ WebSocket连接异常: {e}")
            return False
    
    async def send_hsai_message(self, message_type: str = "chat") -> bool:
        """发送HSAI消息"""
        if not self.websocket:
            logger.error("❌ WebSocket连接未建立")
            return False
            
        try:
            # 根据消息类型构造不同的内容
            content = "测试聊天消息内容"
            entry_type = "chat"
            if message_type == "workflow_trigger":
                content = "触发工作流测试"
                entry_type = "workflow_trigger"
            
            # 构造测试消息
            import uuid
            test_message = {
                "type": "chat",
                "content": content,
                "user_id": self.user_id,
                "entry_type": entry_type,
                "session_id": f"test_{message_type}_{uuid.uuid4().hex[:8]}",  # 使用UUID而不是时间戳
                "timestamp": int(time.time()),
                "test_mode": True
            }
            
            logger.info(f"📤 发送HSAI {message_type} 消息...")
            
            # 使用Socket.IO协议格式发送消息
            # 42表示MESSAGE事件，["message", data]是事件名和数据
            socketio_msg = f'42["message",{json.dumps(test_message, ensure_ascii=False)}]'
            logger.info(f"📤 发送Socket.IO消息: {socketio_msg[:100]}...")
            await self.websocket.send(socketio_msg)
            
            logger.info("✅ HSAI消息发送成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 发送HSAI消息异常: {e}")
            return False
    
    async def listen_for_responses(self, timeout: int = 30) -> dict:
        """监听响应"""
        if not self.websocket:
            logger.error("❌ WebSocket连接未建立")
            return {"success": False, "responses": []}
            
        logger.info(f"👂 监听响应 (超时: {timeout}秒)...")
        
        responses = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    response_str = str(response)
                    logger.info(f"📥 收到响应: {response_str}")
                    
                    # 处理Socket.IO协议消息
                    if response_str.startswith('42'):
                        # Socket.IO MESSAGE事件
                        json_part = response_str[2:]  # 移除'42'前缀
                        try:
                            data = json.loads(json_part)
                            if isinstance(data, list) and len(data) >= 2:
                                event_name = data[0]
                                event_data = data[1]
                                
                                response_info = {
                                    "event": event_name,
                                    "data": event_data,
                                    "timestamp": time.time()
                                }
                                responses.append(response_info)
                                
                                logger.info(f"📨 事件: {event_name}")
                                if isinstance(event_data, dict):
                                    msg_type = event_data.get("type", "unknown")
                                    logger.info(f"📄 消息类型: {msg_type}")
                                    
                                    # 检查是否为HSAI响应
                                    if msg_type in ["hsai_response", "workflow_completed", "hsai_error"]:
                                        logger.info("✅ 检测到HSAI响应")
                                        logger.info(f"📊 响应数据: {json.dumps(event_data, ensure_ascii=False)[:200]}...")
                                        return {"success": True, "responses": responses, "hsai_response": event_data}
                                        
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
                    
            logger.warning("⏰ 监听超时")
            return {"success": False, "responses": responses}
            
        except Exception as e:
            logger.error(f"❌ 监听响应异常: {e}")
            return {"success": False, "responses": responses, "error": str(e)}
    
    async def run_comprehensive_test(self):
        """运行综合测试"""
        logger.info("🚀 开始综合HSAI事件处理器测试...")
        
        try:
            # 1. 登录获取认证信息
            if not await self.login():
                logger.error("❌ 登录失败，无法继续测试")
                return False
                
            # 2. 建立WebSocket连接
            if not await self.connect_websocket():
                logger.error("❌ WebSocket连接失败")
                return False
                
            # 3. 发送HSAI聊天消息
            if not await self.send_hsai_message("chat"):
                logger.error("❌ 发送HSAI聊天消息失败")
                return False
                
            # 4. 监听响应
            chat_response = await self.listen_for_responses(30)
            if chat_response.get("success"):
                logger.info("✅ HSAI聊天消息处理成功")
            else:
                logger.warning("⚠️  HSAI聊天消息处理未收到预期响应")
                
            # 5. 发送HSAI工作流触发消息
            if not await self.send_hsai_message("workflow_trigger"):
                logger.error("❌ 发送HSAI工作流触发消息失败")
                return False
                
            # 6. 监听响应
            workflow_response = await self.listen_for_responses(30)
            if workflow_response.get("success"):
                logger.info("✅ HSAI工作流触发消息处理成功")
            else:
                logger.warning("⚠️  HSAI工作流触发消息处理未收到预期响应")
                
            # 7. 关闭连接
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
                logger.info("🔒 WebSocket连接已关闭")
                
            # 输出测试结果
            logger.info("📊 测试结果:")
            logger.info(f"   登录: ✅ 成功")
            logger.info(f"   WebSocket连接: ✅ 成功")
            logger.info(f"   HSAI聊天消息发送: ✅ 成功")
            logger.info(f"   HSAI聊天消息响应: {'✅ 成功' if chat_response.get('success') else '⚠️ 未收到预期响应'}")
            logger.info(f"   HSAI工作流触发消息发送: ✅ 成功")
            logger.info(f"   HSAI工作流触发消息响应: {'✅ 成功' if workflow_response.get('success') else '⚠️ 未收到预期响应'}")
            
            overall_success = chat_response.get("success") or workflow_response.get("success")
            logger.info(f"🎯 总体结果: {'✅ 成功' if overall_success else '⚠️ 部分成功'}")
            
            return overall_success
            
        except Exception as e:
            logger.error(f"❌ 综合测试执行异常: {e}")
            return False

async def main():
    """主函数"""
    tester = ComprehensiveHSAITest()
    
    try:
        success = await tester.run_comprehensive_test()
        
        if success:
            logger.info("🎉 综合HSAI事件处理器测试成功!")
            return 0
        else:
            logger.warning("⚠️  综合HSAI事件处理器测试部分成功或失败")
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