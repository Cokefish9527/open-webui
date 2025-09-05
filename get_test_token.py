#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取测试用JWT token的脚本
用于WebSocket连接认证
"""

import jwt
import time
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from open_webui.env import WEBUI_SECRET_KEY
except ImportError:
    # 如果无法导入，使用默认密钥
    WEBUI_SECRET_KEY = "your-secret-key-here-change-in-production"

def generate_test_token(user_id: str = "test_user_123", user_name: str = "Test User") -> str:
    """
    生成测试用JWT token
    
    Args:
        user_id: 用户ID
        user_name: 用户名
        
    Returns:
        str: JWT token
    """
    # token payload
    payload = {
        "id": user_id,
        "name": user_name,
        "email": f"{user_id}@test.com",
        "role": "user",
        "exp": int(time.time()) + 3600,  # 1小时过期
        "iat": int(time.time())
    }
    
    # 生成token
    token = jwt.encode(payload, WEBUI_SECRET_KEY, algorithm="HS256")
    return token

def main():
    """主函数"""
    print("🔐 生成测试用JWT Token")
    print("=" * 50)
    
    # 生成token
    token = generate_test_token()
    
    print(f"User ID: test_user_123")
    print(f"User Name: Test User")
    print(f"Token: {token}")
    print("=" * 50)
    print("请将此token复制到 test_full_websocket_workflow_flow.py 中的 TEST_JWT_TOKEN 变量")
    
    # 同时保存到文件供参考
    with open("test_token.txt", "w", encoding="utf-8") as f:
        f.write(token)
    
    print("Token已保存到 test_token.txt 文件")

if __name__ == "__main__":
    main()