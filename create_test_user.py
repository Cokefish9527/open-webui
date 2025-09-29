#!/usr/bin/env python3
"""
创建测试用户
"""

import sys
import os
import uuid

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
    
    # 测试用户信息
    test_email = "test@example.com"
    test_password = "123456"
    test_name = "Test User"
    
    print(f"创建测试用户: {test_email}")
    print(f"测试密码: {test_password}")
    
    # 生成密码哈希
    hashed_password = get_password_hash(test_password)
    print(f"生成的密码哈希: {hashed_password}")
    
    # 验证密码
    verify_result = pwd_context.verify(test_password, hashed_password)
    print(f"密码验证结果: {verify_result}")
    
    # 数据库路径
    db_path = os.path.join(backend_dir, "data", "webui.db")
    print(f"数据库路径: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查用户是否已存在
    cursor.execute("SELECT id FROM auth WHERE email = ?", (test_email,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        print(f"用户 {test_email} 已存在，删除旧记录...")
        user_id = existing_user[0]
        cursor.execute("DELETE FROM auth WHERE id = ?", (user_id,))
        cursor.execute("DELETE FROM user WHERE id = ?", (user_id,))
    
    # 创建新用户
    user_id = str(uuid.uuid4())
    print(f"新用户ID: {user_id}")
    
    # 插入认证记录
    cursor.execute(
        "INSERT INTO auth (id, email, password, active) VALUES (?, ?, ?, ?)",
        (user_id, test_email, hashed_password, 1)
    )
    
    # 插入用户记录
    import time
    current_time = int(time.time())
    cursor.execute(
        "INSERT INTO user (id, name, email, role, profile_image_url, last_active_at, updated_at, created_at, info_collection_completed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, test_name, test_email, "user", "/user.png", current_time, current_time, current_time, 0)
    )
    
    conn.commit()
    print("✅ 用户创建成功!")
    
    # 验证用户创建
    cursor.execute("SELECT id, email, password, active FROM auth WHERE email = ?", (test_email,))
    user_auth = cursor.fetchone()
    
    if user_auth:
        user_id, email, stored_hash, active = user_auth
        print(f"\n验证用户信息:")
        print(f"  ID: {user_id}")
        print(f"  邮箱: {email}")
        print(f"  活跃: {active}")
        print(f"  密码哈希: {stored_hash}")
        
        # 验证密码
        verify_result = pwd_context.verify(test_password, stored_hash)
        print(f"密码验证结果: {verify_result}")
        
        if verify_result:
            print("✅ 密码验证成功!")
        else:
            print("❌ 密码验证失败!")
    
    conn.close()
            
except Exception as e:
    print(f"创建用户过程中发生错误: {e}")
    import traceback
    traceback.print_exc()