#!/usr/bin/env python3
"""
调试回收站状态检查脚本
用于检查数据库中素材的实际状态
"""

import requests
import json
import time
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ['WEBUI_SECRET_KEY'] = 'your_secret_key_here'
os.environ['DATA_DIR'] = str(project_root / 'data')

from open_webui.models.hsai_materials import HSAIMaterials
from open_webui.internal.db import get_db, Base, engine
from open_webui.models.hsai_materials import HSAIMaterial

# 测试配置
BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"
LOGIN_EMAIL = "saiter2306@163.com"
LOGIN_PASSWORD = "123456"

def login_and_get_token():
    """登录并获取token"""
    login_data = {
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    }
    
    try:
        response = requests.post(f"{BASE_URL}{API_PREFIX}/auths/signin", 
                               json=login_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            token = result.get("token")
            if token and not token.startswith("Bearer "):
                token = f"Bearer {token}"
            return token, result.get("id")
        else:
            print(f"❌ 登录失败: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return None, None

def check_database_directly(user_id):
    """直接检查数据库中的素材状态"""
    print("\n=== 直接检查数据库状态 ===")
    
    try:
        with get_db() as db:
            # 查询所有素材
            all_materials = db.query(HSAIMaterial).filter_by(user_id=user_id).all()
            print(f"用户总素材数: {len(all_materials)}")
            
            # 查询活跃素材
            active_materials = db.query(HSAIMaterial).filter_by(user_id=user_id, is_deleted=False).all()
            print(f"活跃素材数: {len(active_materials)}")
            
            # 查询已删除素材
            deleted_materials = db.query(HSAIMaterial).filter_by(user_id=user_id, is_deleted=True).all()
            print(f"已删除素材数: {len(deleted_materials)}")
            
            # 详细显示素材状态
            print("\n素材详细状态:")
            for i, material in enumerate(all_materials):
                print(f"  [{i+1}] {material.name}")
                print(f"      ID: {material.id}")
                print(f"      folder_id: {material.folder_id}")
                print(f"      is_deleted: {material.is_deleted}")
                print(f"      original_directory: {material.original_directory}")
                print(f"      deleted_at: {material.deleted_at}")
                print(f"      deleted_by: {material.deleted_by}")
                print(f"      status: {material.status}")
                print()
                
    except Exception as e:
        print(f"❌ 数据库检查异常: {e}")

def check_recovery_api(token, user_id):
    """检查回收站API"""
    print("\n=== 检查回收站API ===")
    
    headers = {"Authorization": token}
    
    try:
        # 使用user_id作为enterprise_id（根据代码逻辑）
        params = {
            "enterprise_id": user_id,
            "ps": 50,
            "pi": 1
        }
        
        response = requests.get(f"{BASE_URL}{API_PREFIX}/hsai/materials/recovery/list",
                              params=params, headers=headers, timeout=30)
        
        print(f"API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            materials = result.get('data', [])
            pagination = result.get('pagination', {})
            
            print(f"API返回的回收站素材数: {len(materials)}")
            print(f"分页信息: {pagination}")
            
            for i, material in enumerate(materials):
                print(f"  [{i+1}] {material.get('name')}")
                print(f"      ID: {material.get('id')}")
                print(f"      is_deleted: {material.get('is_deleted')}")
        else:
            print(f"❌ API调用失败: {response.text}")
            
    except Exception as e:
        print(f"❌ API检查异常: {e}")

def check_folder_api(token):
    """检查文件夹列表API"""
    print("\n=== 检查文件夹列表API ===")
    
    headers = {"Authorization": token}
    
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/hsai/materials/folders",
                              headers=headers, timeout=30)
        
        print(f"文件夹API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            folders = response.json()
            print(f"根文件夹数: {len(folders)}")
            
            for folder in folders:
                print(f"  文件夹: {folder.get('name')} (ID: {folder.get('id')})")
                children = folder.get('children', [])
                if children:
                    print(f"    子文件夹数: {len(children)}")
                
                # 检查是否是回收站文件夹
                if folder.get('id') == 'recovery':
                    print(f"    📁 找到回收站虚拟目录")
        else:
            print(f"❌ 文件夹API调用失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 文件夹API检查异常: {e}")

def main():
    """主函数"""
    print("🔍 回收站状态调试检查")
    print("=" * 50)
    
    # 1. 登录获取token
    print("=== 步骤1: 登录获取token ===")
    token, user_id = login_and_get_token()
    if not token or not user_id:
        print("❌ 无法获取认证信息，退出")
        return
    
    print(f"✅ 登录成功，用户ID: {user_id}")
    
    # 2. 直接检查数据库
    check_database_directly(user_id)
    
    # 3. 检查回收站API
    check_recovery_api(token, user_id)
    
    # 4. 检查文件夹API
    check_folder_api(token)
    
    print("\n" + "=" * 50)
    print("🏁 调试检查完成")

if __name__ == "__main__":
    main()