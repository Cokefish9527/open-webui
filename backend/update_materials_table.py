import sqlite3
from open_webui.env import DATA_DIR

print(f"Database path: {DATA_DIR}/webui.db")

try:
    conn = sqlite3.connect(f'{DATA_DIR}/webui.db')
    cursor = conn.cursor()
    
    # 重命名metadata字段为material_metadata
    try:
        cursor.execute("ALTER TABLE hsai_materials RENAME COLUMN metadata TO material_metadata")
        print("Renamed metadata column to material_metadata")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column material_metadata already exists")
        else:
            print(f"Error renaming metadata column: {e}")
    
    # 添加缺失的字段
    new_columns = [
        ("scene_code", "VARCHAR"),
        ("technique_code", "VARCHAR"),
        ("properties_code", "VARCHAR"),
        ("duration", "INTEGER"),
        ("resolution", "VARCHAR"),
        ("oss_bucket", "VARCHAR"),
        ("oss_key", "VARCHAR"),
        ("is_deleted", "BOOLEAN"),
        ("original_directory", "VARCHAR"),
        ("deleted_at", "BIGINT"),
        ("deleted_by", "VARCHAR")
    ]
    
    for column_name, column_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE hsai_materials ADD COLUMN {column_name} {column_type}")
            print(f"Added column {column_name} ({column_type})")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {column_name} already exists")
            else:
                print(f"Error adding column {column_name}: {e}")
    
    conn.commit()
    conn.close()
    print("Database schema updated successfully")
    
except Exception as e:
    print(f"Error updating database schema: {e}")