#!/usr/bin/env python3
"""
修复Redis队列消息表模型定义问题
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def fix_model_definition():
    """修复模型定义"""
    try:
        # 导入数据库配置
        from open_webui.env import DATABASE_URL
        
        print(f"数据库URL: {DATABASE_URL}")
        
        # 检查数据库类型
        if "postgresql" in DATABASE_URL.lower():
            print("检测到PostgreSQL数据库")
            print("PostgreSQL中时间戳列使用timestamp with time zone类型")
            print("需要确保模型与数据库结构匹配")
            return True
        elif "sqlite" in DATABASE_URL.lower():
            print("检测到SQLite数据库")
            print("SQLite中时间戳列使用BIGINT类型")
            return True
        else:
            print(f"不支持的数据库类型: {DATABASE_URL}")
            return False
            
    except Exception as e:
        print(f"检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_current_model():
    """检查当前模型定义"""
    try:
        # 添加项目根目录到Python路径
        backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        # 导入模型
        from open_webui.models.redis_queue_messages import RedisQueueMessage
        
        print("当前模型定义:")
        print(f"  fetched_at 类型: {RedisQueueMessage.fetched_at.type}")
        print(f"  created_at 类型: {RedisQueueMessage.created_at.type}")
        print(f"  updated_at 类型: {RedisQueueMessage.updated_at.type}")
        print(f"  last_executed_at 类型: {RedisQueueMessage.last_executed_at.type}")
        print(f"  retry_count 类型: {RedisQueueMessage.retry_count.type}")
        
        return True
        
    except Exception as e:
        print(f"检查模型定义时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Redis队列消息表模型定义检查工具")
    print("=" * 40)
    
    # 检查数据库类型
    success1 = fix_model_definition()
    
    # 检查当前模型
    success2 = check_current_model()
    
    if success1 and success2:
        print("\n🎉 模型定义检查完成。")
        return 0
    else:
        print("\n❌ 模型定义检查失败。")
        return 1

if __name__ == "__main__":
    sys.exit(main())