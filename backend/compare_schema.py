import sqlite3
from open_webui.env import DATA_DIR

print(f"Database path: {DATA_DIR}/webui.db")

# 测试数据库连接
try:
    conn = sqlite3.connect(f'{DATA_DIR}/webui.db')
    cursor = conn.cursor()
    
    # 查看hsai_materials表结构
    cursor.execute("PRAGMA table_info(hsai_materials)")
    columns = cursor.fetchall()
    print("Database table structure for hsai_materials:")
    db_columns = {}
    for col in columns:
        print(f"  {col[1]} ({col[2]}) - NOT NULL: {col[3] == 1}")
        db_columns[col[1]] = {"type": col[2], "not_null": col[3] == 1}
    
    conn.close()
    
    # 检查模型定义中的字段
    print("\nModel fields (from code):")
    model_fields = {
        "id": "VARCHAR",
        "name": "VARCHAR",
        "description": "TEXT",
        "material_type": "VARCHAR",
        "folder_id": "VARCHAR",
        "user_id": "VARCHAR",
        "file_path": "VARCHAR",
        "file_size": "BIGINT",
        "file_hash": "VARCHAR",
        "mime_type": "VARCHAR",
        "material_metadata": "JSON",
        "tags": "JSON",
        "ai_analysis": "JSON",
        "usage_count": "BIGINT",
        "last_used_at": "BIGINT",
        "status": "VARCHAR",
        "access_control": "JSON",
        "scene_code": "VARCHAR",
        "technique_code": "VARCHAR",
        "properties_code": "VARCHAR",
        "duration": "INTEGER",
        "resolution": "VARCHAR",
        "oss_bucket": "VARCHAR",
        "oss_key": "VARCHAR",
        "is_deleted": "BOOLEAN",
        "original_directory": "VARCHAR",
        "deleted_at": "BIGINT",
        "deleted_by": "VARCHAR",
        "created_at": "BIGINT",
        "updated_at": "BIGINT"
    }
    
    for field, type_info in model_fields.items():
        print(f"  {field} ({type_info})")
    
    # 检查差异
    print("\nDifferences:")
    for field, type_info in model_fields.items():
        if field not in db_columns:
            print(f"  Missing in DB: {field}")
        else:
            db_type = db_columns[field]["type"]
            # 简单类型映射检查
            type_mapping = {
                "VARCHAR": ["VARCHAR", "TEXT"],
                "TEXT": ["TEXT", "VARCHAR"],
                "BIGINT": ["BIGINT", "INTEGER"],
                "INTEGER": ["INTEGER", "BIGINT"],
                "BOOLEAN": ["BOOLEAN", "INTEGER"]
            }
            
            expected_types = type_mapping.get(type_info, [type_info])
            if db_type not in expected_types:
                print(f"  Type mismatch for {field}: DB={db_type}, Model={type_info}")
    
    for db_field in db_columns:
        if db_field not in model_fields:
            print(f"  Extra in DB: {db_field}")
            
except Exception as e:
    print(f"Error comparing schema: {e}")