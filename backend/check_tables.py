import sqlite3
from open_webui.env import DATA_DIR

print(f"Database path: {DATA_DIR}/webui.db")

# 测试数据库连接
try:
    conn = sqlite3.connect(f'{DATA_DIR}/webui.db')
    cursor = conn.cursor()
    
    # 查看所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("All tables in database:")
    for table in tables:
        print(f"  {table[0]}")
    
    # 检查是否有类似material的表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%material%'")
    material_tables = cursor.fetchall()
    print("\nMaterial-related tables:")
    for table in material_tables:
        print(f"  {table[0]}")
        
        # 查看表结构
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        print(f"  Structure of {table[0]}:")
        for col in columns:
            print(f"    {col[1]} ({col[2]})")
    
    conn.close()
except Exception as e:
    print(f"Error connecting to database: {e}")