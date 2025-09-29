#!/usr/bin/env python3
"""
更新用户密码
"""

import sys
import os

# 添加项目路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# 设置环境变量
os.environ['DATABASE_URL'] = 'sqlite:///backend/data/webui.db'

try:
    import sqlite3
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def get_password_hash(password):
        return pwd_context.hash(password)
    
    # 目标用户信息
    target_email = "saiter2306@163.com"
    new_password = "123456"
    
    print(f"更新用户密码: {target_email}")
    print(f"新密码: {new_password}")
    
    # 生成新密码哈希
    new_hashed_password = get_password_hash(new_password)
    print(f"新密码哈希: {new_hashed_password}")
    
    # 验证新密码
    verify_result = pwd_context.verify(new_password, new_hashed_password)
    print(f"新密码验证结果: {verify_result}")
    
    # 数据库路径
    db_path = os.path.join(backend_dir, "data", "webui.db")
    print(f"数据库路径: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 更新用户密码
    cursor.execute(
        "UPDATE auth SET password = ? WHERE email = ?",
        (new_hashed_password, target_email)
    )
    
    if cursor.rowcount > 0:
        print("✅ 用户密码更新成功!")
        
        # 验证更新
        cursor.execute("SELECT id, email, password, active FROM auth WHERE email = ?", (target_email,))
        user_auth = cursor.fetchone()
        
        if user_auth:
            user_id, email, stored_hash, active = user_auth
            print(f"\n验证更新后的用户信息:")
            print(f"  ID: {user_id}")
            print(f"  邮箱: {email}")
            print(f"  活跃: {active}")
            print(f"  密码哈希: {stored_hash}")
            
            # 验证密码
            verify_result = pwd_context.verify(new_password, stored_hash)
            print(f"更新后密码验证结果: {verify_result}")
            
            if verify_result:
                print("✅ 更新后密码验证成功!")
            else:
                print("❌ 更新后密码验证失败!")
    else:
        print(f"❌ 未找到用户: {target_email}")
    
    conn.commit()
    conn.close()
            
except Exception as e:
    print(f"更新用户密码过程中发生错误: {e}")
    import traceback
    traceback.print_exc()