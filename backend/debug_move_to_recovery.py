#!/usr/bin/env python3
"""
调试移入回收站接口的500错误
"""

import requests
import json
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)

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

def get_headers(token):
    """获取请求头"""
    return {
        "Authorization": token,
        "Content-Type": "application/json"
    }

def get_first_material(token):
    """获取第一个素材"""
    headers = get_headers(token)
    
    # 获取素材列表
    response = requests.get(f"{BASE_URL}{API_PREFIX}/hsai/materials/", headers=headers)
    if response.status_code == 200:
        materials = response.json()
        if isinstance(materials, list) and materials:
            return materials[0]
        elif isinstance(materials, dict) and materials.get('data'):
            data = materials['data']
            if data:
                return data[0]
    
    print(f"获取素材列表失败: {response.status_code} - {response.text}")
    return None

def test_move_to_recovery(token, material_id):
    """测试移入回收站"""
    headers = get_headers(token)
    
    # 先获取素材详情
    print(f"获取素材详情: {material_id}")
    response = requests.get(f"{BASE_URL}{API_PREFIX}/hsai/materials/{material_id}", headers=headers)
    if response.status_code == 200:
        material = response.json()
        print(f"素材信息: {json.dumps(material, ensure_ascii=False, indent=2)}")
    else:
        print(f"获取素材详情失败: {response.status_code} - {response.text}")
    
    # 测试移入回收站
    print(f"\n测试移入回收站: {material_id}")
    delete_data = {"reason": "测试移入回收站"}
    
    response = requests.post(
        f"{BASE_URL}{API_PREFIX}/hsai/materials/{material_id}/move-to-recovery",
        json=delete_data,
        headers=headers
    )
    
    print(f"响应状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    print(f"响应内容: {response.text}")
    
    if response.status_code != 200:
        print(f"移入回收站失败!")
    else:
        print("移入回收站成功!")

def main():
    print("=== 调试移入回收站接口 ===")
    
    # 登录
    token = login()
    if not token:
        print("登录失败")
        return
    
    print("登录成功")
    
    # 获取第一个素材
    material = get_first_material(token)
    if not material:
        print("没有找到素材")
        return
    
    material_id = material.get('id')
    print(f"找到素材: {material.get('name')} (ID: {material_id})")
    
    # 测试移入回收站
    test_move_to_recovery(token, material_id)

if __name__ == "__main__":
    main()