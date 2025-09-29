#!/usr/bin/env python3
"""
测试登录修复的脚本
"""

import sys
import os

# 添加项目路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# 设置环境变量
os.environ['DATABASE_URL'] = 'sqlite:///backend/data/webui.db'

try:
    # 直接导入需要的模块
    import sqlite3
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def verify_password(plain_password, hashed_password):
        return (
            pwd_context.verify(plain_password, hashed_password) if hashed_password else None
        )
    
    # 测试用户信息
    test_email = "saiter2306@163.com"
    test_password = "123456"
    
    print(f"测试登录用户: {test_email}")
    print(f"测试密码: {test_password}")
    
    # 直接查询数据库
    db_path = os.path.join(backend_dir, "data", "webui.db")
    print(f"数据库路径: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询用户认证信息
    cursor.execute("SELECT id, email, password, active FROM auth WHERE email = ?", (test_email,))
    user_auth = cursor.fetchone()
    
    if user_auth:
        user_id, email, hashed_password, active = user_auth
        print(f"\n找到用户认证信息:")
        print(f"  ID: {user_id}")
        print(f"  邮箱: {email}")
        print(f"  活跃: {active}")
        print(f"  密码哈希: {hashed_password}")
        
        # 尝试验证密码
        print("\n正在验证密码...")
        try:
            result = verify_password(test_password, hashed_password)
            if result:
                print("✅ 密码验证成功!")
            else:
                print("❌ 密码验证失败!")
        except Exception as e:
            print(f"密码验证时发生错误: {e}")
            print("这可能是bcrypt/passlib版本兼容性问题")
    else:
        print(f"❌ 未找到用户: {test_email}")
        
    conn.close()
            
except Exception as e:
    print(f"测试过程中发生错误: {e}")
    import traceback
    traceback.print_exc()