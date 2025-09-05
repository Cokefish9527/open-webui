"""
爆款学习调度器测试脚本

用于测试病毒学习调度器的行为，而不影响主应用程序的启动流程
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from open_webui.utils.viral_learning_scheduler import viral_learning_scheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

async def test_scheduler_behavior():
    """测试调度器行为"""
    log.info("Starting viral learning scheduler test...")
    
    # 启动调度器
    await viral_learning_scheduler.start()
    
    # 获取初始状态
    status = viral_learning_scheduler.get_status()
    log.info(f"Initial scheduler status: {status}")
    
    # 运行一段时间观察行为
    log.info("Running scheduler for 5 minutes to observe behavior...")
    await asyncio.sleep(300)  # 5分钟
    
    # 获取最终状态
    final_status = viral_learning_scheduler.get_status()
    log.info(f"Final scheduler status: {final_status}")
    
    # 停止调度器
    await viral_learning_scheduler.stop()
    log.info("Scheduler test completed.")

if __name__ == "__main__":
    asyncio.run(test_scheduler_behavior())