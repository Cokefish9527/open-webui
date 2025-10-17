import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from open_webui.models.hsai_materials import HSAIMaterials, HSAIMaterialForm
from open_webui.env import DATA_DIR
import sqlite3
import json

print(f"Database path: {DATA_DIR}/webui.db")

# 测试数据库连接
try:
    conn = sqlite3.connect(f'{DATA_DIR}/webui.db')
    cursor = conn.cursor()
    
    # 检查表结构
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hsai_material'")
    table_exists = cursor.fetchone()
    print(f"HSAI material table exists: {table_exists is not None}")
    
    if table_exists:
        # 查看表结构
        cursor.execute("PRAGMA table_info(hsai_material)")
        columns = cursor.fetchall()
        print("HSAI material table structure:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    
    conn.close()
except Exception as e:
    print(f"Error connecting to database: {e}")

# 测试用户ID
user_id = "496e0f43-8bfa-464a-b333-7738d4b3b76d"
print(f"\nTesting with user ID: {user_id}")

# 尝试创建一个简单的素材记录
try:
    form_data = HSAIMaterialForm(
        name="test_material",
        description="Test material for debugging",
        material_type="text",
        file_path="/test/path/test.txt",
        file_size=100,
        file_hash="test_hash",
        mime_type="text/plain"
    )
    
    print("Form data created successfully")
    print(f"Form data: {form_data.model_dump()}")
    
except Exception as e:
    print(f"Error creating form data: {e}")