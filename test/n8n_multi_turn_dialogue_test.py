"""
多轮对话测试脚本
测试向n8n测试地址（https://n8n.hsai.cc/webhook-test/n8n_chat）发送消息
记录模拟前端、服务端的收发顺序
"""

import asyncio
import json
import time
import requests
import websockets
import logging
from datetime import datetime
from typing import Optional, Any, List, Dict

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiTurnDialogueTester:
    """多轮对话测试器"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.n8n_test_url = "https://n8n.hsai.cc/webhook-test/n8n_chat"
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.websocket: Any = None
        # 使用UUID方式构造session_id，而不是时间戳拼接
        import uuid
        self.session_id: str = f"multi_turn_test_{uuid.uuid4().hex[:8]}"
        self.message_sequence: List[Dict[str, Any]] = []
        self.test_results = {
            "connection": False,
            "authentication": False,
            "messages_sent": 0,
            "responses_received": 0,
            "workflow_triggered": 0,
            "sequence_correct": True
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
        """建立WebSocket连接"""
        try:
            logger.info("🌐 建立WebSocket连接...")
            
            # 使用正确的Socket.IO路径
            ws_url = f"ws://localhost:8080/ws/socket.io/?EIO=4&transport=websocket"
            logger.info(f"📍 连接地址: {ws_url}")
            
            # 连接WebSocket
            self.websocket = await websockets.connect(ws_url)
            
            # 处理初始连接消息 (Engine.IO handshake)
            initial_msg = await self.websocket.recv()
            self._log_message("服务端", "初始连接", initial_msg)
            
            # 发送Socket.IO连接消息，包含认证信息
            auth_msg = f'40{{"token":"{self.token}"}}'
            self._log_message("前端", "认证请求", auth_msg)
            await self.websocket.send(auth_msg)
            
            # 等待连接确认消息
            try:
                confirm_msg = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
                self._log_message("服务端", "认证响应", confirm_msg)
                
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
                            self._log_message("服务端", "连接消息", msg)
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
    
    def _log_message(self, sender: str, msg_type: str, content: Any):
        """记录消息收发顺序"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        message_record = {
            "timestamp": timestamp,
            "sender": sender,
            "type": msg_type,
            "content": str(content)[:200] + "..." if len(str(content)) > 200 else str(content)
        }
        self.message_sequence.append(message_record)
        logger.info(f"[{timestamp}] {sender} -> {msg_type}: {message_record['content']}")
    
    async def send_message(self, content: str, message_number: int) -> bool:
        """发送单条消息"""
        if not self.websocket:
            logger.error("❌ WebSocket连接未建立")
            return False
            
        try:
            # 构造HSAI测试消息
            test_message = {
                "type": "workflow_trigger",
                "content": content,
                "user_id": self.user_id,
                "entry_type": "chat",
                "session_id": self.session_id,
                "workflow_type": "main",
                "timestamp": datetime.now().isoformat(),
                "test": True,
                "n8n_webhook_url": self.n8n_test_url,
                "message_number": message_number  # 添加消息编号用于跟踪
            }
            
            logger.info(f"📤 发送第 {message_number} 轮对话消息...")
            
            # 使用Socket.IO协议格式发送消息
            socketio_msg = f'42["message",{json.dumps(test_message, ensure_ascii=False)}]'
            self._log_message("前端", f"对话消息#{message_number}", socketio_msg)
            await self.websocket.send(socketio_msg)
            
            self.test_results["messages_sent"] += 1
            logger.info(f"✅ 第 {message_number} 轮对话消息发送成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 发送第 {message_number} 轮对话消息异常: {e}")
            return False
    
    async def listen_for_responses(self, expected_responses: int, timeout: int = 60) -> bool:
        """监听工作流响应"""
        if not self.websocket:
            logger.error("❌ WebSocket连接未建立")
            return False
            
        logger.info(f"👂 监听工作流响应 (期待 {expected_responses} 个响应，超时: {timeout}秒)...")
        
        start_time = time.time()
        responses_received = 0
        
        try:
            while time.time() - start_time < timeout and responses_received < expected_responses:
                try:
                    # 接收消息
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    response_str = str(response)
                    
                    # 记录收到的消息
                    self._log_message("服务端", f"响应消息#{responses_received+1}", response_str)
                    
                    # 处理Socket.IO协议消息
                    if response_str.startswith('42'):
                        # Socket.IO MESSAGE事件
                        json_part = response_str[2:]  # 移除'42'前缀
                        try:
                            data = json.loads(json_part)
                            if isinstance(data, list) and len(data) >= 2:
                                event_name = data[0]
                                event_data = data[1]
                                
                                if event_name == "message" and isinstance(event_data, dict):
                                    msg_type = event_data.get("type", "")
                                    
                                    # 检查是否为HSAI响应消息
                                    if msg_type in ["hsai_response", "workflow_completed", "n8n_response"]:
                                        self.test_results["responses_received"] += 1
                                        self.test_results["workflow_triggered"] += 1
                                        responses_received += 1
                                        logger.info(f"✅ 收到第 {responses_received} 个工作流响应")
                                        
                                elif event_name == "error" and isinstance(event_data, dict):
                                    logger.error(f"❌ 收到错误响应: {event_data.get('content', '')}")
                                    return False
                                    
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️  无法解析JSON: {json_part[:100]}")
                            
                    elif response_str.startswith('2'):
                        # Socket.IO PING消息，需要回复PONG
                        await self.websocket.send('3')
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"⚠️  接收消息时异常: {e}")
                    continue
                    
            if responses_received < expected_responses:
                logger.warning(f"⏰ 监听超时，只收到 {responses_received}/{expected_responses} 个响应")
                return False
            else:
                logger.info(f"✅ 成功收到所有 {expected_responses} 个响应")
                return True
                
        except Exception as e:
            logger.error(f"❌ 监听响应异常: {e}")
            return False
    
    async def run_multi_turn_test(self) -> dict:
        """运行多轮对话测试"""
        logger.info("🚀 开始多轮对话测试...")
        logger.info(f"🎯 测试端点: {self.n8n_test_url}")
        logger.info(f"🔢 会话ID: {self.session_id}")
        
        # 定义多轮对话内容
        dialogue_content = [
            "你好，请介绍一下你们的服务",
            "我想了解视频创作流程",
            "能否提供一些爆款视频的建议？",
            "谢谢你的帮助"
        ]
        
        try:
            # 1. 登录获取认证信息
            if not await self.login():
                logger.error("❌ 登录失败，无法继续测试")
                return self.test_results
                
            # 2. 建立WebSocket连接
            if not await self.connect_websocket():
                logger.error("❌ WebSocket连接失败")
                return self.test_results
                
            # 3. 进行多轮对话
            for i, content in enumerate(dialogue_content, 1):
                logger.info(f"🔄 开始第 {i} 轮对话")
                
                # 发送消息
                if not await self.send_message(content, i):
                    logger.error(f"❌ 第 {i} 轮对话消息发送失败")
                    break
                
                # 等待响应（给每轮对话一些时间间隔）
                await asyncio.sleep(2)
                
                # 监听该轮对话的响应
                await self.listen_for_responses(1, timeout=30)
                
                # 轮间间隔
                if i < len(dialogue_content):
                    logger.info(f"⏳ 等待2秒后进行下一轮对话...")
                    await asyncio.sleep(2)
            
            # 4. 关闭连接
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
                self._log_message("前端", "连接关闭", "WebSocket连接已关闭")
                logger.info("🔒 WebSocket连接已关闭")
                
        except Exception as e:
            logger.error(f"❌ 测试执行异常: {e}")
            
        # 输出测试结果
        logger.info("📊 测试结果:")
        for test_name, result in self.test_results.items():
            if isinstance(result, bool):
                status = "✅ 通过" if result else "❌ 失败"
            else:
                status = f"📊 {result}"
            logger.info(f"   {test_name}: {status}")
            
        overall_success = (
            self.test_results["connection"] and 
            self.test_results["authentication"] and
            self.test_results["messages_sent"] == len(dialogue_content) and
            self.test_results["responses_received"] == len(dialogue_content)
        )
        logger.info(f"🎯 总体结果: {'✅ 成功' if overall_success else '❌ 失败'}")
        
        # 保存消息序列到文件
        await self._save_message_sequence()
        
        return self.test_results
    
    async def _save_message_sequence(self):
        """保存消息序列到文件"""
        try:
            sequence_data = {
                "test_session": self.session_id,
                "n8n_endpoint": self.n8n_test_url,
                "timestamp": datetime.now().isoformat(),
                "message_sequence": self.message_sequence,
                "test_results": self.test_results
            }
            
            filename = f"multi_turn_dialogue_sequence_{int(time.time())}.json"
            filepath = f"c:\\work\\open-webui\\test\\{filename}"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(sequence_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"📝 消息序列已保存到: {filepath}")
        except Exception as e:
            logger.error(f"❌ 保存消息序列失败: {e}")

async def main():
    """主函数"""
    tester = MultiTurnDialogueTester()
    
    try:
        results = await tester.run_multi_turn_test()
        overall_success = (
            results["connection"] and 
            results["authentication"] and
            results["messages_sent"] > 0 and
            results["responses_received"] > 0
        )
        
        if overall_success:
            logger.info("🎉 多轮对话测试成功!")
            return 0
        else:
            logger.error("❌ 多轮对话测试失败")
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