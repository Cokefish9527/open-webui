import sqlite3
import os
from passlib.context import CryptContext

# 设置密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 数据库路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
db_path = os.path.join(backend_dir, "data", "webui.db")

print(f"数据库路径: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询用户
    test_users = [
        "saiter2306@163.com",
        "saiter2306001@163.com"
    ]
    
    for email in test_users:
        print(f"\n检查用户: {email}")
        
        # 查询认证表
        cursor.execute("SELECT id, email, password, active FROM auth WHERE email = ?", (email,))
        auth_record = cursor.fetchone()
        
        if auth_record:
            user_id, email, hashed_password, active = auth_record
            print(f"  认证记录:")
            print(f"    ID: {user_id}")
            print(f"    邮箱: {email}")
            print(f"    活跃: {active}")
            print(f"    密码哈希: {hashed_password}")
            
            # 验证密码
            try:
                result = pwd_context.verify("123456", hashed_password)
                print(f"    密码验证: {'✅ 成功' if result else '❌ 失败'}")
            except Exception as e:
                print(f"    密码验证错误: {e}")
        else:
            print(f"  ❌ 未找到认证记录")
            
        # 查询用户表
        cursor.execute("SELECT id, email, name, role FROM user WHERE email = ?", (email,))
        user_record = cursor.fetchone()
        
        if user_record:
            user_id, email, name, role = user_record
            print(f"  用户记录:")
            print(f"    ID: {user_id}")
            print(f"    邮箱: {email}")
            print(f"    姓名: {name}")
            print(f"    角色: {role}")
        else:
            print(f"  ❌ 未找到用户记录")
    
    conn.close()
    
except Exception as e:
    print(f"查询数据库时发生错误: {e}")
    import traceback
    traceback.print_exc()