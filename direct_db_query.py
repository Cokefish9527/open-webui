import sqlite3
import os

# 数据库路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
db_path = os.path.join(backend_dir, "data", "webui.db")

print(f"数据库路径: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"\n数据库中的表:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # 查询用户表结构
    cursor.execute("PRAGMA table_info(user);")
    user_columns = cursor.fetchall()
    print(f"\n用户表结构:")
    for column in user_columns:
        print(f"  - {column[1]} ({column[2]})")
    
    # 查询认证表结构
    cursor.execute("PRAGMA table_info(auth);")
    auth_columns = cursor.fetchall()
    print(f"\n认证表结构:")
    for column in auth_columns:
        print(f"  - {column[1]} ({column[2]})")
    
    # 查询特定用户
    test_email = "saiter2306@163.com"
    print(f"\n查询用户: {test_email}")
    
    # 查询用户表
    cursor.execute("SELECT * FROM user WHERE email = ?;", (test_email,))
    user_record = cursor.fetchone()
    if user_record:
        print(f"用户表记录:")
        for i, column in enumerate(user_columns):
            print(f"  {column[1]}: {user_record[i]}")
    else:
        print(f"❌ 用户表中未找到用户: {test_email}")
    
    # 查询认证表
    cursor.execute("SELECT * FROM auth WHERE email = ?;", (test_email,))
    auth_record = cursor.fetchone()
    if auth_record:
        print(f"认证表记录:")
        for i, column in enumerate(auth_columns):
            print(f"  {column[1]}: {auth_record[i]}")
    else:
        print(f"❌ 认证表中未找到用户: {test_email}")
    
    conn.close()
    
except Exception as e:
    print(f"查询数据库时发生错误: {e}")
    import traceback
    traceback.print_exc()