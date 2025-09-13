"""
增强版工作流场景测试脚本
支持配置文件、详细测试报告和多种测试策略

新增功能：
1. 配置文件支持
2. 详细的测试报告生成
3. 多个测试场景的数据驱动测试
4. 测试结果验证
5. 性能监控
"""

import asyncio
import json
import time
import requests
import websockets
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'workflow_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class TestResult(Enum):
    """测试结果枚举"""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"

@dataclass
class TestCase:
    """测试用例"""
    name: str
    description: str
    test_function: str
    expected_result: Dict[str, Any]
    timeout: int = 30
    retry_count: int = 1

@dataclass 
class TestReport:
    """测试报告"""
    test_name: str
    result: TestResult
    start_time: datetime
    end_time: datetime
    duration: float
    message: str
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "result": self.result.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration,
            "message": self.message,
            "details": self.details or {}
        }

class EnhancedWorkflowTester:
    """增强版工作流测试器"""
    
    def __init__(self, config_file: str = "test_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session = requests.Session()
        self.test_reports: List[TestReport] = []
        
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            config_path = Path(self.config_file)
            if not config_path.exists():
                logger.warning(f"配置文件 {self.config_file} 不存在，使用默认配置")
                return self.get_default_config()
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"✅ 成功加载配置文件: {self.config_file}")
                return config
                
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "test_config": {
                "base_url": "http://localhost:8080",
                "websocket_url": "ws://localhost:8080/hsai/ws",
                "username": "admin@localhost",
                "password": "admin",
                "timeout": 30,
                "debug": True
            }
        }
    
    async def run_test_case(self, test_case: TestCase) -> TestReport:
        """运行单个测试用例"""
        start_time = datetime.now()
        
        try:
            logger.info(f"🧪 开始执行测试: {test_case.name}")
            
            # 通过反射调用测试方法
            test_method = getattr(self, test_case.test_function)
            
            # 执行测试（支持重试）
            for attempt in range(test_case.retry_count):
                try:
                    if attempt > 0:
                        logger.info(f"🔄 第 {attempt + 1} 次重试: {test_case.name}")
                        await asyncio.sleep(2)  # 重试前等待
                    
                    result = await test_method()
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    if result:
                        return TestReport(
                            test_name=test_case.name,
                            result=TestResult.PASSED,
                            start_time=start_time,
                            end_time=end_time,
                            duration=duration,
                            message="测试通过",
                            details={"attempts": attempt + 1}
                        )
                    else:
                        if attempt == test_case.retry_count - 1:  # 最后一次尝试
                            return TestReport(
                                test_name=test_case.name,
                                result=TestResult.FAILED,
                                start_time=start_time,
                                end_time=end_time,
                                duration=duration,
                                message="测试失败",
                                details={"attempts": attempt + 1}
                            )
                        
                except Exception as e:
                    if attempt == test_case.retry_count - 1:  # 最后一次尝试
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        
                        return TestReport(
                            test_name=test_case.name,
                            result=TestResult.ERROR,
                            start_time=start_time,
                            end_time=end_time,
                            duration=duration,
                            message=f"测试异常: {str(e)}",
                            details={"attempts": attempt + 1, "error": str(e)}
                        )
                        
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return TestReport(
                test_name=test_case.name,
                result=TestResult.ERROR,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                message=f"测试执行异常: {str(e)}",
                details={"error": str(e)}
            )
    
    async def login(self) -> bool:
        """用户登录"""
        try:
            logger.info("🔐 开始用户登录...")
            
            config = self.config["test_config"]
            login_data = {
                "email": config["username"],
                "password": config["password"]
            }
            
            response = self.session.post(
                f"{config['base_url']}/api/v1/auths/signin",
                json=login_data,
                timeout=config["timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                self.token = result.get("token")
                self.user_id = result.get("id")
                
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
    
    async def test_woc_health_check(self) -> bool:
        """测试WOC健康检查"""
        try:
            config = self.config["test_config"]
            response = self.session.get(
                f"{config['base_url']}/api/v1/woc/health",
                timeout=config["timeout"]
            )
            
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✅ WOC健康检查通过: {health_data.get('status')}")
                return health_data.get("status") == "healthy"
            else:
                logger.error(f"❌ WOC健康检查失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ WOC健康检查异常: {e}")
            return False
    
    async def test_company_info_scenario(self) -> bool:
        """测试企业信息收集场景"""
        scenario = self.config.get("test_scenarios", {}).get("company_info", {})
        test_data = self.config.get("test_data", {})
        
        # 随机选择一个公司进行测试
        companies = test_data.get("companies", ["阿里巴巴集团"])
        company = random.choice(companies)
        
        message_data = {
            "type": "chat",
            "content": scenario.get("content", "").replace("阿里巴巴集团", company),
            "user_id": self.user_id,
            "entry_type": scenario.get("entry_type", "company"),
            "session_id": f"test_company_{int(time.time())}",
            "metadata": {
                **scenario.get("metadata", {}),
                "company_name": company,
                "test_timestamp": datetime.now().isoformat()
            }
        }
        
        return await self.test_websocket_workflow(
            message_data, 
            f"企业信息收集 - {company}"
        )
    
    async def test_video_creation_scenario(self) -> bool:
        """测试视频创作场景"""
        scenario = self.config.get("test_scenarios", {}).get("video_creation", {})
        test_data = self.config.get("test_data", {})
        
        # 随机选择主题和平台
        topics = test_data.get("video_topics", ["人工智能发展趋势"])
        platforms = test_data.get("platforms", ["抖音"])
        
        topic = random.choice(topics)
        platform = random.choice(platforms)
        
        message_data = {
            "type": "chat",
            "content": scenario.get("content", "").replace("人工智能发展趋势", topic),
            "user_id": self.user_id,
            "entry_type": scenario.get("entry_type", "chat"),
            "session_id": f"test_video_{int(time.time())}",
            "metadata": {
                **scenario.get("metadata", {}),
                "video_topic": topic,
                "target_platform": platform,
                "test_timestamp": datetime.now().isoformat()
            }
        }
        
        return await self.test_websocket_workflow(
            message_data,
            f"视频创作 - {topic} ({platform})"
        )
    
    async def test_video_analysis_scenario(self) -> bool:
        """测试视频分析场景"""
        scenario = self.config.get("test_scenarios", {}).get("video_analysis", {})
        test_data = self.config.get("test_data", {})
        
        platforms = test_data.get("platforms", ["抖音"])
        platform = random.choice(platforms)
        
        message_data = {
            "type": "chat",
            "content": scenario.get("content", "").replace("抖音", platform),
            "user_id": self.user_id,
            "entry_type": scenario.get("entry_type", "chat"),
            "session_id": f"test_analysis_{int(time.time())}",
            "metadata": {
                **scenario.get("metadata", {}),
                "platform": platform,
                "test_timestamp": datetime.now().isoformat()
            }
        }
        
        return await self.test_websocket_workflow(
            message_data,
            f"视频分析 - {platform}"
        )
    
    async def test_websocket_workflow(self, message_data: Dict[str, Any], test_name: str) -> bool:
        """通过WebSocket测试工作流"""
        try:
            config = self.config["test_config"]
            # 使用正确的WebSocket URL格式
            ws_url = f"ws://localhost:8080/hsai/ws/{self.user_id}?token={self.token}"
            
            logger.info(f"🌐 开始WebSocket工作流测试: {test_name}")
            
            # 移除timeout参数，使用默认连接设置
            async with websockets.connect(ws_url) as websocket:
                # 发送消息
                message_json = json.dumps(message_data, ensure_ascii=False)
                if config.get("debug"):
                    logger.info(f"📤 发送消息: {message_json}")
                await websocket.send(message_json)
                
                # 等待响应
                start_time = time.time()
                responses = []
                
                while time.time() - start_time < config["timeout"]:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        responses.append(response_data)
                        
                        if config.get("debug"):
                            logger.info(f"📥 收到响应: {response_data.get('type', 'unknown')}")
                        
                        # 检查最终响应
                        if response_data.get("type") == "workflow_response":
                            success = response_data.get("success", False)
                            if success:
                                logger.info(f"✅ {test_name} 工作流测试成功")
                                return True
                            else:
                                error_msg = response_data.get("error_message", "未知错误")
                                logger.error(f"❌ {test_name} 工作流执行失败: {error_msg}")
                                return False
                        
                        # 检查错误响应
                        if response_data.get("type") == "error":
                            logger.error(f"❌ {test_name} 收到错误响应: {response_data.get('content')}")
                            return False
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"❌ 接收响应异常: {e}")
                        return False
                
                logger.error(f"⏰ {test_name} 测试超时")
                return False
                
        except Exception as e:
            logger.error(f"❌ WebSocket工作流测试异常: {e}")
            return False
    
    async def run_comprehensive_test(self) -> List[TestReport]:
        """运行综合测试"""
        logger.info("🚀 开始运行综合工作流测试...")
        
        # 定义测试用例
        test_cases = [
            TestCase(
                name="用户登录",
                description="验证用户认证功能",
                test_function="login",
                expected_result={"success": True},
                retry_count=2
            ),
            TestCase(
                name="WOC健康检查",
                description="验证工作流编排中心健康状态",
                test_function="test_woc_health_check",
                expected_result={"status": "healthy"},
                retry_count=1
            ),
            TestCase(
                name="企业信息收集场景",
                description="测试企业信息收集工作流场景",
                test_function="test_company_info_scenario",
                expected_result={"success": True},
                timeout=60,
                retry_count=2
            ),
            TestCase(
                name="视频创作场景",
                description="测试视频创作工作流场景",
                test_function="test_video_creation_scenario",
                expected_result={"success": True},
                timeout=60,
                retry_count=2
            ),
            TestCase(
                name="视频分析场景",
                description="测试视频分析工作流场景", 
                test_function="test_video_analysis_scenario",
                expected_result={"success": True},
                timeout=60,
                retry_count=2
            )
        ]
        
        # 执行测试用例
        for test_case in test_cases:
            report = await self.run_test_case(test_case)
            self.test_reports.append(report)
            
            # 如果登录失败，跳过后续测试
            if test_case.name == "用户登录" and report.result != TestResult.PASSED:
                logger.error("❌ 登录失败，跳过后续测试")
                break
                
            # 测试之间的间隔
            await asyncio.sleep(1)
        
        return self.test_reports
    
    def generate_test_report(self):
        """生成测试报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"workflow_test_report_{timestamp}.json"
        
        # 统计信息
        total_tests = len(self.test_reports)
        passed_tests = sum(1 for r in self.test_reports if r.result == TestResult.PASSED)
        failed_tests = sum(1 for r in self.test_reports if r.result == TestResult.FAILED)
        error_tests = sum(1 for r in self.test_reports if r.result == TestResult.ERROR)
        
        # 生成报告
        report_data = {
            "test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "error_tests": error_tests,
                "success_rate": round(passed_tests / total_tests * 100, 2) if total_tests > 0 else 0,
                "total_duration": round(sum(r.duration for r in self.test_reports), 2)
            },
            "test_details": [report.to_dict() for report in self.test_reports],
            "config": self.config
        }
        
        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 测试报告已生成: {report_file}")
        
        # 打印总结
        self.print_test_summary()
        
        return report_file
    
    def print_test_summary(self):
        """打印测试总结"""
        logger.info("\n" + "="*70)
        logger.info("📊 工作流场景测试结果总结")
        logger.info("="*70)
        
        total_tests = len(self.test_reports)
        passed_tests = sum(1 for r in self.test_reports if r.result == TestResult.PASSED)
        failed_tests = sum(1 for r in self.test_reports if r.result == TestResult.FAILED)
        error_tests = sum(1 for r in self.test_reports if r.result == TestResult.ERROR)
        
        for report in self.test_reports:
            status_icon = {
                TestResult.PASSED: "✅",
                TestResult.FAILED: "❌", 
                TestResult.ERROR: "⚠️",
                TestResult.SKIPPED: "⏭️"
            }.get(report.result, "❓")
            
            logger.info(f"   {status_icon} {report.test_name}: {report.result.value} ({report.duration:.2f}s)")
            if report.result != TestResult.PASSED and report.message:
                logger.info(f"      💬 {report.message}")
        
        logger.info("-"*70)
        logger.info(f"📈 总计: {total_tests} 项测试")
        logger.info(f"✅ 通过: {passed_tests} 项")
        logger.info(f"❌ 失败: {failed_tests} 项")
        logger.info(f"⚠️  错误: {error_tests} 项")
        
        if total_tests > 0:
            success_rate = passed_tests / total_tests * 100
            logger.info(f"📊 成功率: {success_rate:.1f}%")
            total_duration = sum(r.duration for r in self.test_reports)
            logger.info(f"⏱️  总耗时: {total_duration:.2f}秒")
        
        logger.info("="*70)

async def main():
    """主函数"""
    import sys
    
    config_file = "test_config.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    logger.info(f"🎯 启动增强版工作流场景测试 (配置: {config_file})")
    
    try:
        tester = EnhancedWorkflowTester(config_file)
        await tester.run_comprehensive_test()
        tester.generate_test_report()
        
        # 检查是否有失败的测试
        failed_count = sum(1 for r in tester.test_reports 
                          if r.result in [TestResult.FAILED, TestResult.ERROR])
        
        if failed_count > 0:
            logger.warning(f"⚠️ 发现 {failed_count} 个失败的测试")
            sys.exit(1)
        else:
            logger.info("🎉 所有测试均通过！")
            
    except KeyboardInterrupt:
        logger.info("\n🛑 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 测试执行异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())