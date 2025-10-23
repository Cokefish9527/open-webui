#!/usr/bin/env python3
"""
验证Redis队列消息表修复是否成功
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def verify_fix():
    """验证修复是否成功"""
    try:
        # 导入数据库配置
        from open_webui.env import DATABASE_URL
        
        print(f"数据库URL: {DATABASE_URL}")
        
        # 检查数据库类型
        if "postgresql" in DATABASE_URL.lower():
            print("检测到PostgreSQL数据库")
            return verify_postgresql_fix(DATABASE_URL)
        elif "sqlite" in DATABASE_URL.lower():
            print("检测到SQLite数据库")
            return verify_sqlite_fix(DATABASE_URL)
        else:
            print(f"不支持的数据库类型: {DATABASE_URL}")
            return False
            
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_postgresql_fix(database_url):
    """验证PostgreSQL修复"""
    try:
        # 导入SQLAlchemy
        from sqlalchemy import create_engine, text
        
        # 创建数据库引擎
        engine = create_engine(database_url)
        
        # 检查correlation_id列是否存在
        check_column_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'redis_queue_messages' 
        AND column_name = 'correlation_id'
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(check_column_sql))
            if result.fetchone():
                print("✓ PostgreSQL: correlation_id列已存在")
            else:
                print("✗ PostgreSQL: correlation_id列不存在")
                return False
                
            # 检查数据类型
            check_types_sql = """
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_name = 'redis_queue_messages' 
            AND column_name IN ('fetched_at', 'last_executed_at', 'retry_count', 'created_at', 'updated_at')
            ORDER BY column_name
            """
            
            result = conn.execute(text(check_types_sql))
            columns = result.fetchall()
            
            print("PostgreSQL数据类型检查:")
            expected_types = {
                'fetched_at': 'timestamp with time zone',
                'last_executed_at': 'bigint',
                'retry_count': 'bigint',
                'created_at': 'timestamp with time zone',
                'updated_at': 'timestamp with time zone'
            }
            
            all_correct = True
            for col_name, actual_type in columns:
                expected_type = expected_types.get(col_name, '')
                if actual_type == expected_type:
                    print(f"  ✓ {col_name}: {actual_type}")
                else:
                    print(f"  ✗ {col_name}: 期望 {expected_type}, 实际 {actual_type}")
                    all_correct = False
                    
            return all_correct
                
    except Exception as e:
        print(f"PostgreSQL验证过程中发生错误: {e}")
        return False

def verify_sqlite_fix(database_url):
    """验证SQLite修复"""
    try:
        import sqlite3
        
        # 从数据库URL中提取数据库文件路径
        if database_url.startswith("sqlite:///"):
            db_path = database_url[10:]  # 去掉 "sqlite:///" 前缀
            
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.path.dirname(__file__), '..', 'backend', db_path)
                db_path = os.path.abspath(db_path)
                
            print(f"SQLite数据库路径: {db_path}")
            
            # 检查数据库文件是否存在
            if not os.path.exists(db_path):
                print(f"SQLite数据库文件不存在: {db_path}")
                return False
                
            # 连接数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查correlation_id列是否存在
            cursor.execute('PRAGMA table_info(redis_queue_messages)')
            columns = cursor.fetchall()
            has_correlation_id = any(col[1] == 'correlation_id' for col in columns)
            
            if has_correlation_id:
                print("✓ SQLite: correlation_id列已存在")
                conn.close()
                return True
            else:
                print("✗ SQLite: correlation_id列不存在")
                conn.close()
                return False
                
    except Exception as e:
        print(f"SQLite验证过程中发生错误: {e}")
        return False

def main():
    print("Redis队列消息表修复验证工具")
    print("=" * 40)
    
    success = verify_fix()
    if success:
        print("\n🎉 修复验证成功！Redis队列消息表已正确修复。")
        print("   - correlation_id列已添加")
        print("   - 数据类型已修正")
        return 0
    else:
        print("\n❌ 修复验证失败！Redis队列消息表可能仍有问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())