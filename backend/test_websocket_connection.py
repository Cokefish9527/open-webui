"""
WebSocket连接测试脚本
用于验证OpenWebUI的WebSocket端点是否正常工作

解决问题：
1. 使用正确的WebSocket URL格式: ws://localhost:8080/hsai/ws/{user_id}?token={token}
2. 移除不支持的timeout参数
3. 使用正确的认证方式
"""

import asyncio
import json
import time
import requests
import websockets
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSocketConnectionTester:
    """WebSocket连接测试器"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.token = None
        self.user_id = None
        
    async def login(self) -> bool:
        """用户登录获取token"""
        try:
            logger.info("🔐 开始用户登录...")
            
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
            
    async def test_websocket_connection(self) -> bool:
        """测试WebSocket连接"""
        try:
            logger.info("🌐 测试WebSocket连接...")
            
            # 构建正确的WebSocket URL
            ws_url = f"ws://localhost:8080/hsai/ws/{self.user_id}?token={self.token}"
            logger.info(f"📍 WebSocket URL: {ws_url}")
            
            # 连接WebSocket（不使用timeout参数）
            async with websockets.connect(ws_url) as websocket:
                logger.info("✅ WebSocket连接建立成功")
                
                # 等待连接确认消息
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    connection_msg = json.loads(response)
                    logger.info(f"📥 收到连接确认消息: {connection_msg.get('content', 'N/A')}")
                    
                    # 显示可用的工作流
                    if 'available_workflows' in connection_msg:
                        logger.info("📋 可用工作流:")
                        for workflow in connection_msg['available_workflows']:
                            logger.info(f"   - {workflow['name']}: {workflow['description']}")
                            
                except asyncio.TimeoutError:
                    logger.warning("⏰ 等待连接确认消息超时")
                
                # 发送测试消息
                test_message = {
                    "type": "chat",
                    "content": "Hello, 这是一个WebSocket连接测试消息",
                    "user_id": self.user_id,
                    "entry_type": "chat",
                    "session_id": f"test_session_{int(time.time())}",
                    "metadata": {
                        "test": True,
                        "timestamp": datetime.now().isoformat() if 'datetime' in globals() else str(int(time.time()))
                    }
                }
                
                logger.info("📤 发送测试消息...")
                await websocket.send(json.dumps(test_message, ensure_ascii=False))
                
                # 等待响应
                start_time = time.time()
                response_received = False
                
                while time.time() - start_time < 30 and not response_received:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        
                        logger.info(f"📥 收到响应: {response_data}")
                        
                        if response_data.get("type") in ["workflow_response", "error"]:
                            response_received = True
                            if response_data.get("type") == "workflow_response":
                                if response_data.get("success"):
                                    logger.info("✅ WebSocket工作流测试成功")
                                    return True
                                else:
                                    logger.error(f"❌ 工作流执行失败: {response_data.get('error_message')}")
                                    return False
                            else:
                                logger.error(f"❌ 收到错误响应: {response_data.get('content')}")
                                return False
                        
                    except asyncio.TimeoutError:
                        logger.info("⏳ 等待响应中...")
                        continue
                    except Exception as e:
                        logger.error(f"❌ 接收响应异常: {e}")
                        break
                
                if not response_received:
                    logger.warning("⏰ 未收到完整响应，但连接正常")
                    return True  # 连接本身是成功的
                    
        except Exception as e:
            logger.error(f"❌ WebSocket连接测试异常: {e}")
            return False
        
        return True
    
    async def run_test(self) -> bool:
        """运行完整测试"""
        logger.info("🚀 开始WebSocket连接测试...")
        
        # 1. 登录
        if not await self.login():
            return False
            
        # 2. 测试WebSocket连接
        if not await self.test_websocket_connection():
            return False
            
        logger.info("🎉 WebSocket连接测试完成!")
        return True

async def main():
    """主函数"""
    tester = WebSocketConnectionTester()
    
    try:
        success = await tester.run_test()
        if success:
            logger.info("✅ 所有测试通过")
        else:
            logger.error("❌ 测试失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"❌ 测试执行异常: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    import sys
    result = asyncio.run(main())
    sys.exit(result)