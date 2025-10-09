"""
任务完成信号处理测试脚本
用于测试Redis队列监听器中任务完成信号的处理逻辑
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any

import redis

from open_webui.env import REDIS_URL
from open_webui.models.hsai_tasks import HSAITasks, HSAITaskForm, HSAITaskStatus

# 配置日志
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def get_redis_client():
    """获取Redis客户端实例"""
    return redis.from_url(REDIS_URL)


def create_test_task() -> str:
    """创建一个测试任务"""
    task_form = HSAITaskForm(
        title="测试任务",
        description="用于测试任务完成信号处理的测试任务",
        task_type="video_creation",
        task_category="test",
        config={"test": True},
        priority=1
    )
    
    # 创建任务
    task = HSAITasks.insert_new_task("test_user_id", task_form)
    if task:
        log.info(f"创建测试任务成功: task_id={task.id}")
        return task.id
    else:
        log.error("创建测试任务失败")
        return ""


def send_task_completion_signal(task_id: str):
    """发送任务完成信号到Redis队列"""
    redis_client = get_redis_client()
    
    # 构造消息
    message = {
        "env": "test",
        "session_id": f"test_session_{uuid.uuid4().hex[:8]}",
        "user_id": "test_user_id",
        "request_id": task_id,  # 使用任务ID作为请求ID
        "operate_id": "test_completion",
        "socket_id": f"test_socket_{uuid.uuid4().hex[:8]}",
        "status": "FINISHED",
        "content_type": 1,
        "content": {
            "text": "任务已完成",
            "data": {
                "result": "success"
            }
        },
        "create_ts": int(time.time() * 1000)
    }
    
    # 发送到队列
    queue_name = "ai-task-completion-queue"
    redis_client.lpush(queue_name, json.dumps(message))
    log.info(f"发送任务完成信号到队列 {queue_name}: task_id={task_id}")


def check_task_status(task_id: str) -> str:
    """检查任务状态"""
    task = HSAITasks.get_task_by_id(task_id)
    if task:
        return task.status
    return "not_found"


async def test_task_completion_flow():
    """测试任务完成信号处理流程"""
    log.info("开始测试任务完成信号处理流程")
    
    # 1. 创建测试任务
    task_id = create_test_task()
    if not task_id:
        log.error("无法创建测试任务，测试终止")
        return False
    
    # 2. 验证任务初始状态
    initial_status = check_task_status(task_id)
    log.info(f"任务初始状态: {initial_status}")
    
    if initial_status != HSAITaskStatus.PENDING:
        log.warning(f"任务初始状态不是PENDING，而是{initial_status}")
    
    # 3. 发送任务完成信号
    send_task_completion_signal(task_id)
    
    # 4. 等待处理（给一些时间让信号处理器处理消息）
    log.info("等待任务完成信号处理...")
    await asyncio.sleep(5)
    
    # 5. 检查任务最终状态
    final_status = check_task_status(task_id)
    log.info(f"任务最终状态: {final_status}")
    
    # 6. 验证结果
    if final_status == HSAITaskStatus.COMPLETED:
        log.info("测试成功：任务状态已更新为COMPLETED")
        return True
    else:
        log.error(f"测试失败：任务状态未正确更新，当前状态为{final_status}")
        return False


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_task_completion_flow())