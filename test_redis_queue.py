#!/usr/bin/env python3
"""
测试Redis队列功能的简单脚本
"""

import json
import time
import redis


# Redis配置（根据实际情况修改）
REDIS_URL = "redis://localhost:6379/0"


def get_redis_client():
    """获取Redis客户端实例"""
    return redis.from_url(REDIS_URL)


def send_video_learning_notification(video_id: int, status: str, business_name: str = "HSAI"):
    """发送视频学习通知到Redis队列"""
    try:
        # 获取Redis客户端
        redis_client = get_redis_client()
        
        # 创建消息
        message = {
            "video_id": video_id,
            "status": status,  # "success" 或 "failed"
            "business_name": business_name,
            "timestamp": int(time.time())
        }
        
        # 将消息转换为JSON并发送到Redis队列
        message_json = json.dumps(message, ensure_ascii=False)
        redis_client.lpush("video_learning_notification", message_json)
        
        print(f"已发送视频学习通知: {message}")
        return True
        
    except Exception as e:
        print(f"发送视频学习通知失败: {e}")
        return False


def listen_to_queue():
    """监听队列消息（用于测试）"""
    try:
        redis_client = get_redis_client()
        print("开始监听 video_learning_notification 队列...")
        
        while True:
            # 从队列中阻塞式获取消息
            result = redis_client.brpop(["video_learning_notification"], timeout=5)
            
            if result:
                # 解析消息
                if isinstance(result, (list, tuple)) and len(result) >= 2:
                    queue_name, message_data = result[0], result[1]
                    message = json.loads(message_data.decode('utf-8'))
                    print(f"收到消息: {message}")
                else:
                    print(f"收到未知格式的消息: {result}")
            else:
                print("超时，继续监听...")
                
    except KeyboardInterrupt:
        print("停止监听")
    except Exception as e:
        print(f"监听队列时发生错误: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "send":
            # 发送测试消息
            video_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            status = sys.argv[3] if len(sys.argv) > 3 else "success"
            business_name = sys.argv[4] if len(sys.argv) > 4 else "HSAI"
            send_video_learning_notification(video_id, status, business_name)
        elif sys.argv[1] == "listen":
            # 监听队列
            listen_to_queue()
    else:
        print("使用方法:")
        print("  python test_redis_queue.py send [video_id] [status] [business_name]  - 发送测试消息")
        print("  python test_redis_queue.py listen                   - 监听队列消息")
        print("\n示例:")
        print("  python test_redis_queue.py send 1 success HSAI     - 发送学习成功消息")
        print("  python test_redis_queue.py send 2 failed HSAI      - 发送学习失败消息")