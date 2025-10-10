#!/usr/bin/env python3
"""
插入默认计费配置数据
"""

import sqlite3
import os
import time

# 数据库路径
db_path = r"data/webui.db"

# 检查数据库文件是否存在
if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    exit(1)

# 连接数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"连接到数据库: {db_path}")

# 插入默认计费配置数据
try:
    # 存储空间计费配置 (2/GB/月)
    cursor.execute("""
        INSERT OR IGNORE INTO billing_config 
        (id, config_type, config_key, config_value, description, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'storage_gb_per_month',
        'resource',
        'storage',
        '{"rate": "2", "unit": "GB/month"}',
        '存储空间计费：2积分/GB/月',
        '1',
        int(time.time()),
        int(time.time())
    ))
    
    # 第三方API调用计费配置 (0.1/次)
    cursor.execute("""
        INSERT OR IGNORE INTO billing_config 
        (id, config_type, config_key, config_value, description, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'api_call_per_request',
        'resource',
        'api_call',
        '{"rate": "0.1", "unit": "per_call"}',
        '第三方API调用计费：0.1积分/次',
        '1',
        int(time.time()),
        int(time.time())
    ))
    
    # 提交更改
    conn.commit()
    print("✓ 默认计费配置数据插入完成")
    
except Exception as e:
    print(f"✗ 插入默认计费配置数据失败: {e}")
    conn.rollback()

# 验证数据是否插入成功
try:
    cursor.execute("SELECT COUNT(*) FROM billing_config")
    count = cursor.fetchone()[0]
    print(f"billing_config表中现有记录数: {count}")
    
    cursor.execute("SELECT id, config_key, config_value, description FROM billing_config")
    rows = cursor.fetchall()
    for row in rows:
        print(f"  - {row[0]}: {row[3]}")
        
except Exception as e:
    print(f"验证数据时出错: {e}")

# 关闭连接
conn.close()

print("\n默认计费配置数据插入完成!")