import sqlite3
from open_webui.models.redis_queue_messages import RedisQueueMessage

# 连接到数据库
conn = sqlite3.connect('data/webui.db')
cursor = conn.cursor()

# 获取redis_queue_messages表的结构信息
cursor.execute('PRAGMA table_info(redis_queue_messages)')
columns = cursor.fetchall()

print("Redis Queue Messages table columns:")
for col in columns:
    print(f"  {col}")

# 检查模型中定义的字段是否都存在于表中
model_fields = [
    'id', 'queue_name', 'correlation_id', 'raw_data', 'fetched_at',
    'execution_result', 'error_message', 'last_executed_at', 'status',
    'retry_count', 'created_at', 'updated_at'
]

print("\n模型字段检查:")
missing_fields = []
for field in model_fields:
    exists = any(col[1] == field for col in columns)
    status = "✓" if exists else "✗"
    print(f"  {status} {field}")
    if not exists:
        missing_fields.append(field)

if missing_fields:
    print(f"\n缺少的字段: {missing_fields}")
else:
    print("\n所有模型字段都存在于数据库表中！")

# 显示表中的现有数据示例
cursor.execute('SELECT COUNT(*) FROM redis_queue_messages')
count = cursor.fetchone()[0]
print(f"\n表中记录总数: {count}")

if count > 0:
    cursor.execute('SELECT * FROM redis_queue_messages LIMIT 3')
    sample_data = cursor.fetchall()
    print("\n示例数据:")
    for i, row in enumerate(sample_data):
        print(f"  Record {i+1}: {row}")

conn.close()