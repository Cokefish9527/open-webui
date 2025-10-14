import json
import logging
import time
from typing import Dict, Any, Optional
import redis

from open_webui.env import SRC_LOG_LEVELS, REDIS_URL
from open_webui.models.hsai_video_learning_status import HSAIVideoLearningStatuses, HSAIVideoLearningStatusEnum
from open_webui.models.hsai_video_learning_log import HSAIVideoLearningLogs

# 配置日志
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


def get_redis_client():
    """获取Redis客户端实例"""
    return redis.from_url(REDIS_URL)


async def handle_video_learning_notification(message: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> None:
    """
    处理视频学习完成通知队列中的消息
    根据视频学习结果更新视频学习状态
    
    Args:
        message: 从Redis队列中获取的消息数据
        config: 配置信息（可选）
    """
    try:
        log.info(f"处理视频学习通知: video_id={message.get('video_id')}, status={message.get('status')}")
        log.debug(f"完整消息内容: {message}")
        
        # 获取消息关键字段
        video_id = message.get("video_id")
        status = message.get("status")  # success/failed
        business_name = message.get("business_name", "HSAI")  # 从消息中获取business_name，如果没有则使用默认值
        
        # 验证必要字段
        if video_id is None or not status:
            log.error(f"消息缺少必要字段: video_id={video_id}, status={status}")
            return
            
        # 验证状态值
        if status not in ["success", "failed"]:
            log.error(f"无效的状态值: {status}")
            return
            
        # 查找现有的学习状态记录
        existing_status = HSAIVideoLearningStatuses.get_status_by_business_and_video(business_name, str(video_id))
        
        # 记录原始状态
        original_status = existing_status.status if existing_status else None
        
        if status == "success":
            # 学习成功：将视频状态设为已学习
            learning_status = HSAIVideoLearningStatusEnum.LEARNED
            
            if existing_status:
                # 更新现有记录
                update_data = {
                    "status": learning_status.value,  # 转换枚举为字符串
                    "updated_at": int(time.time())
                }
                updated_status = HSAIVideoLearningStatuses.update_status(existing_status.id, update_data)
                if updated_status:
                    log.info(f"成功更新视频学习状态: video_id={video_id}, status={learning_status.value}")
                else:
                    log.error(f"更新视频学习状态失败: video_id={video_id}")
            else:
                # 创建新的学习状态记录
                status_form = {
                    "business_name": business_name,
                    "video_id": str(video_id),
                    "status": learning_status.value  # 转换枚举为字符串
                }
                new_status = HSAIVideoLearningStatuses.insert_new_status(status_form)
                if new_status:
                    log.info(f"成功创建视频学习状态记录: video_id={video_id}, status={learning_status.value}")
                else:
                    log.error(f"创建视频学习状态记录失败: video_id={video_id}")
        else:
            # 学习失败：将视频状态重置为待学习（删除记录）
            try:
                # 记录日志
                log_form = {
                    "business_name": business_name,
                    "video_id": str(video_id),
                    "from_status": original_status,
                    "to_status": "pending",  # 重置为待学习状态
                    "change_reason": "视频学习任务失败，重置为待学习状态",
                    "changed_by": "system"
                }
                log_entry = HSAIVideoLearningLogs.insert_new_log(log_form)
                if log_entry:
                    log.info(f"成功记录视频学习失败日志: video_id={video_id}")
                else:
                    log.error(f"记录视频学习失败日志失败: video_id={video_id}")
            except Exception as e:
                log.error(f"记录视频学习失败日志时发生错误: {e}")
            
            # 删除视频学习状态记录，使其重置为待学习
            if existing_status:
                try:
                    result = HSAIVideoLearningStatuses.delete_status_by_id(existing_status.id)
                    if result:
                        log.info(f"成功删除视频学习状态记录，重置为待学习: video_id={video_id}")
                    else:
                        log.error(f"删除视频学习状态记录失败: video_id={video_id}")
                except Exception as e:
                    log.error(f"删除视频学习状态记录时发生错误: {e}")
            else:
                log.info(f"视频学习状态记录不存在，无需删除: video_id={video_id}")
                
        # 记录状态变更日志（仅对成功情况）
        if status == "success":
            try:
                log_form = {
                    "business_name": business_name,
                    "video_id": str(video_id),
                    "from_status": original_status,
                    "to_status": HSAIVideoLearningStatusEnum.LEARNED.value if status == "success" else "pending",
                    "change_reason": f"视频学习任务完成，结果: {status}",
                    "changed_by": "system"
                }
                log_entry = HSAIVideoLearningLogs.insert_new_log(log_form)
                if log_entry:
                    log.info(f"成功记录视频学习状态变更日志: video_id={video_id}")
                else:
                    log.error(f"记录视频学习状态变更日志失败: video_id={video_id}")
            except Exception as e:
                log.error(f"记录视频学习状态变更日志时发生错误: {e}")
                
    except Exception as e:
        log.error(f"处理视频学习通知时发生错误: {e}", exc_info=True)
        raise


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
