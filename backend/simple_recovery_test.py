#!/usr/bin/env python3
"""
简单的回收站测试脚本 - 测试修复是否生效
"""

import requests
import json

# 配置
BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"
LOGIN_EMAIL = "saiter2306@163.com"
LOGIN_PASSWORD = "123456"

def login():
    """登录获取token"""
    login_data = {
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}{API_PREFIX}/auths/signin", json=login_data)
    if response.status_code == 200:
        data = response.json()
        token = data.get("token")
        if token:
            return f"Bearer {token}" if not token.startswith("Bearer ") else token
    return None

def test_folders_with_recovery(token):
    """测试获取目录接口是否包含回收站"""
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{BASE_URL}{API_PREFIX}/hsai/materials/folders", headers=headers)
    print(f"获取目录接口状态码: {response.status_code}")
    
    if response.status_code == 200:
        folders = response.json()
        print(f"获取到 {len(folders)} 个目录")
        
        # 检查回收站
        recovery_found = any(folder.get('id') == 'recovery' for folder in folders)
        print(f"回收站虚拟目录: {'✅ 找到' if recovery_found else '❌ 未找到'}")
        
        if recovery_found:
            recovery_folder = next(folder for folder in folders if folder.get('id') == 'recovery')
            print(f"回收站信息: {json.dumps(recovery_folder, ensure_ascii=False, indent=2)}")
        
        return recovery_found
    else:
        print(f"获取目录失败: {response.text}")
        return False

def test_move_to_recovery(token):
    """测试移入回收站功能"""
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    # 获取第一个素材用于测试
    response = requests.get(f"{BASE_URL}{API_PREFIX}/hsai/materials/", headers=headers)
    if response.status_code != 200:
        print(f"获取素材列表失败: {response.status_code}")
        return False
    
    materials = response.json()
    if isinstance(materials, list) and materials:
        material = materials[0]
    elif isinstance(materials, dict) and materials.get('data'):
        material_list = materials['data']
        if not material_list:
            print("没有找到素材用于测试")
            return False
        material = material_list[0]
    else:
        print("没有找到素材用于测试")
        return False
    
    material_id = material.get('id')
    print(f"测试素材: {material.get('name')} (ID: {material_id})")
    
    # 测试移入回收站
    delete_data = {"reason": "测试移入回收站"}
    response = requests.post(
        f"{BASE_URL}{API_PREFIX}/hsai/materials/{material_id}/move-to-recovery",
        json=delete_data,
        headers=headers
    )
    
    print(f"移入回收站状态码: {response.status_code}")
    if response.status_code == 200:
        print("✅ 移入回收站成功")
        return True
    else:
        print(f"❌ 移入回收站失败: {response.text}")
        return False

def main():
    print("=== 简单回收站修复验证 ===")
    
    # 登录
    token = login()
    if not token:
        print("❌ 登录失败")
        return
    
    print("✅ 登录成功")
    
    # 测试1: 检查回收站虚拟目录
    print("\n--- 测试1: 回收站虚拟目录 ---")
    recovery_found = test_folders_with_recovery(token)
    
    # 测试2: 移入回收站
    print("\n--- 测试2: 移入回收站功能 ---")
    move_success = test_move_to_recovery(token)
    
    # 总结
    print("\n=== 测试结果汇总 ===")
    print(f"回收站虚拟目录: {'✅' if recovery_found else '❌'}")
    print(f"移入回收站功能: {'✅' if move_success else '❌'}")
    
    if recovery_found and move_success:
        print("🎉 回收站功能修复验证通过！")
    else:
        print("❌ 回收站功能仍需修复")

if __name__ == "__main__":
    main()