import sqlite3
import os
from open_webui.env import DATA_DIR

def check_database_structure():
    db_path = os.path.join(DATA_DIR, 'webui.db')
    print(f"Database path: {db_path}")
    
    # 测试数据库连接
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查看所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("All tables in database:")
        for table in tables:
            print(f"  {table[0]}")
        
        # 查看hsai_materials表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hsai_materials'")
        material_table = cursor.fetchone()
        if material_table:
            print(f"\nStructure of hsai_materials table:")
            cursor.execute("PRAGMA table_info(hsai_materials)")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        else:
            print("\nhsai_materials table not found")
        
        # 查看hsai_tasks表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hsai_tasks'")
        tasks_table = cursor.fetchone()
        if tasks_table:
            print(f"\nStructure of hsai_tasks table:")
            cursor.execute("PRAGMA table_info(hsai_tasks)")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        else:
            print("\nhsai_tasks table not found")
            
        conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}")

if __name__ == "__main__":
    check_database_structure()