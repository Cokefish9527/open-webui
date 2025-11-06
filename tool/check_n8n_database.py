#!/usr/bin/env python3
"""
检查n8n数据库中的表结构，特别是hsai_extraction_blueprint表
"""

import sys
import os

# 添加项目根目录到Python路径
BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

def check_n8n_database():
    """检查n8n数据库结构"""
    try:
        # 导入n8n数据库配置
        from open_webui.env import N8N_DATABASE_URL
        
        print(f"n8n数据库URL: {N8N_DATABASE_URL}")
        
        # 检查数据库类型
        if "postgresql" in N8N_DATABASE_URL.lower():
            print("检测到PostgreSQL数据库")
            return check_postgresql_n8n_structure(N8N_DATABASE_URL)
        elif "sqlite" in N8N_DATABASE_URL.lower():
            print("检测到SQLite数据库")
            return check_sqlite_n8n_structure(N8N_DATABASE_URL)
        else:
            print(f"不支持的数据库类型: {N8N_DATABASE_URL}")
            return False
            
    except Exception as e:
        print(f"检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_postgresql_n8n_structure(database_url):
    """检查PostgreSQL n8n数据库表结构"""
    try:
        # 导入SQLAlchemy
        from sqlalchemy import create_engine, text
        
        # 创建数据库引擎
        engine = create_engine(database_url)
        
        # 获取所有表名
        with engine.connect() as conn:
            # 获取表名
            tables_result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
            tables = [row[0] for row in tables_result.fetchall()]
            
            print("\nPostgreSQL数据库中的表:")
            for table in tables:
                print(f"  - {table}")
                
            # 检查是否有hsai_extraction_blueprint表
            if 'hsai_extraction_blueprint' in tables:
                print("\n找到hsai_extraction_blueprint表，获取表结构...")
                
                # 获取表结构信息
                table_info_sql = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'hsai_extraction_blueprint' 
                ORDER BY ordinal_position
                """
                
                result = conn.execute(text(table_info_sql))
                columns = result.fetchall()
                
                print("\nhsai_extraction_blueprint表结构:")
                print("列名 | 数据类型 | 可空 | 默认值")
                print("-" * 50)
                for col in columns:
                    print(f"{col[0]} | {col[1]} | {col[2]} | {col[3]}")
            else:
                print("\n未找到hsai_extraction_blueprint表")
                
            return True
                
    except Exception as e:
        print(f"PostgreSQL结构检查过程中发生错误: {e}")
        return False

def check_sqlite_n8n_structure(database_url):
    """检查SQLite n8n数据库表结构"""
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
            
            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            print("\nSQLite数据库中的表:")
            for table in tables:
                print(f"  - {table}")
                
            # 检查是否有hsai_extraction_blueprint表
            if 'hsai_extraction_blueprint' in tables:
                print("\n找到hsai_extraction_blueprint表，获取表结构...")
                
                # 获取表结构信息
                cursor.execute('PRAGMA table_info(hsai_extraction_blueprint)')
                columns = cursor.fetchall()
                
                print("\nhsai_extraction_blueprint表结构:")
                print("cid | 名称 | 类型 | 非空 | 默认值 | 主键")
                print("-" * 50)
                for col in columns:
                    print(f"{col[0]} | {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
            else:
                print("\n未找到hsai_extraction_blueprint表")
                
            conn.close()
            return True
                
    except Exception as e:
        print(f"SQLite结构检查过程中发生错误: {e}")
        return False

def main():
    print("n8n数据库表结构检查工具")
    print("=" * 40)
    
    success = check_n8n_database()
    if success:
        print("\n🎉 表结构检查完成。")
        return 0
    else:
        print("\n❌ 表结构检查失败。")
        return 1

if __name__ == "__main__":
    sys.exit(main())