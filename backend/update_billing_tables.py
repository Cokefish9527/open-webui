#!/usr/bin/env python3
"""
更新数据库表结构，添加计费系统相关表和字段
"""

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

print(f"连接到数据库: {db_path}")

# 添加user表的company_id列（如果不存在）
try:
    cursor.execute("ALTER TABLE user ADD COLUMN company_id VARCHAR(255) REFERENCES companies(id)")
    print("✓ 成功添加user表的company_id列")
except Exception as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ user表的company_id列已存在")
    else:
        print(f"✗ 添加user表的company_id列失败: {e}")

# 添加hsai_projects表的company_id列（如果不存在）
try:
    cursor.execute("ALTER TABLE hsai_projects ADD COLUMN company_id VARCHAR(255) REFERENCES companies(id)")
    print("✓ 成功添加hsai_projects表的company_id列")
except Exception as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ hsai_projects表的company_id列已存在")
    else:
        print(f"✗ 添加hsai_projects表的company_id列失败: {e}")

# 添加hsai_tasks表的project_id列（如果不存在）
try:
    cursor.execute("ALTER TABLE hsai_tasks ADD COLUMN project_id VARCHAR(255) REFERENCES hsai_projects(id)")
    print("✓ 成功添加hsai_tasks表的project_id列")
except Exception as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ hsai_tasks表的project_id列已存在")
    else:
        print(f"✗ 添加hsai_tasks表的project_id列失败: {e}")

# 添加hsai_tasks表的prompt_config列（如果不存在）
try:
    cursor.execute("ALTER TABLE hsai_tasks ADD COLUMN prompt_config JSON")
    print("✓ 成功添加hsai_tasks表的prompt_config列")
except Exception as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ hsai_tasks表的prompt_config列已存在")
    else:
        print(f"✗ 添加hsai_tasks表的prompt_config列失败: {e}")

# 创建billing_config表（如果不存在）
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS billing_config (
            id VARCHAR NOT NULL PRIMARY KEY,
            config_type VARCHAR NOT NULL,
            config_key VARCHAR NOT NULL,
            config_value JSON NOT NULL,
            description TEXT,
            is_active VARCHAR DEFAULT '1',
            created_at BIGINT,
            updated_at BIGINT
        )
    ''')
    print("✓ 成功创建billing_config表")
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_billing_config_type ON billing_config (config_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_billing_config_key ON billing_config (config_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_billing_config_active ON billing_config (is_active)")
    print("✓ 成功创建billing_config表索引")
    
except Exception as e:
    print(f"✗ 创建billing_config表失败: {e}")

# 创建hsai_business_api_usage_log表（如果不存在）
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hsai_business_api_usage_log (
            id BIGINT NOT NULL PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT,
            service_provider VARCHAR(100) NOT NULL,
            model_name VARCHAR(100),
            credits_consumed NUMERIC(12, 6) NOT NULL DEFAULT 0,
            consumed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✓ 成功创建hsai_business_api_usage_log表")
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_user_id ON hsai_business_api_usage_log (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_session_id ON hsai_business_api_usage_log (session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_service_provider ON hsai_business_api_usage_log (service_provider)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_consumed_at ON hsai_business_api_usage_log (consumed_at)")
    print("✓ 成功创建hsai_business_api_usage_log表索引")
    
except Exception as e:
    print(f"✗ 创建hsai_business_api_usage_log表失败: {e}")

# 提交更改
conn.commit()

# 验证表和列是否已添加
print("\n验证更新后的表结构:")

# 检查user表
try:
    cursor.execute('PRAGMA table_info(user)')
    columns = cursor.fetchall()
    has_company_id = any(col[1] == 'company_id' for col in columns)
    print(f"user表是否有company_id列: {has_company_id}")
except Exception as e:
    print(f"检查user表结构失败: {e}")

# 检查hsai_projects表
try:
    cursor.execute('PRAGMA table_info(hsai_projects)')
    columns = cursor.fetchall()
    has_company_id = any(col[1] == 'company_id' for col in columns)
    print(f"hsai_projects表是否有company_id列: {has_company_id}")
except Exception as e:
    print(f"检查hsai_projects表结构失败: {e}")

# 检查hsai_tasks表
try:
    cursor.execute('PRAGMA table_info(hsai_tasks)')
    columns = cursor.fetchall()
    has_project_id = any(col[1] == 'project_id' for col in columns)
    has_prompt_config = any(col[1] == 'prompt_config' for col in columns)
    print(f"hsai_tasks表是否有project_id列: {has_project_id}")
    print(f"hsai_tasks表是否有prompt_config列: {has_prompt_config}")
except Exception as e:
    print(f"检查hsai_tasks表结构失败: {e}")

# 检查billing_config表
try:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='billing_config'")
    result = cursor.fetchone()
    print(f"billing_config表是否存在: {result is not None}")
except Exception as e:
    print(f"检查billing_config表失败: {e}")

# 检查hsai_business_api_usage_log表
try:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hsai_business_api_usage_log'")
    result = cursor.fetchone()
    print(f"hsai_business_api_usage_log表是否存在: {result is not None}")
except Exception as e:
    print(f"检查hsai_business_api_usage_log表失败: {e}")

# 关闭连接
conn.close()

print("\n数据库表结构更新完成!")