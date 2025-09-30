#!/usr/bin/env python3
"""
测试视频学习通知功能的脚本
"""

import json
import time
import sys
import os

# 添加项目路径到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# 直接实现获取Redis客户端的功能
import redis
from open_webui.env import REDIS_URL

def get_redis_client():
    """获取Redis客户端实例"""
    return redis.from_url(REDIS_URL)


def send_test_notification():
    """发送测试通知到Redis队列"""
    try:
        # 获取Redis客户端
        redis_client = get_redis_client()
        
        # 创建测试消息
        test_message = {
            "video_id": 1,
            "status": "success",  # 或 "failed"
            "timestamp": int(time.time())
        }
        
        # 将消息转换为JSON并发送到Redis队列
        message_json = json.dumps(test_message, ensure_ascii=False)
        redis_client.lpush("video_learning_notification", message_json)
        
        print(f"已发送测试通知: {test_message}")
        return True
        
    except Exception as e:
        print(f"发送测试通知失败: {e}")
        return False


def send_failed_test_notification():
    """发送失败状态的测试通知到Redis队列"""
    try:
        # 获取Redis客户端
        redis_client = get_redis_client()
        
        # 创建测试消息
        test_message = {
            "video_id": 2,
            "status": "failed",
            "timestamp": int(time.time())
        }
        
        # 将消息转换为JSON并发送到Redis队列
        message_json = json.dumps(test_message, ensure_ascii=False)
        redis_client.lpush("video_learning_notification", message_json)
        
        print(f"已发送失败状态测试通知: {test_message}")
        return True
        
    except Exception as e:
        print(f"发送失败状态测试通知失败: {e}")
        return False


if __name__ == "__main__":
    print("视频学习通知测试脚本")
    print("1. 发送成功状态通知")
    print("2. 发送失败状态通知")
    
    choice = input("请选择要发送的通知类型 (1 或 2): ")
    
    if choice == "1":
        send_test_notification()
    elif choice == "2":
        send_failed_test_notification()
    else:
        print("无效的选择")