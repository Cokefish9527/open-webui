import sqlite3
from open_webui.env import DATA_DIR

print(f"Database path: {DATA_DIR}/webui.db")

try:
    conn = sqlite3.connect(f'{DATA_DIR}/webui.db')
    cursor = conn.cursor()
    
    # 查询所有用户
    cursor.execute("SELECT id, email FROM auth")
    users = cursor.fetchall()
    print("All users in database:")
    for user in users:
        print(f"  ID: {user[0]}, Email: {user[1]}")
    
    # 检查测试脚本中的用户是否存在
    test_user_id = "496e0f43-8bfa-464a-b333-7738d4b3b76d"
    cursor.execute("SELECT id, email FROM auth WHERE id = ?", (test_user_id,))
    user = cursor.fetchone()
    if user:
        print(f"\nTest user found: ID: {user[0]}, Email: {user[1]}")
    else:
        print(f"\nTest user with ID {test_user_id} not found in database")
    
    conn.close()
except Exception as e:
    print(f"Error querying database: {e}")