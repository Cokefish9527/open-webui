#!/usr/bin/env python3
"""
直接测试数据库查询结果，不经过Pydantic模型
"""

import requests
import json
import time

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

def login_and_get_token():
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
                user_id = login_result.get("id")
                print(f"✅ 登录成功: {login_result.get('name')} ({login_result.get('email')})")
                print(f"   用户ID: {user_id}")
                return f"Bearer {token}" if not token.startswith("Bearer ") else token, user_id
            else:
                print(f"❌ 登录响应中未找到token")
                return None, None
        else:
            print(f"❌ 登录失败: {resp.status_code} - {resp.text}")
            return None, None
    except Exception as e:
        print(f"❌ 登录过程中发生错误: {str(e)}")
        return None, None

def add_debug_endpoint():
    """临时添加一个调试端点，直接返回数据库原始数据"""
    print("为了调试目的，我们需要在API中临时添加一个调试端点")
    print("这将帮助我们绕过Pydantic模型，直接查看数据库数据")
    
    debug_endpoint_code = """
@router.get("/debug/folders", summary="调试：获取原始文件夹数据")
async def debug_get_folders(user=Depends(get_verified_user)):
    \"\"\"调试端点：返回数据库原始查询结果，不经过Pydantic\"\"\"
    from open_webui.internal.db import get_db
    
    try:
        with get_db() as db:
            # 直接查询数据库
            raw_folders = db.query(HSAIMaterialFolder).filter_by(user_id=user.id).all()
            
            # 转换为字典，不使用Pydantic
            result = []
            for folder in raw_folders:
                folder_dict = {
                    "id": folder.id,
                    "name": folder.name,
                    "description": folder.description,
                    "parent_id": folder.parent_id,  # 直接访问数据库字段
                    "user_id": folder.user_id,
                    "settings": folder.settings,
                    "sort_order": folder.sort_order,
                    "created_at": folder.created_at,
                    "updated_at": folder.updated_at
                }
                result.append(folder_dict)
            
            return {
                "total": len(result),
                "folders": result,
                "debug_info": {
                    "raw_query_count": len(raw_folders),
                    "root_count": len([f for f in result if f["parent_id"] is None]),
                    "child_count": len([f for f in result if f["parent_id"] is not None])
                }
            }
    except Exception as e:
        log.exception(f"Debug endpoint error: {e}")
        return {"error": str(e)}
"""
    
    print("需要将以上代码添加到 hsai_materials.py 路由文件中")
    print("位置：在其他路由之后")
    print("\n请手动添加这个调试端点，然后我们再进行测试")

def test_with_debug_endpoint():
    """使用调试端点测试"""
    token, user_id = login_and_get_token()
    if not token:
        print("❌ 登录失败")
        return False
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    def api_url(path):
        return f"{BASE_URL}{API_PREFIX}{path}"
    
    try:
        # 调用调试端点
        print("\n🔍 调用调试端点...")
        resp = requests.get(api_url("/hsai/materials/debug/folders"), headers=headers, timeout=TEST_TIMEOUT)
        
        if resp.status_code != 200:
            print(f"❌ 调试端点失败: {resp.status_code} - {resp.text}")
            print("可能调试端点还没有添加")
            return False
        
        debug_data = resp.json()
        print(f"✅ 调试端点响应成功")
        print(f"   总文件夹数: {debug_data['total']}")
        print(f"   根文件夹数: {debug_data['debug_info']['root_count']}")
        print(f"   子文件夹数: {debug_data['debug_info']['child_count']}")
        
        # 显示一些样本数据
        print(f"\n📋 子文件夹样本 (前5个):")
        child_folders = [f for f in debug_data['folders'] if f['parent_id'] is not None]
        for i, folder in enumerate(child_folders[:5]):
            print(f"   [{i+1}] {folder['name']} (ID: {folder['id']}) -> 父目录: {folder['parent_id']}")
        
        # 对比正常API的结果
        print(f"\n📊 对比正常API结果...")
        resp_normal = requests.get(api_url("/hsai/materials/folders"), headers=headers, timeout=TEST_TIMEOUT)
        
        if resp_normal.status_code == 200:
            normal_data = resp_normal.json()
            print(f"   正常API返回的根文件夹数: {len(normal_data)}")
            
            # 检查children字段
            total_children = 0
            for folder in normal_data:
                total_children += len(folder.get('children', []))
            
            print(f"   正常API中的children总数: {total_children}")
            
            if total_children == 0 and debug_data['debug_info']['child_count'] > 0:
                print("❌ 发现问题：调试数据显示有子文件夹，但正常API中children为空")
                print("   这证实了树构建逻辑的问题")
            else:
                print("✅ 数据一致，问题可能在其他地方")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== 数据库原始数据对比测试 ===")
    
    # 首先尝试调用调试端点
    result = test_with_debug_endpoint()
    
    if not result:
        # 如果调试端点不存在，提供添加指导
        add_debug_endpoint()