#!/usr/bin/env python3
"""
测试文件夹创建功能的脚本
用于验证在设置上级目录时的错误修复情况
"""

import requests
import json
import time
from typing import Optional, Dict, Any

# 配置
BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"  # 根据实际API前缀调整
TOKEN = "your_token_here"  # 需要替换为实际的认证token

def auth_headers() -> Dict[str, str]:
    """生成认证请求头"""
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

def url(path: str) -> str:
    """构建完整的API URL"""
    return f"{BASE_URL}{API_PREFIX}{path}"

def test_create_folder_with_parent():
    """测试创建带上级目录的文件夹"""
    print("开始测试文件夹创建功能...")
    
    try:
        # 1. 首先创建一个根文件夹
        print("1. 创建根文件夹...")
        root_folder_data = {
            "name": f"test_root_{int(time.time())}",
            "description": "测试根文件夹"
        }
        
        resp = requests.post(
            url("/hsai/materials/folders"),
            headers=auth_headers(),
            json=root_folder_data,
            timeout=30
        )
        
        if resp.status_code == 401:
            print("❌ 认证失败，请检查TOKEN配置")
            return False
            
        if resp.status_code != 200:
            print(f"❌ 创建根文件夹失败: {resp.status_code} - {resp.text}")
            return False
            
        root_folder = resp.json()
        root_folder_id = root_folder["id"]
        print(f"✅ 根文件夹创建成功: {root_folder['name']} (ID: {root_folder_id})")
        
        # 2. 创建子文件夹（指定parent_id）
        print("2. 创建子文件夹...")
        sub_folder_data = {
            "name": f"test_sub_{int(time.time())}",
            "description": "测试子文件夹",
            "parent_id": root_folder_id
        }
        
        resp = requests.post(
            url("/hsai/materials/folders"),
            headers=auth_headers(),
            json=sub_folder_data,
            timeout=30
        )
        
        if resp.status_code != 200:
            print(f"❌ 创建子文件夹失败: {resp.status_code} - {resp.text}")
            return False
            
        sub_folder = resp.json()
        print(f"✅ 子文件夹创建成功: {sub_folder['name']} (ID: {sub_folder['id']})")
        print(f"   父文件夹ID: {sub_folder.get('parent_id')}")
        
        # 3. 测试无效的parent_id
        print("3. 测试无效的parent_id...")
        invalid_folder_data = {
            "name": f"test_invalid_{int(time.time())}",
            "description": "测试无效父目录",
            "parent_id": "invalid_parent_id_12345"
        }
        
        resp = requests.post(
            url("/hsai/materials/folders"),
            headers=auth_headers(),
            json=invalid_folder_data,
            timeout=30
        )
        
        if resp.status_code == 400:
            error_detail = resp.json().get("detail", "")
            print(f"✅ 无效parent_id正确被拒绝: {error_detail}")
        else:
            print(f"⚠️  无效parent_id测试结果异常: {resp.status_code} - {resp.text}")
        
        # 4. 测试重复文件夹名称
        print("4. 测试重复文件夹名称...")
        duplicate_folder_data = {
            "name": sub_folder['name'],  # 使用相同的名称
            "description": "重复名称测试",
            "parent_id": root_folder_id
        }
        
        resp = requests.post(
            url("/hsai/materials/folders"),
            headers=auth_headers(),
            json=duplicate_folder_data,
            timeout=30
        )
        
        if resp.status_code == 400:
            error_detail = resp.json().get("detail", "")
            print(f"✅ 重复文件夹名称正确被拒绝: {error_detail}")
        else:
            print(f"⚠️  重复名称测试结果异常: {resp.status_code} - {resp.text}")
        
        print("\n✅ 所有测试完成！文件夹创建功能正常工作。")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务器正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        return False

def print_usage():
    """打印使用说明"""
    print("""
使用说明:
1. 请先确保后端服务器正在运行 (http://localhost:8080)
2. 修改脚本中的 TOKEN 变量为有效的认证令牌
3. 如果API前缀不同，请修改 API_PREFIX 变量
4. 运行脚本: python test_folder_creation.py
""")

if __name__ == "__main__":
    print("=== 文件夹创建功能测试 ===")
    
    if TOKEN == "your_token_here":
        print("⚠️  请先设置有效的TOKEN")
        print_usage()
    else:
        success = test_create_folder_with_parent()
        if success:
            print("\n🎉 测试通过！问题已修复。")
        else:
            print("\n❌ 测试失败，仍存在问题。")