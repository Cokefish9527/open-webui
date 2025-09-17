"""
n8n工作流视频抓取完成通知脚本
用于在n8n工作流完成视频抓取后，向Redis队列发送通知消息
"""

import json
import time
import uuid
from typing import Dict, Any, List, Optional
import redis

from open_webui.utils.redis_signal_handler import get_redis_client

def send_video_crawl_notification(
    enterprise_id: str,
    video_url: str,
    video_title: str = "",
    video_description: str = "",
    thumbnail_url: str = "",
    duration: int = 0,
    platform: str = "",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    crawl_status: str = "success",
    error_message: str = ""
) -> bool:
    """
    发送视频抓取完成通知到Redis队列
    
    Args:
        enterprise_id: 企业ID
        video_url: 视频链接
        video_title: 视频标题
        video_description: 视频描述
        thumbnail_url: 缩略图链接
        duration: 视频时长（秒）
        platform: 平台名称
        tags: 视频标签列表
        metadata: 其他元数据
        crawl_status: 抓取状态 (success/error)
        error_message: 错误信息（如果抓取失败）
        
    Returns:
        bool: 发送是否成功
    """
    try:
        # 获取Redis客户端
        redis_client = get_redis_client()
        
        # 构造消息体
        message = {
            "env": "prod",              # 环境 gray/prod
            "enterprise_id": enterprise_id,        # 企业ID
            "video_url": video_url,            # 抓取到的视频链接
            "video_title": video_title,          # 视频标题
            "video_description": video_description,    # 视频描述
            "thumbnail_url": thumbnail_url,        # 缩略图链接
            "duration": duration,              # 视频时长（秒）
            "platform": platform,             # 平台名称（如抖音、快手等）
            "tags": tags or [],                 # 视频标签
            "metadata": metadata or {},             # 其他元数据
            "crawl_timestamp": int(time.time()),       # 抓取时间戳
            "crawl_status": crawl_status,  # 抓取状态 success/error
            "error_message": error_message,        # 错误信息（如果抓取失败）
            "retry_count": 0,           # 重试次数
            "message_id": str(uuid.uuid4()),           # 消息唯一标识符
            "create_ts": int(time.time())     # 消息创建时间戳
        }
        
        # 将消息转换为JSON并发送到Redis队列
        message_json = json.dumps(message, ensure_ascii=False)
        redis_client.lpush("viral_video_crawled_notification", message_json)
        
        print(f"已发送视频抓取通知: {video_url}")
        return True
        
    except Exception as e:
        print(f"发送视频抓取通知失败: {e}")
        return False


def test_notification():
    """测试通知发送功能"""
    # 示例数据
    success = send_video_crawl_notification(
        enterprise_id="test_enterprise_123",
        video_url="https://example.com/video123.mp4",
        video_title="爆款视频标题",
        video_description="这是一个爆款视频的描述",
        thumbnail_url="https://example.com/thumbnail.jpg",
        duration=120,
        platform="抖音",
        tags=["搞笑", "娱乐", "热门"],
        metadata={
            "author": "测试作者",
            "views": 10000,
            "likes": 5000
        }
    )
    
    if success:
        print("测试通知发送成功")
    else:
        print("测试通知发送失败")


if __name__ == "__main__":
    test_notification()