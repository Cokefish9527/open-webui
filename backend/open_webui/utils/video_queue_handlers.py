"""
视频队列消息处理器
包含各种视频相关队列的处理逻辑
"""

import logging
import json
from typing import Dict, Any
from sqlalchemy.orm import Session

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.viral_video_processor import ViralVideoProcessor

# 配置日志
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("CONFIG", logging.INFO))


async def handle_viral_video_crawl_notification(message: Dict[str, Any], db_session: Session) -> None:
    """
    处理爆款视频抓取通知队列消息
    
    Args:
        message: 队列消息数据
        db_session: 数据库会话
    """
    try:
        log.info(f"处理爆款视频抓取通知: {message.get('video_url', '未知URL')}")
        
        # 创建视频处理器实例
        processor = ViralVideoProcessor(db_session)
        
        # 处理单条消息
        # 注意：这里需要将消息转换为bytes格式，因为原有的处理器期望这种格式
        message_json = json.dumps(message, ensure_ascii=False).encode('utf-8')
        processor._process_message(message_json)
        
    except Exception as e:
        log.error(f"处理爆款视频抓取通知时发生错误: {e}")
        raise


def handle_viral_video_crawl_notification_sync(message: Dict[str, Any], db_session: Session) -> None:
    """
    同步方式处理爆款视频抓取通知队列消息
    
    Args:
        message: 队列消息数据
        db_session: 数据库会话
    """
    try:
        log.info(f"同步处理爆款视频抓取通知: {message.get('video_url', '未知URL')}")
        
        # 创建视频处理器实例
        processor = ViralVideoProcessor(db_session)
        
        # 处理单条消息
        # 注意：这里需要将消息转换为bytes格式，因为原有的处理器期望这种格式
        message_json = json.dumps(message, ensure_ascii=False).encode('utf-8')
        processor._process_message(message_json)
        
    except Exception as e:
        log.error(f"同步处理爆款视频抓取通知时发生错误: {e}")
        raise


async def handle_generic_video_message(message: Dict[str, Any], db_session: Session) -> None:
    """
    处理通用视频队列消息
    
    Args:
        message: 队列消息数据
        db_session: 数据库会话
    """
    try:
        message_type = message.get("type", "unknown")
        log.info(f"处理通用视频消息类型: {message_type}")
        
        # 根据消息类型进行不同的处理
        if message_type == "video_crawl_completed":
            await handle_viral_video_crawl_notification(message, db_session)
        else:
            log.warning(f"未知的视频消息类型: {message_type}")
            
    except Exception as e:
        log.error(f"处理通用视频消息时发生错误: {e}")
        raise


# 示例：如何添加新的队列处理器
def register_additional_queue_handlers(redis_queue_listener) -> None:
    """
    注册额外的队列处理器
    
    Args:
        redis_queue_listener: Redis队列监听器实例
    """
    # 注册更多队列处理器的示例
    # redis_queue_listener.register_handler(
    #     "new_video_queue", 
    #     handle_new_video_type,
    #     {
    #         "timeout": 60,
    #         "max_retry": 5,
    #         "dead_letter_queue": "new_video_dead_letter"
    #     }
    # )
    
    pass


# 示例处理器函数（可根据需要实现）
async def handle_new_video_type(message: Dict[str, Any], db_session: Session) -> None:
    """
    处理新类型的视频消息
    
    Args:
        message: 队列消息数据
        db_session: 数据库会话
    """
    # 实现具体的处理逻辑
    pass