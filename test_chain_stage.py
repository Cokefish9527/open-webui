#!/usr/bin/env python3
"""
测试思维链功能的脚本
向Redis队列发送思维链状态消息，验证后端是否能正确处理
"""

import redis
import json
import time
import uuid

# Redis连接配置（使用公网配置）
REDIS_HOST = "r-bp16h5hix81xr15svxpd.redis.rds.aliyuncs.com"
REDIS_PORT = 6379
REDIS_DB = 7
REDIS_USERNAME = "r-bp16h5hix81xr15svx"
REDIS_PASSWORD = "hdtFOXRwdFA1EZzaypqv7PE6j1XuVT"

def send_chain_stage_message():
    """发送思维链状态消息到Redis队列"""
    # 连接Redis
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        username=REDIS_USERNAME,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
    
    # 测试Redis连接
    try:
        r.ping()
        print("Redis连接成功")
    except Exception as e:
        print(f"Redis连接失败: {e}")
        return
    
    # 生成测试数据
    session_id = f"session_test_{uuid.uuid4().hex[:8]}"
    user_id = "test_user_123"
    request_id = f"request_{uuid.uuid4().hex[:8]}"
    socket_id = None  # 在实际应用中，这应该是有效的socket_id
    
    # 思维链阶段列表
    chain_stages = [
        "think",
        "search",
        "collect_message",
        "message_analysis",
        "blue_image",
        "check_blue_image",
        "select_video_script",
        "parse_hot_video",
        "generate_video_text",
        "generate_final_video"
    ]
    
    print(f"开始发送思维链状态消息测试，session_id: {session_id}")
    
    # 发送每个阶段的消息
    for i, stage in enumerate(chain_stages):
        message = {
            "session_id": session_id,
            "user_id": user_id,
            "request_id": request_id,
            "socket_id": socket_id,
            "create_ts": int(time.time() * 1000),
            "chain_stage": stage
        }
        
        # 将消息推送到Redis队列
        r.lpush("ai-conversation-chain-stage-queue", json.dumps(message, ensure_ascii=False))
        print(f"已发送阶段 [{i+1}/{len(chain_stages)}]: {stage}")
        
        # 等待1秒再发送下一个阶段
        time.sleep(1)
    
    print("所有思维链状态消息已发送完成")

if __name__ == "__main__":
    send_chain_stage_message()