import json
import logging
import time
from typing import Dict, Any, Optional
import redis

from open_webui.env import SRC_LOG_LEVELS, REDIS_URL
from open_webui.models.hsai_video_learning_status import HSAIVideoLearningStatuses, HSAIVideoLearningStatusEnum
from open_webui.models.hsai_video_learning_log import HSAIVideoLearningLogs
# 导入任务相关模块
from open_webui.models.hsai_tasks import HSAITasks, HSAITaskUpdateForm, HSAITaskStatus
# 导入通用对话结束机制
from open_webui.utils.conversation_ender import end_conversation_for_task_completion

# 配置日志
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


def get_redis_client():
    """获取Redis客户端实例"""
    return redis.from_url(REDIS_URL)


async def handle_video_learning_notification(message: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> None:
    """
    处理视频学习通知队列中的信息
    更新视频学习状态和对应的任务状态
    
    Args:
        message: 从Redis队列中获取的消息数据
        config: 配置信息（可选）
    """
    try:
        log.info(f"处理视频学习通知: video_id={message.get('video_id')}, status={message.get('status')}")
        log.debug(f"完整消息内容: {message}")
        
        video_id = message.get("video_id")
        status = message.get("status")  # success/failed
        business_name = message.get("business_name", "HSAI")
        user_id = message.get("user_id")  # 获取用户ID用于对话结束通知
        session_id = message.get("session_id")  # 获取会话ID用于对话结束通知
        
        if video_id is None or not status:
            log.error(f"消息缺少必要字段: video_id={video_id}, status={status}")
            return
            
        if status not in ["success", "failed"]:
            log.error(f"无效的状态值: {status}")
            return
            
        existing_status = HSAIVideoLearningStatuses.get_status_by_business_and_video(business_name, str(video_id))
        original_status = existing_status.status if existing_status else None
        target_status = (
            HSAIVideoLearningStatusEnum.LEARNED
            if status == "success"
            else HSAIVideoLearningStatusEnum.PENDING
        )
        
        try:
            if status == "success":
                result_status = HSAIVideoLearningStatuses.upsert_status(
                    business_name=business_name,
                    video_id=str(video_id),
                    status_value=target_status.value,
                )
            else:
                result_status = HSAIVideoLearningStatuses.mark_pending(
                    business_name=business_name,
                    video_id=str(video_id),
                )
            if result_status:
                log.info(f"成功更新视频学习状态: video_id={video_id}, status={target_status.value}")
            else:
                log.error(f"无法更新视频学习状态: video_id={video_id}")
        except Exception as exc:
            log.error(f"更新/重置视频学习状态时发生错误: {exc}")
            raise
        
        try:
            reason = (
                "视频学习已完成，状态变为LEARNED"
                if status == "success"
                else "视频学习处理失败，状态变为PENDING"
            )
            log_entry = HSAIVideoLearningLogs.record_status_change(
                business_name=business_name,
                video_id=str(video_id),
                from_status=original_status,
                to_status=target_status.value,
                reason=reason,
                operator="system",
            )
            if log_entry:
                log.info(f"成功记录视频学习状态变更日志: video_id={video_id}")
            else:
                log.error(f"记录视频学习状态变更日志失败: video_id={video_id}")
        except Exception as err:
            log.error(f"记录视频学习状态变更日志时发生错误: {err}")
            
        # 如果视频学习成功，查找并更新对应的视频发布任务
        if status == "success":
            try:
                # 查找对应的视频发布任务并标记为完成
                task = _find_and_complete_video_task(video_id, user_id)
                if task:
                    log.info(f"成功将视频发布任务标记为完成: task_id={task.id}")
                    
                    # 使用新的通用对话结束机制
                    try:
                        # 发送对话结束通知
                        await end_conversation_for_task_completion(
                            user_id=user_id,
                            task_id=task.id,
                            session_id=session_id,
                            task_type="视频发布"
                        )
                    except Exception as e:
                        log.error(f"发送对话结束通知时发生错误: {e}")
                else:
                    log.info(f"未找到对应的视频发布任务: video_id={video_id}")
            except Exception as task_err:
                log.error(f"处理视频发布任务时发生错误: {task_err}")
            
    except Exception as e:
        log.error(f"处理视频学习通知时发生错误: {e}", exc_info=True)
        raise


def _find_and_complete_video_task(video_id: str, user_id: Optional[str] = None) -> Optional[Any]:
    """
    根据视频ID查找并完成对应的视频发布任务
    
    Args:
        video_id: 视频ID
        user_id: 用户ID（可选）
        
    Returns:
        完成的任务对象，如果未找到则返回None
    """
    try:
        # 根据视频ID查找任务
        # 这里假设任务配置中存储了视频ID
        tasks = HSAITasks.get_tasks_by_user_id(
            user_id=user_id if user_id else None,
            task_type="platform_publishing",  # 只查找视频发布任务
            limit=100,
        )
        
        # 如果没有通过user_id找到任务，尝试查找所有用户的视频发布任务
        if not tasks and not user_id:
            # 这种情况下可能需要采用其他策略查找任务
            # 暂时保留原有逻辑作为备选
            tasks = HSAITasks.get_tasks_by_user_id(
                user_id=None,
                limit=100,
            )
        
        for task in tasks:
            config = task.config or {}
            # 检查任务类型是否为视频发布任务
            if task.task_type == "platform_publishing":
                # 检查任务配置中是否包含对应的视频ID
                if config.get("video_id") == str(video_id):
                    # 检查任务是否已经完成
                    if task.status != HSAITaskStatus.COMPLETED.value:
                        # 更新任务状态为完成
                        updated_task = HSAITasks.update_task_by_id(
                            task.id,
                            HSAITaskUpdateForm(
                                status=HSAITaskStatus.COMPLETED.value,
                                progress=100
                            )
                        )
                        if updated_task:
                            log.info(f"成功将视频发布任务标记为完成: task_id={task.id}")
                            return updated_task
                        else:
                            log.error(f"更新视频发布任务失败: task_id={task.id}")
                    else:
                        log.info(f"视频发布任务已经是完成状态: task_id={task.id}")
                        return task
        return None
    except Exception as e:
        log.error(f"查找并完成视频发布任务时发生错误: {e}")
        return None


def register_video_learning_queue_handler(redis_queue_listener) -> None:
    """
    注册视频学习通知队列处理器
    
    Args:
        redis_queue_listener: Redis队列监听器实例
    """
    # 注册视频学习通知队列处理器
    redis_queue_listener.register_handler(
        "video_learning_notification", 
        handle_video_learning_notification,
        {
            "timeout": 30,
            "max_retry": 3,
            "dead_letter_queue": "video_learning_dead_letter"
        }
    )
    
    log.info("已注册视频学习通知队列处理器")