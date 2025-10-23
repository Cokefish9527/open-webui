import sqlite3

# 连接到数据库
conn = sqlite3.connect('data/webui.db')
cursor = conn.cursor()

# 获取redis_queue_messages表的结构信息
try:
    cursor.execute('PRAGMA table_info(redis_queue_messages)')
    columns = cursor.fetchall()
    print("Redis Queue Messages table columns:")
    for col in columns:
        print(col)
    
    # 检查是否有correlation_id列
    has_correlation_id = any(col[1] == 'correlation_id' for col in columns)
    print(f"\nHas correlation_id column: {has_correlation_id}")
    
    if not has_correlation_id:
        print("\nERROR: Missing correlation_id column!")
        print("Need to add the column to the table.")
        
        # 显示表中的现有数据示例
        cursor.execute('SELECT * FROM redis_queue_messages LIMIT 1')
        sample_data = cursor.fetchall()
        if sample_data:
            print("\nSample data from redis_queue_messages:")
            for row in sample_data:
                print(row)
        else:
            print("\nNo data found in redis_queue_messages table.")
            
except Exception as e:
    print(f"Error getting redis_queue_messages table info: {e}")

conn.close()