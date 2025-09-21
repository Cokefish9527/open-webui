"""
工作流场景测试脚本
用于模拟前端在不同场景下通过服务端向n8n工作流发送消息的完整流程测试

测试覆盖：
1. 企业信息收集工作流
2. 视频创作工作流  
3. 视频分析工作流
4. 工作流编排中心(WOC)功能测试
"""

import asyncio
import json
import time
import requests
import websockets
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestMode(Enum):
    """测试模式"""
    QUICK = "quick"  # 快速测试
    FULL = "full"    # 完整工作流测试
    COMPANY_INFO = "company_info"  # 企业信息收集专项测试
    VIDEO_CREATION = "video_creation"  # 视频创作专项测试
    VIDEO_CRAWL = "video_crawl"  # 视频分析专项测试
    WOC_MANAGEMENT = "woc_management"  # WOC管理功能测试

@dataclass
class TestConfig:
    """测试配置"""
    base_url: str = "http://localhost:8080"
    websocket_url: str = "ws://localhost:8080/hsai/ws"
    username: str = "saiter2306@163.com"
    password: str = "123456"
    timeout: int = 30
    debug: bool = True

class WorkflowTester:
    """工作流测试器"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session = requests.Session()
        
    async def login(self) -> bool:
        """用户登录获取token"""
        try:
            logger.info("🔐 开始用户登录...")
            
            login_data = {
                "email": self.config.username,
                "password": self.config.password
            }
            
            response = self.session.post(
                f"{self.config.base_url}/api/v1/auths/signin",
                json=login_data,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                self.token = result.get("token")
                self.user_id = result.get("id")
                
                # 设置请求头
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                })
                
                logger.info(f"✅ 登录成功！用户ID: {self.user_id}")
                return True
            else:
                logger.error(f"❌ 登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 登录异常: {e}")
            return False
    
    def test_woc_health(self) -> bool:
        """测试WOC健康状态"""
        try:
            logger.info("🏥 测试WOC健康状态...")
            
            response = self.session.get(
                f"{self.config.base_url}/api/v1/woc/health",
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✅ WOC健康检查通过: {health_data}")
                return True
            else:
                logger.error(f"❌ WOC健康检查失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ WOC健康检查异常: {e}")
            return False
    
    def test_woc_status(self) -> bool:
        """测试WOC状态查询"""
        try:
            logger.info("📊 测试WOC状态查询...")
            
            response = self.session.get(
                f"{self.config.base_url}/api/v1/woc/status",
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                status_data = response.json()
                logger.info(f"✅ WOC状态查询成功: {status_data}")
                return True
            else:
                logger.error(f"❌ WOC状态查询失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ WOC状态查询异常: {e}")
            return False
    
    async def test_websocket_workflow(self, message_data: Dict[str, Any], test_name: str) -> bool:
        """通过WebSocket测试工作流"""
        try:
            logger.info(f"🌐 开始WebSocket工作流测试: {test_name}")
            
            # 构建WebSocket URL（使用正确的路由格式）
            ws_url = f"ws://localhost:8080/hsai/ws/{self.user_id}?token={self.token}"
            
            # 使用websockets库连接（移除timeout参数）
            async with websockets.connect(ws_url) as websocket:
                logger.info("✅ WebSocket连接成功")
                
                # 发送消息
                message_json = json.dumps(message_data, ensure_ascii=False)
                logger.info(f"📤 发送消息: {message_json}")
                await websocket.send(message_json)
                
                # 等待响应
                start_time = time.time()
                responses = []
                
                while time.time() - start_time < self.config.timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        responses.append(response_data)
                        
                        logger.info(f"📥 收到响应: {response_data}")
                        
                        # 检查是否为最终响应
                        if response_data.get("type") == "workflow_response":
                            if response_data.get("success"):
                                logger.info(f"✅ {test_name} 工作流测试成功")
                                return True
                            else:
                                logger.error(f"❌ {test_name} 工作流执行失败: {response_data.get('error_message')}")
                                return False
                                
                    except asyncio.TimeoutError:
                        logger.info("⏳ 等待响应中...")
                        continue
                    except Exception as e:
                        logger.error(f"❌ 接收响应异常: {e}")
                        break
                
                logger.error(f"⏰ {test_name} 测试超时")
                return False
                
        except Exception as e:
            logger.error(f"❌ WebSocket工作流测试异常: {e}")
            return False
    
    async def test_company_info_workflow(self) -> bool:
        """测试企业信息收集工作流"""
        logger.info("🏢 开始企业信息收集工作流测试...")
        
        message_data = {
            "type": "chat",
            "content": "帮我收集和分析阿里巴巴集团的企业信息，包括公司背景、业务结构、竞争对手分析等",
            "user_id": self.user_id,
            "entry_type": "company",
            "session_id": f"test_company_{int(time.time())}",
            "metadata": {
                "test_scenario": "company_info_collection",
                "company_name": "阿里巴巴集团"
            }
        }
        
        return await self.test_websocket_workflow(message_data, "企业信息收集")
    
    async def test_video_creation_workflow(self) -> bool:
        """测试视频创作工作流"""
        logger.info("🎬 开始视频创作工作流测试...")
        
        message_data = {
            "type": "chat", 
            "content": "帮我创作一个关于人工智能发展趋势的短视频，包括脚本撰写、关键词优化和发布建议",
            "user_id": self.user_id,
            "entry_type": "chat",
            "session_id": f"test_video_{int(time.time())}",
            "metadata": {
                "test_scenario": "video_creation",
                "video_topic": "人工智能发展趋势",
                "target_platform": "抖音"
            }
        }
        
        return await self.test_websocket_workflow(message_data, "视频创作")
    
    async def test_video_analysis_workflow(self) -> bool:
        """测试视频分析工作流"""
        logger.info("📹 开始视频分析工作流测试...")
        
        message_data = {
            "type": "chat",
            "content": "帮我分析最近抖音上关于科技类视频的热门内容和关键词趋势",
            "user_id": self.user_id,
            "entry_type": "chat", 
            "session_id": f"test_analysis_{int(time.time())}",
            "metadata": {
                "test_scenario": "video_analysis",
                "platform": "抖音",
                "category": "科技"
            }
        }
        
        return await self.test_websocket_workflow(message_data, "视频分析")
    
    async def test_workflow_trigger_direct(self) -> bool:
        """测试直接工作流触发"""
        logger.info("⚡ 开始直接工作流触发测试...")
        
        message_data = {
            "type": "workflow_trigger",
            "content": "测试主工作流直接触发功能",
            "user_id": self.user_id,
            "workflow_type": "main",
            "session_id": f"test_direct_{int(time.time())}",
            "metadata": {
                "test_scenario": "direct_trigger"
            }
        }
        
        return await self.test_websocket_workflow(message_data, "直接工作流触发")
    
    def test_user_executions(self) -> bool:
        """测试用户执行列表查询"""
        try:
            logger.info("📋 测试用户执行列表查询...")
            
            response = self.session.get(
                f"{self.config.base_url}/api/v1/woc/executions/user?limit=5",
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                executions_data = response.json()
                logger.info(f"✅ 用户执行列表查询成功: 共{executions_data.get('total', 0)}条记录")
                
                if self.config.debug:
                    for execution in executions_data.get('executions', [])[:3]:
                        logger.info(f"   📝 执行记录: {execution.get('execution_id')} - {execution.get('status')}")
                        
                return True
            else:
                logger.error(f"❌ 用户执行列表查询失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 用户执行列表查询异常: {e}")
            return False
    
    async def run_test_mode(self, mode: TestMode) -> Dict[str, bool]:
        """运行指定的测试模式"""
        results = {}
        
        logger.info(f"🚀 开始运行测试模式: {mode.value}")
        
        # 登录
        if not await self.login():
            return {"login": False}
        results["login"] = True
        
        if mode == TestMode.QUICK:
            # 快速测试：基本功能验证
            results["woc_health"] = self.test_woc_health()
            results["woc_status"] = self.test_woc_status()
            results["company_info"] = await self.test_company_info_workflow()
            
        elif mode == TestMode.FULL:
            # 完整测试：所有功能验证
            results["woc_health"] = self.test_woc_health()
            results["woc_status"] = self.test_woc_status()
            results["company_info"] = await self.test_company_info_workflow()
            results["video_creation"] = await self.test_video_creation_workflow()
            results["video_analysis"] = await self.test_video_analysis_workflow()
            results["direct_trigger"] = await self.test_workflow_trigger_direct()
            results["user_executions"] = self.test_user_executions()
            
        elif mode == TestMode.COMPANY_INFO:
            # 企业信息收集专项测试
            results["woc_health"] = self.test_woc_health()
            results["company_info"] = await self.test_company_info_workflow()
            
        elif mode == TestMode.VIDEO_CREATION:
            # 视频创作专项测试
            results["woc_health"] = self.test_woc_health()
            results["video_creation"] = await self.test_video_creation_workflow()
            
        elif mode == TestMode.VIDEO_CRAWL:
            # 视频分析专项测试
            results["woc_health"] = self.test_woc_health()
            results["video_analysis"] = await self.test_video_analysis_workflow()
            
        elif mode == TestMode.WOC_MANAGEMENT:
            # WOC管理功能专项测试
            results["woc_health"] = self.test_woc_health()
            results["woc_status"] = self.test_woc_status()
            results["user_executions"] = self.test_user_executions()
        
        return results
    
    def print_test_summary(self, results: Dict[str, bool]):
        """打印测试总结"""
        logger.info("\n" + "="*60)
        logger.info("📊 测试结果总结")
        logger.info("="*60)
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result)
        failed_tests = total_tests - passed_tests
        
        for test_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"   {test_name}: {status}")
        
        logger.info("-"*60)
        logger.info(f"总计: {total_tests} 项测试")
        logger.info(f"通过: {passed_tests} 项")
        logger.info(f"失败: {failed_tests} 项")
        logger.info(f"成功率: {passed_tests/total_tests*100:.1f}%")
        logger.info("="*60)

def print_usage():
    """打印使用说明"""
    print("""
