import sqlite3
from open_webui.env import DATA_DIR

print(f"Database path: {DATA_DIR}/webui.db")

try:
    conn = sqlite3.connect(f'{DATA_DIR}/webui.db')
    cursor = conn.cursor()
    
    # 查询所有素材记录
    cursor.execute("SELECT id, name, user_id FROM hsai_materials LIMIT 10")
    materials = cursor.fetchall()
    print("First 10 materials in database:")
    for material in materials:
        print(f"  ID: {material[0]}, Name: {material[1]}, User ID: {material[2]}")
    
    # 检查特定用户是否有素材记录
    user_id = "496e0f43-8bfa-464a-b333-7738d4b3b76d"
    cursor.execute("SELECT COUNT(*) FROM hsai_materials WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    print(f"\nNumber of materials for user {user_id}: {count}")
    
    conn.close()
except Exception as e:
    print(f"Error querying database: {e}")