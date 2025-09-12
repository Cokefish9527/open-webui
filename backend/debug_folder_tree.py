#!/usr/bin/env python3
"""
专门诊断文件夹树构建问题的脚本
"""

import requests
import json
import time
from typing import Optional

# 尝试导入配置文件
try:
    from test_config import (
        BASE_URL, API_PREFIX, TOKEN, TEST_TIMEOUT,
        USE_LOGIN, LOGIN_EMAIL, LOGIN_PASSWORD
    )
except ImportError:
    BASE_URL = "http://localhost:8080"
    API_PREFIX = "/api/v1"
    TOKEN = "your_token_here"
    TEST_TIMEOUT = 30
    USE_LOGIN = True
    LOGIN_EMAIL = "saiter2306@163.com"
    LOGIN_PASSWORD = "123456"

def login_and_get_token() -> Optional[str]:
    """登录获取TOKEN"""
    if not USE_LOGIN:
        return TOKEN
        
    print("🔑 正在登录...")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    login_data = {
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    }
    
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auths/signin",
            headers=headers,
            json=login_data,
            timeout=TEST_TIMEOUT
        )
        
        if resp.status_code == 200:
            login_result = resp.json()
            token = login_result.get("token")
            if token:
                print(f"✅ 登录成功: {login_result.get('name')} ({login_result.get('email')})")
                return f"Bearer {token}" if not token.startswith("Bearer ") else token
            else:
                print(f"❌ 登录响应中未找到token")
                return None
        else:
            print(f"❌ 登录失败: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"❌ 登录过程中发生错误: {str(e)}")
        return None

def test_folder_tree_construction():
    """测试文件夹树构建逻辑"""
    print("=== 文件夹树构建诊断 ===")
    
    # 登录获取token
    token = login_and_get_token()
    if not token:
        print("❌ 登录失败，测试终止")
        return False
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    def api_url(path):
        return f"{BASE_URL}{API_PREFIX}{path}"
    
    try:
        # 步骤1: 创建一个根文件夹
        print("\n1️⃣ 创建根文件夹...")
        root_folder_data = {
            "name": f"debug_root_{int(time.time())}",
            "description": "调试用根文件夹"
        }
        
        resp = requests.post(api_url("/hsai/materials/folders"), headers=headers, json=root_folder_data, timeout=TEST_TIMEOUT)
        
        if resp.status_code != 200:
            print(f"❌ 创建根文件夹失败: {resp.status_code} - {resp.text}")
            return False
        
        root_folder = resp.json()
        root_folder_id = root_folder["id"]
        print(f"✅ 根文件夹创建成功: {root_folder['name']} (ID: {root_folder_id})")
        
        # 步骤2: 创建子文件夹
        print("\n2️⃣ 创建子文件夹...")
        sub_folder_data = {
            "name": f"debug_sub_{int(time.time())}",
            "description": "调试用子文件夹",
            "parent_id": root_folder_id
        }
        
        resp = requests.post(api_url("/hsai/materials/folders"), headers=headers, json=sub_folder_data, timeout=TEST_TIMEOUT)
        
        if resp.status_code != 200:
            print(f"❌ 创建子文件夹失败: {resp.status_code} - {resp.text}")
            return False
        
        sub_folder = resp.json()
        sub_folder_id = sub_folder["id"]
        print(f"✅ 子文件夹创建成功: {sub_folder['name']} (ID: {sub_folder_id})")
        print(f"   指定的父文件夹ID: {sub_folder.get('parent_id')}")
        
        # 步骤3: 获取目录树并分析
        print("\n3️⃣ 获取目录树并分析...")
        resp = requests.get(api_url("/hsai/materials/folders"), headers=headers, timeout=TEST_TIMEOUT)
        
        if resp.status_code != 200:
            print(f"❌ 获取目录树失败: {resp.status_code} - {resp.text}")
            return False
        
        folders = resp.json()
        print(f"✅ 获取目录树成功，共 {len(folders)} 个根级文件夹")
        
        # 查找我们刚创建的根文件夹
        found_root = None
        found_sub_in_tree = None
        
        for folder in folders:
            if folder['id'] == root_folder_id:
                found_root = folder
                print(f"🔍 找到根文件夹: {folder['name']} (ID: {folder['id']})")
                print(f"   子文件夹数量: {len(folder.get('children', []))}")
                
                # 检查子文件夹
                for child in folder.get('children', []):
                    print(f"   └── 子文件夹: {child['name']} (ID: {child['id']})")
                    if child['id'] == sub_folder_id:
                        found_sub_in_tree = child
                        print(f"       ✅ 找到刚创建的子文件夹!")
                break
        
        if not found_root:
            print(f"❌ 在目录树中未找到根文件夹 {root_folder_id}")
            return False
            
        if not found_sub_in_tree:
            print(f"❌ 在目录树中未找到子文件夹 {sub_folder_id}")
            print(f"   根文件夹的children: {found_root.get('children', [])}")
            
            # 进一步诊断：检查是否是数据库问题
            print("\n🔍 进一步诊断...")
            
            # 检查数据库中的实际数据
            print("📊 检查当前所有文件夹的父子关系...")
            all_folders_by_id = {}
            root_count = 0
            child_count = 0
            
            for folder in folders:
                all_folders_by_id[folder['id']] = folder
                if folder.get('parent_id') is None:
                    root_count += 1
                else:
                    child_count += 1
                    parent_id = folder.get('parent_id')
                    print(f"   子文件夹 {folder['name']} ({folder['id']}) -> 父文件夹 {parent_id}")
                    
                    # 检查父文件夹是否存在
                    parent_in_response = any(f['id'] == parent_id for f in folders)
                    if not parent_in_response:
                        print(f"     ⚠️  父文件夹 {parent_id} 不在响应中!")
            
            print(f"📊 统计: {root_count} 个根文件夹, {child_count} 个子文件夹")
            
            return False
        else:
            print(f"✅ 文件夹树构建正确！")
            return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    test_folder_tree_construction()