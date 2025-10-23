#!/usr/bin/env python3
"""
通用Redis队列消息表修复工具
自动检测数据库类型（SQLite或PostgreSQL）并添加缺失的correlation_id列
"""

import sys
import os
import sqlite3

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def fix_redis_queue_table():
    """修复Redis队列消息表，添加缺失的correlation_id列"""
    try:
        # 导入数据库配置
        from open_webui.env import DATABASE_URL
        
        print(f"数据库URL: {DATABASE_URL}")
        
        # 检查数据库类型
        if "postgresql" in DATABASE_URL.lower():
            print("检测到PostgreSQL数据库")
            return fix_postgresql_table(DATABASE_URL)
        elif "sqlite" in DATABASE_URL.lower():
            print("检测到SQLite数据库")
            return fix_sqlite_table(DATABASE_URL)
        else:
            print(f"不支持的数据库类型: {DATABASE_URL}")
            return False
            
    except Exception as e:
        print(f"修复过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_postgresql_table(database_url):
    """修复PostgreSQL数据库中的表"""
    try:
        # 导入SQLAlchemy
        from sqlalchemy import create_engine, text
        
        # 创建数据库引擎
        engine = create_engine(database_url)
        
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
                print("PostgreSQL: correlation_id列已存在，无需添加")
                return True
            else:
                print("PostgreSQL: 正在添加correlation_id列...")
                # 添加correlation_id列
                add_column_sql = """
                ALTER TABLE redis_queue_messages 
                ADD COLUMN correlation_id TEXT
                """
                conn.execute(text(add_column_sql))
                conn.commit()
                print("PostgreSQL: correlation_id列添加成功")
                return True
                
    except Exception as e:
        print(f"PostgreSQL修复过程中发生错误: {e}")
        return False

def fix_sqlite_table(database_url):
    """修复SQLite数据库中的表"""
    try:
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
            
            # 检查是否已经存在correlation_id列
            cursor.execute('PRAGMA table_info(redis_queue_messages)')
            columns = cursor.fetchall()
            has_correlation_id = any(col[1] == 'correlation_id' for col in columns)
            
            if has_correlation_id:
                print("SQLite: correlation_id列已存在，无需添加")
                conn.close()
                return True
            else:
                print("SQLite: 正在添加correlation_id列...")
                cursor.execute('ALTER TABLE redis_queue_messages ADD COLUMN correlation_id TEXT')
                conn.commit()
                print("SQLite: correlation_id列添加成功")
                conn.close()
                return True
                
    except Exception as e:
        print(f"SQLite修复过程中发生错误: {e}")
        return False

def main():
    print("通用Redis队列消息表修复工具")
    print("=" * 40)
    
    success = fix_redis_queue_table()
    if success:
        print("\n🎉 修复成功！Redis队列消息表已正确添加correlation_id列。")
        return 0
    else:
        print("\n❌ 修复失败！请检查错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())