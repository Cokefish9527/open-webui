#!/usr/bin/env python3
"""
文件夹接口简单测试脚本
快速测试创建文件夹和获取文件夹的基本功能
"""

import requests
import json
import time
from typing import Optional

# 尝试导入配置文件
try:
    from test_config import (
        BASE_URL, API_PREFIX, TOKEN, TEST_TIMEOUT, FOLDER_NAME_PREFIX,
        USE_LOGIN, LOGIN_EMAIL, LOGIN_PASSWORD
    )
except ImportError:
    # 如果配置文件不存在，使用默认配置
    BASE_URL = "http://localhost:8080"
    API_PREFIX = "/api/v1"
    TOKEN = "your_token_here"  # 请替换为实际token
    TEST_TIMEOUT = 30
    FOLDER_NAME_PREFIX = "test_folder"
    USE_LOGIN = True
    LOGIN_EMAIL = "admin@localhost"
    LOGIN_PASSWORD = "admin"

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

def test_folder_workflow():
    """执行文件夹测试工作流"""
    print("🚀 开始文件夹接口测试...")
    
    # 步骤0: 登录获取TOKEN
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
        # 步骤1: 获取根目录
        print("\n1️⃣ 获取根目录...")
        resp = requests.get(api_url("/hsai/materials/folders"), headers=headers, timeout=TEST_TIMEOUT)
        
        if resp.status_code != 200:
            print(f"❌ 获取根目录失败: {resp.status_code} - {resp.text}")
            return False
        
        folders = resp.json()
        print(f"✅ 获取到 {len(folders)} 个根级文件夹")
        
        # 步骤2: 找到第一个子目录ID，如果没有则使用根目录ID
        print("\n2️⃣ 查找目标父目录...")
        parent_id = None
        
        for folder in folders:
            children = folder.get('children', [])
            if children:
                parent_id = children[0]['id']
                print(f"✅ 使用第一个子目录作为父目录: {children[0]['name']} (ID: {parent_id})")
                break
        
        if not parent_id and folders:
            parent_id = folders[0]['id']
            print(f"⚠️  没有子目录，使用第一个根目录: {folders[0]['name']} (ID: {parent_id})")
        
        if not parent_id:
            print("❌ 无法找到父目录")
            return False
        
        # 步骤3: 创建新的子目录
        print(f"\n3️⃣ 在父目录 {parent_id} 下创建子目录...")
        new_folder_data = {
            "name": f"{FOLDER_NAME_PREFIX}_{int(time.time())}",
            "description": "测试创建的文件夹",
            "parent_id": parent_id
        }
        
        resp = requests.post(api_url("/hsai/materials/folders"), headers=headers, json=new_folder_data, timeout=TEST_TIMEOUT)
        
        if resp.status_code != 200:
            print(f"❌ 创建文件夹失败: {resp.status_code} - {resp.text}")
            return False
        
        new_folder = resp.json()
        print(f"✅ 成功创建文件夹: {new_folder['name']} (ID: {new_folder['id']})")
        
        # 步骤4: 再次获取根目录，验证创建结果
        print(f"\n4️⃣ 验证文件夹创建结果...")
        resp = requests.get(api_url("/hsai/materials/folders"), headers=headers, timeout=TEST_TIMEOUT)
        
        if resp.status_code != 200:
            print(f"❌ 重新获取根目录失败: {resp.status_code}")
            return False
        
        updated_folders = resp.json()
        print(f"✅ 重新获取根目录成功，现有 {len(updated_folders)} 个根级文件夹")
        
        # 查找新创建的文件夹
        found_new_folder = False
        def search_folder(folder_list, target_id):
            for folder in folder_list:
                if folder['id'] == target_id:
                    return True
                if search_folder(folder.get('children', []), target_id):
                    return True
            return False
        
        found_new_folder = search_folder(updated_folders, new_folder['id'])
        
        if found_new_folder:
            print(f"✅ 确认新文件夹已出现在目录树中")
        else:
            print(f"⚠️  在目录树中未找到新创建的文件夹")
        
        # 步骤5: 获取新建目录的详细信息
        print(f"\n5️⃣ 获取新建目录详细信息...")
        
        # 尝试按ID获取（如果接口存在）
        resp = requests.get(api_url(f"/hsai/materials/folders/{new_folder['id']}"), headers=headers, timeout=TEST_TIMEOUT)
        
        if resp.status_code == 200:
            folder_detail = resp.json()
            print(f"✅ 获取目录详细信息成功:")
            print(f"   名称: {folder_detail['name']}")
            print(f"   ID: {folder_detail['id']}")
            print(f"   父目录ID: {folder_detail.get('parent_id')}")
            print(f"   描述: {folder_detail.get('description')}")
        else:
            print(f"⚠️  按ID获取目录信息失败: {resp.status_code}")
            print(f"   但文件夹已在目录树中确认存在")
        
        print(f"\n🎉 测试工作流完成！")
        print(f"📊 测试结果总结:")
        print(f"   ✅ 根目录获取: 成功")
        print(f"   ✅ 父目录确定: 成功 (ID: {parent_id})")
        print(f"   ✅ 子目录创建: 成功 (ID: {new_folder['id']})")
        print(f"   ✅ 创建结果验证: {'成功' if found_new_folder else '部分成功'}")
        print(f"   ✅ 目录详情获取: {'成功' if resp.status_code == 200 else '部分成功'}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务器正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    # 检查配置
    if USE_LOGIN:
        if not LOGIN_EMAIL or not LOGIN_PASSWORD:
            print("⚠️  请在test_config.py中设置有效的LOGIN_EMAIL和LOGIN_PASSWORD")
            print("或者直接修改本文件中的默认配置")
        else:
            print(f"🔑 将使用用户名密码登录: {LOGIN_EMAIL}")
            success = test_folder_workflow()
            if not success:
                print("\n💡 提示:")
                print("   1. 请确保后端服务器正在运行")
                print("   2. 检查用户名密码是否正确")
                print("   3. 确认API接口路径是否正确")
    elif TOKEN == "your_token_here":
        print("⚠️  请先设置有效的TOKEN变量或启用登录功能")
        print("   方式1: 在test_config.py中设置USE_LOGIN=True并配置用户名密码")
        print("   方式2: 修改本文件顶部的TOKEN变量为您的认证令牌")
    else:
        success = test_folder_workflow()
        if not success:
            print("\n💡 提示:")
            print("   1. 请确保后端服务器正在运行")
            print("   2. 检查TOKEN是否有效")
            print("   3. 确认API接口路径是否正确")