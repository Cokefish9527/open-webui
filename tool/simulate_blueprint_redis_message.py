#!/usr/bin/env python3
"""
模拟发送蓝图节点的Redis队列数据，触发主线任务的创建
"""

import json
import redis
import uuid
import time
import argparse
from datetime import datetime

def get_redis_connection():
    """获取Redis连接"""
    try:
        # 根据实际环境配置Redis连接参数
        r = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        # 测试连接
        r.ping()
        return r
    except Exception as e:
        print(f"无法连接到Redis: {e}")
        return None

def generate_blueprint_message(user_id, session_id=None, socket_id=None):
    """生成蓝图消息数据"""
    if not session_id:
        session_id = str(uuid.uuid4())
    if not socket_id:
        socket_id = str(uuid.uuid4())
    
    # 生成模拟的蓝图数据
    blueprint_data = {
        "id": str(uuid.uuid4()),
        "blueprintVersion": "v1.0",
        "executionDurationDays": "30天",
        "plannedTotalPosts": "60条",
        "postingFrequency": "2条/天",
        "requiredTiktokAccounts": "2个",
        "session_id": session_id,
        "request_id": str(uuid.uuid4()),
        "user_id": user_id,
        "socket_id": socket_id,
        "blue_image": "# 企业战略蓝图\n\n## 社交媒体矩阵\n- 抖音账号创建\n- 小红书账号创建\n\n## 内容策略\n- 视频内容制作\n- 图文内容制作\n\n## 发布计划\n- 每日2条视频\n- 每周3篇图文",
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat()
    }
    
    # 构造Redis消息格式
    message = {
        "type": "ai-conversation-agent-message-queue",
        "session_id": session_id,
        "socket_id": socket_id,
        "user_id": user_id,
        "content_type": "blue_image_content",
        "status": "FINISHED",
        "reply_id": str(uuid.uuid4()),
        "operate_id": str(uuid.uuid4()),
        "data": blueprint_data
    }
    
    return message

def send_blueprint_message(redis_conn, message, queue_name="ai-conversation-agent-message-queue"):
    """发送蓝图消息到Redis队列"""
    try:
        # 将消息转换为JSON字符串
        message_json = json.dumps(message, ensure_ascii=False)
        
        # 推送到Redis队列
        redis_conn.lpush(queue_name, message_json)
        
        print(f"✅ 成功发送蓝图消息到队列 '{queue_name}'")
        print(f"   用户ID: {message.get('user_id')}")
        print(f"   会话ID: {message.get('session_id')}")
        print(f"   消息内容: {message_json[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ 发送消息失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="模拟发送蓝图节点的Redis队列数据")
    parser.add_argument("--user-id", required=True, help="用户ID")
    parser.add_argument("--session-id", help="会话ID（可选）")
    parser.add_argument("--socket-id", help="Socket ID（可选）")
    parser.add_argument("--queue-name", default="ai-conversation-agent-message-queue", help="队列名称")
    parser.add_argument("--host", default="localhost", help="Redis主机地址")
    parser.add_argument("--port", type=int, default=6379, help="Redis端口")
    
    args = parser.parse_args()
    
    print("🚀 开始模拟发送蓝图节点Redis消息...")
    
    # 获取Redis连接
    redis_conn = get_redis_connection()
    if not redis_conn:
        return 1
    
    # 生成蓝图消息
    message = generate_blueprint_message(
        user_id=args.user_id,
        session_id=args.session_id,
        socket_id=args.socket_id
    )
    
    # 发送消息
    success = send_blueprint_message(redis_conn, message, args.queue_name)
    
    if success:
        print("\n✅ 蓝图消息发送完成，系统应该会自动创建相关任务")
        print("💡 您可以通过以下方式验证：")
        print("   1. 检查WebSocket调试页面的任务列表更新")
        print("   2. 查询数据库中的任务记录")
        print("   3. 查看相关日志输出")
        return 0
    else:
        print("\n❌ 蓝图消息发送失败")
        return 1

if __name__ == "__main__":
    exit(main())