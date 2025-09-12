#!/usr/bin/env python3
"""
验证回收站修复的简化测试
"""

import requests
import json

# 配置
BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"
EMAIL = "saiter2306@163.com"
PASSWORD = "123456"

def main():
    print("=== 回收站修复验证 ===")
    
    # 步骤1：登录
    print("1. 登录...")
    login_response = requests.post(
        f"{BASE_URL}{API_PREFIX}/auths/signin",
        json={"email": EMAIL, "password": PASSWORD}
    )
    
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code}")
        return
    
    token = login_response.json().get("token")
    if not token:
        print("❌ 未获取到token")
        return
    
    print("✅ 登录成功")
    
    headers = {
        "Authorization": f"Bearer {token}" if not token.startswith("Bearer ") else token,
        "Content-Type": "application/json"
    }
    
    # 步骤2：检查目录接口（回收站虚拟目录）
    print("\n2. 检查目录接口...")
    folders_response = requests.get(
        f"{BASE_URL}{API_PREFIX}/hsai/materials/folders",
        headers=headers
    )
    
    if folders_response.status_code != 200:
        print(f"❌ 获取目录失败: {folders_response.status_code}")
        return
    
    folders = folders_response.json()
    recovery_found = any(folder.get('id') == 'recovery' for folder in folders)
    
    print(f"{'✅' if recovery_found else '❌'} 回收站虚拟目录: {'已添加' if recovery_found else '未找到'}")
    
    if recovery_found:
        recovery_folder = next(folder for folder in folders if folder.get('id') == 'recovery')
        print(f"   回收站信息: {recovery_folder.get('name')}")
    
    # 步骤3：测试移入回收站（如果有素材的话）
    print("\n3. 测试移入回收站...")
    materials_response = requests.get(
        f"{BASE_URL}{API_PREFIX}/hsai/materials/",
        headers=headers
    )
    
    if materials_response.status_code == 200:
        materials_data = materials_response.json()
        materials = []
        
        if isinstance(materials_data, list):
            materials = materials_data
        elif isinstance(materials_data, dict) and 'data' in materials_data:
            materials = materials_data['data']
        
        if materials:
            # 使用第一个素材测试
            test_material = materials[0]
            material_id = test_material.get('id')
            
            print(f"   测试素材: {test_material.get('name')} (ID: {material_id})")
            
            move_response = requests.post(
                f"{BASE_URL}{API_PREFIX}/hsai/materials/{material_id}/move-to-recovery",
                json={"reason": "测试回收站功能"},
                headers=headers
            )
            
            if move_response.status_code == 200:
                print("✅ 移入回收站成功")
                
                # 测试还原
                print("\n4. 测试还原素材...")
                restore_response = requests.post(
                    f"{BASE_URL}{API_PREFIX}/hsai/materials/recovery/{material_id}/restore",
                    json={},  # 不传递target_directory参数
                    headers=headers
                )
                
                if restore_response.status_code == 200:
                    print("✅ 还原素材成功")
                else:
                    print(f"❌ 还原失败: {restore_response.status_code} - {restore_response.text}")
                    
            else:
                print(f"❌ 移入回收站失败: {move_response.status_code} - {move_response.text}")
        else:
            print("   没有素材可供测试")
    else:
        print(f"   获取素材列表失败: {materials_response.status_code}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()