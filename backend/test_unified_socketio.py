#!/usr/bin/env python3
"""
测试统一Socket.IO集成
验证HSAI功能是否正确集成到OpenWebUI原生Socket.IO中
"""

import asyncio
import socketio
import json
import jwt
import time
import logging
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试配置
TEST_CONFIG = {
    "server_url": "http://localhost:8080",
    "socket_path": "/ws/socket.io",
    "test_user": {
        "id": "test_user_123",
        "name": "Test User",
        "email": "test@example.com",
        "role": "user"
    },
    "jwt_secret": "your-secret-key-here",  # 需要与服务端配置一致
    "timeout": 30
}

class UnifiedSocketIOTester:
    """统一Socket.IO集成测试器"""
    
    def __init__(self):
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.responses = []
        
    def generate_test_token(self):
        """生成测试JWT令牌"""
        payload = {
            "id": TEST_CONFIG["test_user"]["id"],
            "name": TEST_CONFIG["test_user"]["name"],
            "email": TEST_CONFIG["test_user"]["email"],
            "role": TEST_CONFIG["test_user"]["role"],
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        token = jwt.encode(payload, TEST_CONFIG["jwt_secret"], algorithm="HS256")
        return token
        
    async def setup_event_handlers(self):
        """设置事件处理器"""
        
        @self.sio.event
        async def connect():
            self.connected = True
            logger.info("✓ Socket.IO连接建立成功")
            
        @self.sio.event
        async def disconnect():
            self.connected = False
            logger.info("× Socket.IO连接已断开")
            
        @self.sio.event
        async def connect_error(data):
            logger.error(f"× Socket.IO连接错误: {data}")
            
        # HSAI核心事件（合并后的工作流事件）
        @self.sio.on('hsai_response')
        async def hsai_response(data):
            logger.info(f"✓ 收到HSAI响应: {data}")
            # 检查是否为工作流事件
            event_type = data.get('type', '')
            if event_type in ['workflow_started', 'workflow_progress', 'workflow_completed', 'status_response']:
                logger.info(f"🚀 工作流事件: {event_type} - {data}")
            self.responses.append(('hsai_response', data))
            
        @self.sio.on('hsai_error')
        async def hsai_error(data):
            logger.error(f"× 收到HSAI错误: {data}")
            # 检查是否为工作流失败事件
            event_type = data.get('type', '')
            if event_type in ['workflow_failed', 'workflow_error']:
                logger.error(f"❌ 工作流失败: {data}")
            self.responses.append(('hsai_error', data))
            

            
        logger.info("事件处理器设置完成")
        
    async def connect_to_server(self):
        """连接到Socket.IO服务器"""
        try:
            token = self.generate_test_token()
            logger.info(f"生成测试令牌: {token[:20]}...")
            
            # 使用auth参数传递令牌
            await self.sio.connect(
                TEST_CONFIG["server_url"],
                socketio_path=TEST_CONFIG["socket_path"],
                auth={"token": token},
                transports=['websocket', 'polling'],
                wait_timeout=10
            )
            
            # 等待连接建立
            await asyncio.sleep(2)
            
            if self.connected:
                logger.info("✓ Socket.IO连接验证成功")
                return True
            else:
                logger.error("× Socket.IO连接验证失败")
                return False
                
        except Exception as e:
            logger.error(f"× Socket.IO连接失败: {e}")
            return False
            
    async def test_hsai_message(self, message_data):
        """测试HSAI消息发送"""
        try:
            logger.info(f"发送HSAI消息: {message_data}")
            await self.sio.emit('hsai_message', message_data)
            
            # 等待响应
            start_time = time.time()
            while time.time() - start_time < TEST_CONFIG["timeout"]:
                if self.responses:
                    break
                await asyncio.sleep(0.5)
                
            if self.responses:
                logger.info(f"✓ 消息测试成功，收到 {len(self.responses)} 个响应")
                return True
            else:
                logger.warning("⚠ 消息测试超时，未收到响应")
                return False
                
        except Exception as e:
            logger.error(f"× HSAI消息测试失败: {e}")
            return False
            
    async def test_status_query(self):
        """测试状态查询"""
        try:
            logger.info("发送状态查询")
            await self.sio.emit('hsai_status', {})
            
            # 等待状态响应
            start_time = time.time()
            status_received = False
            
            while time.time() - start_time < 10:
                for event_type, data in self.responses:
                    # 现在状态响应也使用hsai_response事件，通过type字段区分
                    if event_type == 'hsai_response' and isinstance(data, dict) and data.get('type') == 'status_response':
                        status_received = True
                        break
                if status_received:
                    break
                await asyncio.sleep(0.5)
                
            if status_received:
                logger.info("✓ 状态查询测试成功")
                return True
            else:
                logger.warning("⚠ 状态查询测试超时")
                return False
                
        except Exception as e:
            logger.error(f"× 状态查询测试失败: {e}")
            return False
            
    async def run_comprehensive_test(self):
        """运行综合测试"""
        logger.info("="*60)
        logger.info("开始统一Socket.IO集成综合测试")
        logger.info("="*60)
        
        # 设置事件处理器
        await self.setup_event_handlers()
        
        # 1. 连接测试
        logger.info("\n[1/4] Socket.IO连接测试")
        if not await self.connect_to_server():
            logger.error("连接测试失败，终止测试")
            return False
            
        # 2. 简单消息测试
        logger.info("\n[2/4] 简单消息测试")
        self.responses.clear()
        simple_message = {
            "content": "你好，这是一个测试消息",
            "user_id": TEST_CONFIG["test_user"]["id"],
            "session_id": f"test_session_{int(time.time())}"
        }
        
        simple_test_result = await self.test_hsai_message(simple_message)
        
        # 3. 复杂消息测试（指定工作流类型）
        logger.info("\n[3/4] 指定工作流类型测试")
        self.responses.clear()
        workflow_message = {
            "content": "请分析这家公司的信息",
            "user_id": TEST_CONFIG["test_user"]["id"],
            "session_id": f"test_session_{int(time.time())}",
            "workflow_type": "company_info",
            "business_name": "测试公司",
            "metadata": {
                "test_mode": True
            }
        }
        
        workflow_test_result = await self.test_hsai_message(workflow_message)
        
        # 4. 状态查询测试
        logger.info("\n[4/4] 状态查询测试")
        self.responses.clear()
        status_test_result = await self.test_status_query()
        
        # 汇总结果
        logger.info("\n" + "="*60)
        logger.info("测试结果汇总")
        logger.info("="*60)
        logger.info(f"Socket.IO连接: {'✓ 成功' if True else '× 失败'}")
        logger.info(f"简单消息测试: {'✓ 成功' if simple_test_result else '× 失败'}")
        logger.info(f"工作流消息测试: {'✓ 成功' if workflow_test_result else '× 失败'}")
        logger.info(f"状态查询测试: {'✓ 成功' if status_test_result else '× 失败'}")
        
        # 总体评估
        total_tests = 4
        passed_tests = sum([
            True,  # 连接成功
            simple_test_result,
            workflow_test_result,
            status_test_result
        ])
        
        success_rate = passed_tests / total_tests * 100
        logger.info(f"\n总体成功率: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        if success_rate >= 75:
            logger.info("🎉 统一Socket.IO集成测试整体成功！")
            return True
        else:
            logger.error("😞 统一Socket.IO集成测试存在问题，需要检查")
            return False
            
    async def cleanup(self):
        """清理资源"""
        try:
            if self.connected:
                await self.sio.disconnect()
            logger.info("资源清理完成")
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")

async def main():
    """主函数"""
    tester = UnifiedSocketIOTester()
    
    try:
        # 运行综合测试
        success = await tester.run_comprehensive_test()
        
        # 等待一下让日志输出完整
        await asyncio.sleep(1)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"测试过程中发生未预期错误: {e}")
        return 1
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    # 运行测试
    exit_code = asyncio.run(main())
    exit(exit_code)