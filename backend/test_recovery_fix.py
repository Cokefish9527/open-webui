#!/usr/bin/env python3
"""
回收站功能修复验证脚本
测试移入回收站和回收站查询功能
"""

import requests
import json
import time

# 测试配置
BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"
LOGIN_EMAIL = "saiter2306@163.com"
LOGIN_PASSWORD = "123456"
TIMEOUT = 30

def login():
    """登录获取token"""
    print("=== 登录获取token ===")
    
    login_data = {
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    }
    
    try:
        response = requests.post(f"{BASE_URL}{API_PREFIX}/auths/signin", 
                               json=login_data, timeout=TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            token = result.get("token")
            if token and not token.startswith("Bearer "):
                token = f"Bearer {token}"
            user_id = result.get("id")
            print(f"✅ 登录成功，用户ID: {user_id}")
            return token, user_id
        else:
            print(f"❌ 登录失败: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return None, None

def get_materials(token):
    """获取用户的素材列表"""
    print("\n=== 获取素材列表 ===")
    
    headers = {"Authorization": token}
    
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/hsai/materials/",
                              headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            materials = result.get('data', [])
            print(f"✅ 获取到 {len(materials)} 个素材")
            
            # 返回第一个素材用于测试
            if materials:
                first_material = materials[0]
                print(f"   第一个素材: {first_material.get('name')} (ID: {first_material.get('id')})")
                return first_material.get('id')
            else:
                print("⚠️  没有找到任何素材")
                return None
        else:
            print(f"❌ 获取素材失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 获取素材异常: {e}")
        return None

def move_to_recovery(token, material_id):
    """移入回收站"""
    print(f"\n=== 移入回收站 (素材ID: {material_id}) ===")
    
    headers = {"Authorization": token, "Content-Type": "application/json"}
    data = {"reason": "测试移入回收站"}
    
    try:
        response = requests.post(f"{BASE_URL}{API_PREFIX}/hsai/materials/{material_id}/move-to-recovery",
                               json=data, headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            print("✅ 成功移入回收站")
            return True
        else:
            print(f"❌ 移入回收站失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 移入回收站异常: {e}")
        return False

def check_recovery_list(token):
    """检查回收站列表"""
    print("\n=== 检查回收站列表 ===")
    
    headers = {"Authorization": token}
    
    try:
        # 注意：修复后的接口不再需要enterprise_id参数
        params = {
            "ps": 50,
            "pi": 1
        }
        
        response = requests.get(f"{BASE_URL}{API_PREFIX}/hsai/materials/recovery/list",
                              params=params, headers=headers, timeout=TIMEOUT)
        
        print(f"API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            materials = result.get('data', [])
            pagination = result.get('pagination', {})
            
            print(f"✅ 回收站中有 {len(materials)} 个素材")
            print(f"   分页信息: 总计 {pagination.get('total', 0)} 个")
            
            for i, material in enumerate(materials):
                print(f"   [{i+1}] {material.get('name')} (ID: {material.get('id')})")
                print(f"       is_deleted: {material.get('is_deleted')}")
                print(f"       deleted_at: {material.get('deleted_at')}")
            
            return len(materials) > 0
        else:
            print(f"❌ 获取回收站列表失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 检查回收站异常: {e}")
        return False

def main():
    """主函数"""
    print("🔧 回收站功能修复验证")
    print("=" * 50)
    
    # 1. 登录
    token, user_id = login()
    if not token:
        print("❌ 登录失败，无法继续测试")
        return
    
    # 2. 获取素材列表
    material_id = get_materials(token)
    if not material_id:
        print("❌ 没有可用的素材进行测试")
        return
    
    # 3. 移入回收站
    if not move_to_recovery(token, material_id):
        print("❌ 移入回收站失败")
        return
    
    # 4. 检查回收站列表
    if check_recovery_list(token):
        print("\n🎉 回收站功能修复验证成功！")
        print("✅ 移入回收站功能正常")
        print("✅ 回收站查询功能正常")
    else:
        print("\n❌ 回收站功能仍然存在问题")
        print("   可能原因：")
        print("   1. 数据库表结构缺少 is_deleted 字段")
        print("   2. 素材更新逻辑存在问题")
        print("   3. 回收站查询逻辑存在问题")
    
    print("\n" + "=" * 50)
    print("🏁 验证完成")

if __name__ == "__main__":
    main()