#!/usr/bin/env python3
"""
检查Redis队列消息表的完整结构
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def check_table_structure():
    """检查表结构"""
    try:
        # 导入数据库配置
        from open_webui.env import DATABASE_URL
        
        print(f"数据库URL: {DATABASE_URL}")
        
        # 检查数据库类型
        if "postgresql" in DATABASE_URL.lower():
            print("检测到PostgreSQL数据库")
            return check_postgresql_structure(DATABASE_URL)
        elif "sqlite" in DATABASE_URL.lower():
            print("检测到SQLite数据库")
            return check_sqlite_structure(DATABASE_URL)
        else:
            print(f"不支持的数据库类型: {DATABASE_URL}")
            return False
            
    except Exception as e:
        print(f"检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_postgresql_structure(database_url):
    """检查PostgreSQL数据库表结构"""
    try:
        # 导入SQLAlchemy
        from sqlalchemy import create_engine, text
        
        # 创建数据库引擎
        engine = create_engine(database_url)
        
        # 获取表结构信息
        table_info_sql = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'redis_queue_messages' 
        ORDER BY ordinal_position
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(table_info_sql))
            columns = result.fetchall()
            
            print("\nPostgreSQL表结构:")
            print("列名 | 数据类型 | 可空 | 默认值")
            print("-" * 50)
            for col in columns:
                print(f"{col[0]} | {col[1]} | {col[2]} | {col[3]}")
                
            return True
                
    except Exception as e:
        print(f"PostgreSQL结构检查过程中发生错误: {e}")
        return False

def check_sqlite_structure(database_url):
    """检查SQLite数据库表结构"""
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
            
            # 获取表结构信息
            cursor.execute('PRAGMA table_info(redis_queue_messages)')
            columns = cursor.fetchall()
            
            print("\nSQLite表结构:")
            print("cid | 名称 | 类型 | 非空 | 默认值 | 主键")
            print("-" * 50)
            for col in columns:
                print(f"{col[0]} | {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
                
            conn.close()
            return True
                
    except Exception as e:
        print(f"SQLite结构检查过程中发生错误: {e}")
        return False

def main():
    print("Redis队列消息表结构检查工具")
    print("=" * 40)
    
    success = check_table_structure()
    if success:
        print("\n🎉 表结构检查完成。")
        return 0
    else:
        print("\n❌ 表结构检查失败。")
        return 1

if __name__ == "__main__":
    sys.exit(main())