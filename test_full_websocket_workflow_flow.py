#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的WebSocket工作流端到端测试脚本

测试流程:
1. 建立WebSocket连接
2. 发送消息到服务端
3. 服务端接收消息并路由到对应工作流
4. 服务端向工作流发送请求
5. 工作流处理并返回响应
6. 服务端结构化处理响应并返回给客户端
"""

import asyncio
import json
import websockets
import jwt
import time
import logging
from typing import Dict, Any
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_websocket_workflow_test.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 测试配置
SERVER_URL = "ws://localhost:8080/ws/hsai/ws"
USER_ID = "test_user_123"
# 注意：这里使用生成的测试JWT token
TEST_JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3RfdXNlcl8xMjMiLCJuYW1lIjoiVGVzdCBVc2VyIiwiZW1haWwiOiJ0ZXN0X3VzZXJfMTIzQHRlc3QuY29tIiwicm9sZSI6InVzZXIiLCJleHAiOjE3NTcwMjEzNTMsImlhdCI6MTc1NzAxNzc1M30.hq3Tpekr1TAqVR5oVyfJQMV_7tcI235D5xHf4GI2Duc"

class WebSocketWorkflowTester:
    def __init__(self, server_url: str, user_id: str, token: str):
        self.server_url = server_url
        self.user_id = user_id
        self.token = token
        self.websocket = None
        self.received_messages = []
        
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            # 构建连接URL
            url = f"{self.server_url}/{self.user_id}?token={self.token}"
            logger.info(f"尝试连接到: {url}")
            
            # 建立连接
            self.websocket = await websockets.connect(url)
            logger.info("✅ WebSocket连接建立成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ WebSocket连接失败: {e}")
            return False
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """发送消息"""
        try:
            message_json = json.dumps(message, ensure_ascii=False)
            await self.websocket.send(message_json)
            logger.info(f"📤 消息发送成功: {message}")
            return True
        except Exception as e:
            logger.error(f"❌ 消息发送失败: {e}")
            return False
    
    async def receive_messages(self, timeout: int = 30):
        """接收消息"""
        try:
            while True:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
                message_data = json.loads(message)
                self.received_messages.append(message_data)
                logger.info(f"📥 收到消息: {message_data}")
                
                # 检查是否是最终响应
                if self._is_final_response(message_data):
                    logger.info("✅ 收到最终响应，测试完成")
                    break
                    
        except asyncio.TimeoutError:
            logger.warning(f"⏳ 等待消息超时 ({timeout}秒)")
        except Exception as e:
            logger.error(f"❌ 接收消息时出错: {e}")
    
    def _is_final_response(self, message: Dict[str, Any]) -> bool:
        """判断是否为最终响应"""
        # 根据对接文档，最终响应应该包含success字段
        return "success" in message and "displayText" in message
    
    async def test_main_workflow(self):
        """测试主工作流"""
        logger.info("🚀 开始测试主工作流...")
        
        # 构造测试消息
        test_message = {
            "type": "chat",
            "content": "你好",
            "user_id": self.user_id,
            "entry_type": "chat",  # 指定入口类型为聊天
            "metadata": {
                "test_case": "main_workflow",
                "timestamp": time.time()
            }
        }
        
        # 发送消息
        if await self.send_message(test_message):
            logger.info("✅ 主工作流消息发送成功")
            # 等待接收响应
            await self.receive_messages(timeout=30)
        else:
            logger.error("❌ 主工作流消息发送失败")
    
    async def test_company_info_workflow(self):
        """测试公司信息收集工作流"""
        logger.info("🚀 开始测试公司信息收集工作流...")
        
        # 构造测试消息
        test_message = {
            "type": "chat",
            "content": "我想了解一些公司信息",
            "user_id": self.user_id,
            "entry_type": "company",  # 指定入口类型为公司信息
            "metadata": {
                "test_case": "company_info_workflow",
                "timestamp": time.time()
            }
        }
        
        # 发送消息
        if await self.send_message(test_message):
            logger.info("✅ 公司信息收集工作流消息发送成功")
            # 等待接收响应
            await self.receive_messages(timeout=60)  # 公司信息收集可能需要更长时间
        else:
            logger.error("❌ 公司信息收集工作流消息发送失败")
    
    async def run_test_sequence(self):
        """运行测试序列"""
        logger.info("🚀 启动完整的WebSocket工作流端到端测试")
        
        # 1. 建立连接
        if not await self.connect():
            logger.error("❌ 无法建立WebSocket连接，测试终止")
            return
        
        try:
            # 2. 测试主工作流
            await self.test_main_workflow()
            
            # 等待一段时间再进行下一个测试
            await asyncio.sleep(2)
            
            # 3. 测试公司信息收集工作流
            await self.test_company_info_workflow()
            
        except Exception as e:
            logger.error(f"❌ 测试过程中发生错误: {e}")
        finally:
            # 关闭连接
            if self.websocket:
                await self.websocket.close()
                logger.info("🔒 WebSocket连接已关闭")
            
            # 输出测试结果摘要
            self._print_test_summary()
    
    def _print_test_summary(self):
        """打印测试结果摘要"""
        logger.info("=" * 50)
        logger.info("📊 测试结果摘要")
        logger.info("=" * 50)
        logger.info(f"总共收到 {len(self.received_messages)} 条消息")
        
        for i, msg in enumerate(self.received_messages):
            logger.info(f"消息 {i+1}: {json.dumps(msg, ensure_ascii=False, indent=2)}")
        
        # 检查关键节点
        self._check_key_nodes()
    
    def _check_key_nodes(self):
        """检查关键节点"""
        logger.info("-" * 30)
        logger.info("🔍 关键节点检查")
        logger.info("-" * 30)
        
        # 1. 检查连接建立
        connection_established = any(
            "连接成功" in str(msg) or msg.get("type") == "status" 
            for msg in self.received_messages
        )
        logger.info(f"1. WebSocket连接建立: {'✅ 成功' if connection_established else '❌ 失败'}")
        
        # 2. 检查消息接收和路由
        message_routed = any(
            "user_id" in msg and "content" in str(msg)
            for msg in self.received_messages
        )
        logger.info(f"2. 消息接收和路由: {'✅ 成功' if message_routed else '❌ 失败'}")
        
        # 3. 检查结构化响应
        structured_response = any(
            "success" in msg and "displayText" in msg
            for msg in self.received_messages
        )
        logger.info(f"3. 结构化响应处理: {'✅ 成功' if structured_response else '❌ 失败'}")
        
        overall_success = connection_established and message_routed and structured_response
        logger.info(f"\n🎯 整体测试结果: {'✅ 通过' if overall_success else '❌ 失败'}")

async def main():
    """主函数"""
    # 注意：您需要替换为实际的有效JWT token
    tester = WebSocketWorkflowTester(
        server_url=SERVER_URL,
        user_id=USER_ID,
        token=TEST_JWT_TOKEN
    )
    
    await tester.run_test_sequence()

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())