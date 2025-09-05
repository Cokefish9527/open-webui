"""
定时工作流测试脚本

用于测试定时工作流的调度行为，确保它们按照预期的时间间隔执行
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from open_webui.utils.viral_learning_scheduler import viral_learning_scheduler
from open_webui.config.n8n_workflows import get_viral_learning_schedule_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

class ScheduledWorkflowTester:
    """定时工作流测试器"""
    
    def __init__(self):
        self.scheduler = viral_learning_scheduler
        self.test_duration = 300  # 5分钟测试时间
    
    async def test_viral_learning_scheduler(self):
        """测试爆款学习调度器"""
        log.info("=== 测试爆款学习调度器 ===")
        
        # 获取配置
        config = get_viral_learning_schedule_config()
        log.info(f"调度器配置: {config}")
        
        # 启动调度器
        log.info("启动病毒学习调度器...")
        await self.scheduler.start()
        
        # 等待一小段时间检查状态
        await asyncio.sleep(5)
        
        # 检查初始状态
        initial_status = self.scheduler.get_status()
        log.info(f"初始状态: {initial_status}")
        
        # 验证调度器已启动但未执行工作流
        assert initial_status["is_running"] == True, "调度器应该正在运行"
        assert initial_status["execution_count"] == 0, "启动时不应执行工作流"
        log.info("✓ 调度器已正确启动，未执行工作流")
        
        # 运行测试周期
        log.info(f"运行测试 {self.test_duration} 秒...")
        start_time = datetime.now()
        
        # 模拟测试期间的检查
        check_interval = 30  # 每30秒检查一次
        num_checks = self.test_duration // check_interval
        
        for i in range(num_checks):
            await asyncio.sleep(check_interval)
            current_status = self.scheduler.get_status()
            elapsed = datetime.now() - start_time
            log.info(f"[{elapsed.total_seconds():.0f}s] 状态检查 #{i+1}: 执行次数 = {current_status['execution_count']}")
        
        # 获取最终状态
        final_status = self.scheduler.get_status()
        log.info(f"最终状态: {final_status}")
        
        # 停止调度器
        await self.scheduler.stop()
        log.info("调度器已停止")
        
        return final_status
    
    async def run_all_tests(self):
        """运行所有测试"""
        log.info("开始定时工作流测试...")
        
        try:
            # 测试爆款学习调度器
            final_status = await self.test_viral_learning_scheduler()
            
            log.info("=== 测试完成 ===")
            log.info(f"总执行次数: {final_status['execution_count']}")
            log.info(f"每日执行次数: {final_status['daily_execution_count']}")
            
            return True
            
        except Exception as e:
            log.error(f"测试失败: {e}")
            return False

async def main():
    """主函数"""
    tester = ScheduledWorkflowTester()
    success = await tester.run_all_tests()
    
    if success:
        log.info("所有测试通过!")
        return 0
    else:
        log.error("测试失败!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)