"""
任务完成信号处理器
处理来自n8n工作流的任务完成信号，通过Redis队列更新任务状态
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.hsai_tasks import HSAITasks, HSAITaskUpdateForm, HSAITaskStatus

# 配置日志
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


async def handle_task_completion_signal(message: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> None:
    """
    处理任务完成信号队列中的消息
    根据工作流结果更新任务状态
    
    Args:
        message: 从Redis队列中获取的消息数据
        config: 配置信息（可选）
    """
    try:
        log.info(f"处理任务完成信号: session_id={message.get('session_id')}, status={message.get('status')}")
        log.debug(f"完整消息内容: {message}")
        
        # 获取消息关键字段
        session_id = message.get("session_id")
        request_id = message.get("request_id")
        user_id = message.get("user_id")
        status = message.get("status", "FINISHED")
        content = message.get("content", {})
        
        # 验证必要字段
        if not session_id and not request_id:
            log.error(f"消息缺少必要字段: session_id={session_id}, request_id={request_id}")
            return
            
        # 根据session_id或request_id查找对应的任务
        # 这里需要根据实际的业务逻辑来查找任务
        # 目前我们假设request_id就是任务ID
        task_id = request_id
        
        if not task_id:
            log.error("无法确定任务ID")
            return
            
        # 查找任务
        task = HSAITasks.get_task_by_id(task_id)
        if not task:
            log.error(f"未找到任务: task_id={task_id}")
            return
            
        # 更新任务状态
        update_data = HSAITaskUpdateForm(
            status=HSAITaskStatus.COMPLETED,
            progress=100
        )
        
        # 如果消息中包含内容，可以更新任务的配置或提示词
        if isinstance(content, dict):
            # 可以根据需要更新任务的其他字段
            pass
            
        updated_task = HSAITasks.update_task_by_id(task_id, update_data)
        if updated_task:
            log.info(f"成功更新任务状态: task_id={task_id}, status={HSAITaskStatus.COMPLETED}")
        else:
            log.error(f"更新任务状态失败: task_id={task_id}")
                
    except Exception as e:
        log.error(f"处理任务完成信号时发生错误: {e}", exc_info=True)
        raise


def register_task_completion_queue_handler(redis_queue_listener) -> None:
    """
    注册任务完成信号队列处理器
    
    Args:
        redis_queue_listener: Redis队列监听器实例
    """
    # 注册任务完成信号队列处理器
    redis_queue_listener.register_handler(
        "ai-task-completion-queue", 
        handle_task_completion_signal,
        {
            "timeout": 30,
            "max_retry": 3,
            "dead_letter_queue": "task_completion_dead_letter"
        }
    )
    
    log.info("已注册任务完成信号队列处理器")