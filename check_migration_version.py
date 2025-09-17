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

# 查询alembic版本表
try:
    cursor.execute('SELECT * FROM alembic_version')
    versions = cursor.fetchall()
    print("当前迁移版本:")
    for version in versions:
        print(version)
except Exception as e:
    print(f"查询alembic_version表出错: {e}")

# 查询迁移历史表（如果存在）
try:
    cursor.execute('SELECT * FROM alembic_version_history')
    history = cursor.fetchall()
    print("\n迁移历史:")
    for record in history:
        print(record)
except Exception as e:
    print(f"查询alembic_version_history表出错(可能不存在): {e}")

# 关闭连接
conn.close()