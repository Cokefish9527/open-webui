import sqlite3
import os

# 数据库路径
db_path = r"data/webui.db"

# 检查数据库文件是否存在
if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    exit(1)

# 连接数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # 检查是否已经存在correlation_id列
    cursor.execute('PRAGMA table_info(redis_queue_messages)')
    columns = cursor.fetchall()
    has_correlation_id = any(col[1] == 'correlation_id' for col in columns)
    
    if has_correlation_id:
        print("correlation_id列已存在，无需添加")
    else:
        # 添加correlation_id列
        print("正在添加correlation_id列...")
        cursor.execute('ALTER TABLE redis_queue_messages ADD COLUMN correlation_id TEXT')
        conn.commit()
        print("correlation_id列添加成功")
        
        # 验证列是否已添加
        cursor.execute('PRAGMA table_info(redis_queue_messages)')
        columns = cursor.fetchall()
        print("\n更新后的表结构:")
        for col in columns:
            print(col)
            
except Exception as e:
    print(f"添加correlation_id列时出错: {e}")
    conn.rollback()
finally:
    # 关闭连接
    conn.close()