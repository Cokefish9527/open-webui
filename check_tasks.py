import sqlite3
import os

# 连接到数据库
db_path = r"d:\Work\hsch\open-webui\backend\data\webui.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hsai_tasks';")
    table_exists = cursor.fetchone()
    
    if table_exists:
        print("HSAI tasks table exists")
        # 查询任务数量
        cursor.execute("SELECT COUNT(*) FROM hsai_tasks;")
        count = cursor.fetchone()[0]
        print(f"Total tasks: {count}")
        
        # 查询一些任务数据
        cursor.execute("SELECT id, title, status, user_id FROM hsai_tasks LIMIT 5;")
        tasks = cursor.fetchall()
        print("Sample tasks:")
        for task in tasks:
            print(f"  ID: {task[0]}, Title: {task[1]}, Status: {task[2]}, User ID: {task[3]}")
    else:
        print("HSAI tasks table does not exist")
    
    conn.close()
else:
    print("Database file not found")