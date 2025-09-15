"""
最终连接测试脚本
"""

import asyncio
import json
import time
import requests
import websockets
import logging
from datetime import datetime
from typing import Optional, Any

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinalConnectionTest:
    """最终连接测试"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.websocket: Any = None
        self.sid: Optional[str] = None
        
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
            
            logger.debug(f"登录响应状态码: {response.status_code}")
            
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
            logger.error(f"❌ 登录异常: {e}", exc_info=True)
            return False
            
    async def test_websocket_connection(self) -> bool:
        """测试WebSocket连接"""
        try:
            logger.info("🌐 测试WebSocket连接...")
            
            # 使用修正后的路径
            ws_url = "ws://localhost:8080/ws/socket.io/?EIO=4&transport=websocket"
            logger.info(f"📍 连接地址: {ws_url}")
            
            # 移除不支持的extra_headers参数
            self.websocket = await websockets.connect(
                ws_url,
                open_timeout=30,
                ping_interval=None
            )
            
            logger.info("✅ WebSocket连接建立成功")
            
            # 处理初始连接消息
            logger.info("👂 等待初始连接消息...")
            initial_msg = await self.websocket.recv()
            logger.info(f"🔗 初始连接消息: {initial_msg}")
            
            # 解析会话ID
            if str(initial_msg).startswith('0'):
                try:
                    handshake_data = json.loads(str(initial_msg)[1:])
                    self.sid = handshake_data.get('sid')
                    logger.info(f"🆔 Socket.IO会话ID: {self.sid}")
                except Exception as e:
                    logger.warning(f"⚠️  解析会话ID失败: {e}")
            
            # 发送认证消息
            auth_msg = f'40"","{{\\"token\\":\\"{self.token}\\"}}"'
            logger.info(f"📤 发送认证消息: {auth_msg}")
            await self.websocket.send(auth_msg)
            
            # 等待认证确认
            logger.info("👂 等待认证确认消息...")
            try:
                confirm_msg = await asyncio.wait_for(self.websocket.recv(), timeout=15.0)
                logger.info(f"✅ 认证确认消息: {confirm_msg}")
                
                if str(confirm_msg).startswith('40'):
                    logger.info("🎉 WebSocket认证成功")
                    return True
                elif str(confirm_msg).startswith('41'):
                    logger.error(f"❌ 认证失败: {confirm_msg}")
                    return False
                else:
                    logger.info(f"ℹ️  收到其他消息: {confirm_msg}")
                    return True
                    
            except asyncio.TimeoutError:
                logger.warning("⏰ 等待认证确认消息超时")
                return False
                
        except Exception as e:
            logger.error(f"❌ WebSocket连接异常: {e}", exc_info=True)
            return False
    
    async def close_connection(self):
        """关闭连接"""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
            logger.info("🔒 WebSocket连接已关闭")
    
    async def run_test(self):
        """运行测试"""
        logger.info("🚀 开始最终连接测试...")
        
        try:
            # 1. 登录
            if not await self.login():
                logger.error("❌ 登录失败")
                return False
                
            # 2. 测试WebSocket连接
            success = await self.test_websocket_connection()
            
            # 3. 关闭连接
            await self.close_connection()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 测试执行异常: {e}", exc_info=True)
            await self.close_connection()
            return False

async def main():
    """主函数"""
    test = FinalConnectionTest()
    
    try:
        success = await test.run_test()
        
        if success:
            logger.info("🎉 最终连接测试成功!")
            return 0
        else:
            logger.warning("⚠️  最终连接测试失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"❌ 测试执行异常: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    import sys
    result = asyncio.run(main())
    sys.exit(result)