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
    ������Ƶѧϰ���֪ͨ�����е���Ϣ
    ������Ƶѧϰ���������Ƶѧϰ״̬
    
    Args:
        message: ��Redis�����л�ȡ����Ϣ����
        config: ������Ϣ����ѡ��
    """
    try:
        log.info(f"������Ƶѧϰ֪ͨ: video_id={message.get('video_id')}, status={message.get('status')}")
        log.debug(f"������Ϣ����: {message}")
        
        video_id = message.get("video_id")
        status = message.get("status")  # success/failed
        business_name = message.get("business_name", "HSAI")
        
        if video_id is None or not status:
            log.error(f"��Ϣȱ�ٱ�Ҫ�ֶ�: video_id={video_id}, status={status}")
            return
            
        if status not in ["success", "failed"]:
            log.error(f"��Ч��״ֵ̬: {status}")
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
                log.info(f"�ɹ�������Ƶѧϰ״̬: video_id={video_id}, status={target_status.value}")
            else:
                log.error(f"�޷������Ƶѧϰ״̬: video_id={video_id}")
        except Exception as exc:
            log.error(f"����/������Ƶѧϰ״̬ʱ��������: {exc}")
            raise
        
        try:
            reason = (
                "��Ƶѧϰ������ɣ�״̬��ΪLEARNED"
                if status == "success"
                else "��Ƶѧϰ����ʧ�ܣ�״̬��ΪPENDING"
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
                log.info(f"�ɹ���¼��Ƶѧϰ״̬�����־: video_id={video_id}")
            else:
                log.error(f"��¼��Ƶѧϰ״̬�����־ʧ��: video_id={video_id}")
        except Exception as err:
            log.error(f"��¼��Ƶѧϰ״̬�����־ʱ��������: {err}")
            
    except Exception as e:
        log.error(f"������Ƶѧϰ֪ͨʱ��������: {e}", exc_info=True)
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
