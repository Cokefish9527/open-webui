#!/usr/bin/env python3
"""
修复Redis队列消息表中的时间戳列问题
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_timestamp_insert():
    """测试时间戳插入"""
    try:
        # 添加项目根目录到Python路径
        backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        # 导入必要的模块
        from open_webui.models.redis_queue_messages import RedisQueueMessages, RedisQueueMessageForm
        from open_webui.env import DATABASE_URL
        
        print(f"数据库URL: {DATABASE_URL}")
        
        print("测试Redis队列消息插入功能...")
        
        # 创建测试数据
        test_data = {
            "env": "test",
            "session_id": "test-session-id",
            "user_id": "test-user-id",
            "operate_id": "test_operation",
            "request_id": "test-request-id",
            "socket_id": "test_socket",
            "status": "PENDING",
            "content_type": 1,
            "content": {
                "text": "这是一个测试消息",
                "data": {
                    "video_link": ""
                }
            },
            "create_ts": int(time.time() * 1000)
        }
        
        # 检查数据库类型
        if "postgresql" in DATABASE_URL.lower():
            print("使用PostgreSQL数据库，需要特殊处理时间戳")
            # 对于PostgreSQL，我们需要使用datetime对象而不是整数
            import datetime
            current_time = int(time.time())
            fetched_at = datetime.datetime.fromtimestamp(current_time)
            
            form_data = RedisQueueMessageForm(
                queue_name="ai-conversation-agent-message-queue",
                raw_data=str(test_data),
                fetched_at=current_time,  # 保持整数，让模型处理转换
                correlation_id="test-correlation-id"
            )
        else:
            print("使用SQLite数据库")
            form_data = RedisQueueMessageForm(
                queue_name="ai-conversation-agent-message-queue",
                raw_data=str(test_data),
                fetched_at=int(time.time()),
                correlation_id="test-correlation-id"
            )
        
        # 尝试插入消息
        print("正在插入测试消息...")
        result = RedisQueueMessages.insert_new_message(form_data)
        
        if result:
            print("✓ 消息插入成功!")
            print(f"  消息ID: {result.id}")
            print(f"  correlation_id: {result.correlation_id}")
            print(f"  队列名称: {result.queue_name}")
            
            # 清理测试数据
            print("正在清理测试数据...")
            RedisQueueMessages.delete_message_by_id(result.id)
            print("✓ 测试数据清理完成")
            
            return True
        else:
            print("✗ 消息插入失败!")
            return False
            
    except ImportError as e:
        print(f"✗ 导入模块失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Redis队列消息时间戳测试")
    print("=" * 40)
    
    success = test_timestamp_insert()
    if success:
        print("\n🎉 时间戳测试通过！")
        return 0
    else:
        print("\n❌ 时间戳测试失败！")
        return 1

if __name__ == "__main__":
    sys.exit(main())