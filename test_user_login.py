#!/usr/bin/env python3
"""
测试用户登录凭据
"""

import sys
import os
import requests

# 添加项目路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

try:
    # 测试用户凭据
    test_users = [
        {"email": "saiter2306@163.com", "password": "123456"},
        {"email": "saiter2306001@163.com", "password": "123456"}
    ]
    
    base_url = "http://localhost:8080"
    
    print("测试用户登录凭据:")
    print("=" * 50)
    
    for user in test_users:
        print(f"\n测试用户: {user['email']}")
        
        try:
            # 尝试登录
            response = requests.post(
                f"{base_url}/api/v1/auths/signin",
                json={
                    "email": user["email"],
                    "password": user["password"]
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ 登录成功!")
                print(f"  用户ID: {data.get('id')}")
                print(f"  用户名: {data.get('name')}")
                print(f"  角色: {data.get('role')}")
            else:
                print(f"❌ 登录失败! 状态码: {response.status_code}")
                if response.text:
                    try:
                        error_data = response.json()
                        print(f"  错误信息: {error_data.get('detail', '未知错误')}")
                    except:
                        print(f"  错误信息: {response.text}")
                        
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            
    print("\n" + "=" * 50)
    print("测试完成")
            
except Exception as e:
    print(f"测试过程中发生错误: {e}")
    import traceback
    traceback.print_exc()