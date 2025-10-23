#!/usr/bin/env python3
"""
测试Redis队列消息插入功能
验证correlation_id列是否已正确添加并可正常使用
"""

import sys
import os
import time
import uuid

def test_redis_queue_insert():
    """测试Redis队列消息插入功能"""
    try:
        # 添加项目根目录到Python路径
        backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        # 导入必要的模块
        from open_webui.models.redis_queue_messages import RedisQueueMessages, RedisQueueMessageForm
        
        print("测试Redis队列消息插入功能...")
        
        # 创建测试数据
        test_data = {
            "env": "test",
            "session_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "operate_id": "test_operation",
            "request_id": str(uuid.uuid4()),
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
        
        form_data = RedisQueueMessageForm(
            queue_name="ai-conversation-agent-message-queue",
            raw_data=str(test_data),
            fetched_at=int(time.time()),
            correlation_id=str(uuid.uuid4())
        )
        
        # 尝试插入消息
        print("正在插入测试消息...")
        result = RedisQueueMessages.insert_new_message(form_data)
        
        if result:
            print("✓ 消息插入成功!")
            print(f"  消息ID: {result.id}")
            print(f"  correlation_id: {result.correlation_id}")
            print(f"  队列名称: {result.queue_name}")
            
            # 验证消息可以被正确检索
            print("正在通过correlation_id检索消息...")
            retrieved = RedisQueueMessages.get_message_by_correlation_id(form_data.correlation_id)
            if retrieved:
                print("✓ 通过correlation_id检索消息成功!")
                print(f"  检索到的消息ID: {retrieved.id}")
            else:
                print("✗ 通过correlation_id检索消息失败!")
                return False
                
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
    print("Redis队列消息插入功能测试")
    print("=" * 40)
    
    success = test_redis_queue_insert()
    if success:
        print("\n🎉 所有测试通过！Redis队列消息功能正常。")
        return 0
    else:
        print("\n❌ 测试失败！Redis队列消息功能可能仍有问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())