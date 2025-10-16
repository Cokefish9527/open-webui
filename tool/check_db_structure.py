import sqlite3

# 连接到SQLite数据库
conn = sqlite3.connect('d:/Work/hsch/open-webui/backend/data/webui.db')
cursor = conn.cursor()

# 获取所有表名
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tables in the database:")
for table in tables:
    print(f"- {table[0]}")

# 获取每个表的结构
for table in tables:
    table_name = table[0]
    print(f"\nStructure of table '{table_name}':")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for column in columns:
        print(f"  {column[1]} ({column[2]}) - Not Null: {bool(column[3])} - Default: {column[4]} - PK: {bool(column[5])}")

conn.close()