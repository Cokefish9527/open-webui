#!/usr/bin/env python3
"""
为PostgreSQL数据库中的redis_queue_messages表添加correlation_id列
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def add_correlation_id_column():
    """为PostgreSQL数据库添加correlation_id列"""
    try:
        # 导入数据库配置
        from open_webui.env import DATABASE_URL
        from sqlalchemy import create_engine, text
        
        print(f"数据库URL: {DATABASE_URL}")
        
        # 检查是否为PostgreSQL数据库
        if "postgresql" not in DATABASE_URL.lower():
            print("错误: 此脚本仅适用于PostgreSQL数据库")
            return False
            
        # 创建数据库引擎
        engine = create_engine(DATABASE_URL)
        
        # 检查是否已经存在correlation_id列
        check_column_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'redis_queue_messages' 
        AND column_name = 'correlation_id'
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(check_column_sql))
            if result.fetchone():
                print("correlation_id列已存在，无需添加")
                return True
            else:
                print("正在添加correlation_id列...")
                # 添加correlation_id列
                add_column_sql = """
                ALTER TABLE redis_queue_messages 
                ADD COLUMN correlation_id TEXT
                """
                conn.execute(text(add_column_sql))
                conn.commit()
                print("correlation_id列添加成功")
                
                # 验证列是否已添加
                result = conn.execute(text(check_column_sql))
                if result.fetchone():
                    print("验证成功: correlation_id列已正确添加到表中")
                    return True
                else:
                    print("验证失败: correlation_id列未正确添加")
                    return False
                    
    except Exception as e:
        print(f"添加correlation_id列时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("PostgreSQL Redis队列消息表修复工具")
    print("=" * 40)
    
    success = add_correlation_id_column()
    if success:
        print("\n🎉 修复成功！Redis队列消息表已正确添加correlation_id列。")
        return 0
    else:
        print("\n❌ 修复失败！请检查错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())