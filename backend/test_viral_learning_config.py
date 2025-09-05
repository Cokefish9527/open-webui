"""
爆款学习调度器配置测试脚本

用于测试病毒学习调度器对不同配置值的处理，包括空值情况
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from open_webui.config.n8n_workflows import get_viral_learning_schedule_config
from open_webui.utils.viral_learning_scheduler import viral_learning_scheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

async def test_config_scenarios():
    """测试不同的配置场景"""
    log.info("=== 测试爆款学习调度器配置处理 ===")
    
    # 保存原始环境变量
    original_env = {}
    config_vars = [
        "VIRAL_LEARNING_ENABLED",
        "VIRAL_LEARNING_INTERVAL_MINUTES",
        "VIRAL_LEARNING_MAX_DAILY_CALLS",
        "VIRAL_LEARNING_START_HOUR",
        "VIRAL_LEARNING_END_HOUR",
        "VIRAL_LEARNING_RETRY_ATTEMPTS",
        "VIRAL_LEARNING_RETRY_DELAY_MINUTES"
    ]
    
    for var in config_vars:
        original_env[var] = os.environ.get(var)
    
    try:
        # 测试场景1: 默认配置（无环境变量）
        log.info("测试场景1: 默认配置（无环境变量）")
        for var in config_vars:
            if var in os.environ:
                del os.environ[var]
        
        config = get_viral_learning_schedule_config()
        log.info(f"默认配置: {config}")
        
        # 重新初始化调度器
        viral_learning_scheduler.config = config
        status = viral_learning_scheduler.get_status()
        log.info(f"默认配置下调度器状态: enabled={status['enabled']}")
        
        # 测试场景2: 空字符串配置
        log.info("测试场景2: 空字符串配置")
        os.environ["VIRAL_LEARNING_ENABLED"] = ""
        os.environ["VIRAL_LEARNING_INTERVAL_MINUTES"] = ""
        os.environ["VIRAL_LEARNING_MAX_DAILY_CALLS"] = ""
        
        config = get_viral_learning_schedule_config()
        log.info(f"空字符串配置: {config}")
        
        # 重新初始化调度器
        viral_learning_scheduler.config = config
        status = viral_learning_scheduler.get_status()
        log.info(f"空字符串配置下调度器状态: enabled={status['enabled']}")
        
        # 测试场景3: 明确禁用
        log.info("测试场景3: 明确禁用")
        os.environ["VIRAL_LEARNING_ENABLED"] = "false"
        os.environ["VIRAL_LEARNING_INTERVAL_MINUTES"] = "0"
        
        config = get_viral_learning_schedule_config()
        log.info(f"禁用配置: {config}")
        
        # 重新初始化调度器
        viral_learning_scheduler.config = config
        status = viral_learning_scheduler.get_status()
        log.info(f"禁用配置下调度器状态: enabled={status['enabled']}")
        
        # 测试场景4: 自定义有效配置
        log.info("测试场景4: 自定义有效配置")
        os.environ["VIRAL_LEARNING_ENABLED"] = "true"
        os.environ["VIRAL_LEARNING_INTERVAL_MINUTES"] = "5"
        os.environ["VIRAL_LEARNING_MAX_DAILY_CALLS"] = "10"
        os.environ["VIRAL_LEARNING_START_HOUR"] = "9"
        os.environ["VIRAL_LEARNING_END_HOUR"] = "18"
        
        config = get_viral_learning_schedule_config()
        log.info(f"自定义配置: {config}")
        
        # 重新初始化调度器
        viral_learning_scheduler.config = config
        status = viral_learning_scheduler.get_status()
        log.info(f"自定义配置下调度器状态: enabled={status['enabled']}")
        
        # 测试场景5: 启动调度器（仅测试启动逻辑，不实际执行工作流）
        log.info("测试场景5: 启动调度器")
        await viral_learning_scheduler.start()
        status = viral_learning_scheduler.get_status()
        log.info(f"调度器启动后状态: is_running={status['is_running']}")
        
        # 立即停止调度器
        await viral_learning_scheduler.stop()
        
    finally:
        # 恢复原始环境变量
        for var, value in original_env.items():
            if value is None and var in os.environ:
                del os.environ[var]
            elif value is not None:
                os.environ[var] = value

async def main():
    """主函数"""
    await test_config_scenarios()
    log.info("配置测试完成!")

if __name__ == "__main__":
    asyncio.run(main())