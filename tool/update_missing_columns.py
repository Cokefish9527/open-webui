#!/usr/bin/env python3
"""
更新数据库表结构，添加缺失的列
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

# 添加user表的company_id列
try:
    cursor.execute('ALTER TABLE user ADD COLUMN company_id VARCHAR(255) REFERENCES companies(id)')
    print("✓ 成功添加user表的company_id列")
except Exception as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ user表的company_id列已存在")
    else:
        print(f"✗ 添加user表的company_id列失败: {e}")

# 添加hsai_projects表的company_id列
try:
    cursor.execute('ALTER TABLE hsai_projects ADD COLUMN company_id VARCHAR(255) REFERENCES companies(id)')
    print("✓ 成功添加hsai_projects表的company_id列")
except Exception as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ hsai_projects表的company_id列已存在")
    else:
        print(f"✗ 添加hsai_projects表的company_id列失败: {e}")

# 添加hsai_tasks表的project_id列
try:
    cursor.execute('ALTER TABLE hsai_tasks ADD COLUMN project_id VARCHAR REFERENCES hsai_projects(id)')
    print("✓ 成功添加hsai_tasks表的project_id列")
except Exception as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ hsai_tasks表的project_id列已存在")
    else:
        print(f"✗ 添加hsai_tasks表的project_id列失败: {e}")

# 添加hsai_tasks表的prompt_config列
try:
    cursor.execute('ALTER TABLE hsai_tasks ADD COLUMN prompt_config JSON')
    print("✓ 成功添加hsai_tasks表的prompt_config列")
except Exception as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ hsai_tasks表的prompt_config列已存在")
    else:
        print(f"✗ 添加hsai_tasks表的prompt_config列失败: {e}")

# 提交更改
conn.commit()

# 验证列是否已添加
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

# 关闭连接
conn.close()

print("\n数据库表结构更新完成!")