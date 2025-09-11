import sqlite3
from open_webui.env import DATA_DIR

print(f"Database path: {DATA_DIR}/webui.db")

# 测试数据库连接
try:
    conn = sqlite3.connect(f'{DATA_DIR}/webui.db')
    cursor = conn.cursor()
    
    # 查看hsai_materials表结构
    cursor.execute("PRAGMA table_info(hsai_materials)")
    columns = cursor.fetchall()
    print("Database table structure for hsai_materials:")
    for col in columns:
        print(f"  {col[1]} ({col[2]}) - NOT NULL: {col[3] == 1}")
    
    conn.close()
except Exception as e:
    print(f"Error connecting to database: {e}")