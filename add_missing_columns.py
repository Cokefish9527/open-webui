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

# 添加collaborators列
try:
    cursor.execute('ALTER TABLE hsai_tasks ADD COLUMN collaborators JSON')
    print("成功添加collaborators列")
except Exception as e:
    print(f"添加collaborators列失败: {e}")

# 添加shared_sessions列
try:
    cursor.execute('ALTER TABLE hsai_tasks ADD COLUMN shared_sessions JSON')
    print("成功添加shared_sessions列")
except Exception as e:
    print(f"添加shared_sessions列失败: {e}")

# 提交更改
conn.commit()

# 验证列是否已添加
try:
    cursor.execute('PRAGMA table_info(hsai_tasks)')
    columns = cursor.fetchall()
    print("\n更新后的表结构:")
    print("cid | name | type | notnull | dflt_value | pk")
    print("-" * 50)
    for col in columns:
        print(col)
        
    # 检查是否有collaborators列
    has_collaborators = any(col[1] == 'collaborators' for col in columns)
    has_shared_sessions = any(col[1] == 'shared_sessions' for col in columns)
    print(f"\n是否有collaborators列: {has_collaborators}")
    print(f"是否有shared_sessions列: {has_shared_sessions}")
    
except Exception as e:
    print(f"查询表结构失败: {e}")

# 关闭连接
conn.close()

print("\n数据库表结构更新完成!")