🔧 工作流场景测试脚本使用说明
================================

测试模式：
  quick         - 快速测试（基本功能验证）
  full          - 完整测试（所有功能验证）  
  company_info  - 企业信息收集专项测试
  video_creation - 视频创作专项测试
  video_analysis - 视频分析专项测试
  woc_management - WOC管理功能专项测试

使用示例：
  python test_workflow_scenarios.py quick
  python test_workflow_scenarios.py full
  python test_workflow_scenarios.py company_info

配置说明：
  - 默认服务器地址: http://localhost:8080
  - 默认用户名: admin@localhost
  - 默认密码: admin
  - 超时时间: 30秒
  
注意事项：
  1. 确保服务器正在运行
  2. 确保WOC工作流编排中心已启用
  3. 确保n8n工作流服务可用
  4. 测试用户需要有相应权限
""")

async def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print_usage()
        return
    
    mode_str = sys.argv[1].lower()
    
    try:
        mode = TestMode(mode_str)
    except ValueError:
        print(f"❌ 无效的测试模式: {mode_str}")
        print_usage()
        return
    
    # 创建测试配置
    config = TestConfig()
    
    # 创建测试器并运行测试
    tester = WorkflowTester(config)
    
    try:
        results = await tester.run_test_mode(mode)
        tester.print_test_summary(results)
        
        # 如果有失败的测试，以非零状态码退出
        if not all(results.values()):
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 测试执行异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())