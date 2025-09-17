import sqlite3
import os

# 数据库路径
db_path = r"c:\work\open-webui\backend\data\webui.db"

# 检查数据库文件是否存在
if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    exit(1)

# 连接数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询hsai_tasks表结构
cursor.execute('PRAGMA table_info(hsai_tasks)')
columns = cursor.fetchall()

print("hsai_tasks表结构:")
print("cid | name | type | notnull | dflt_value | pk")
print("-" * 50)
for col in columns:
    print(col)

# 检查是否有collaborators列
has_collaborators = any(col[1] == 'collaborators' for col in columns)
print(f"\n是否有collaborators列: {has_collaborators}")

# 关闭连接
conn.close()