import sqlite3
import os

# 获取数据库路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
data_dir = os.path.join(backend_dir, 'data')
db_path = f'{data_dir}/webui.db'

print(f"Database path: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询特定用户的认证信息
    test_email = "saiter2306@163.com"
    cursor.execute("SELECT id, email, password, active FROM auth WHERE email = ?", (test_email,))
    user = cursor.fetchone()
    if user:
        print(f"\n测试用户 {test_email} 的认证信息:")
        print(f"  ID: {user[0]}")
        print(f"  邮箱: {user[1]}")
        print(f"  密码哈希: {user[2]}")
        print(f"  活跃: {user[3]}")
    else:
        print(f"\n未找到测试用户 {test_email}")
    
    conn.close()
except Exception as e:
    print(f"查询数据库时发生错误: {e}")
    import traceback
    traceback.print_exc()