#!/usr/bin/env python3
"""
回收站功能调试脚本
跟踪控制台输出，定位问题所在
"""

import requests
import json
import sys
import traceback

# 配置
BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"
LOGIN_EMAIL = "saiter2306@163.com"
LOGIN_PASSWORD = "123456"

def log_response(step, response):
    """记录响应详情"""
    print(f"\n[{step}] 响应状态码: {response.status_code}")
    print(f"[{step}] 响应头: {dict(response.headers)}")
    try:
        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            print(f"[{step}] 响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"[{step}] 响应内容: {response.text[:500]}...")
    except:
        print(f"[{step}] 响应原始内容: {response.text[:500]}...")

def test_connection():
    """测试服务器连接"""
    print("=== 1. 测试服务器连接 ===")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        log_response("连接测试", response)
        return response.status_code in [200, 404]  # 404也说明服务器在运行
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_login():
    """测试登录功能"""
    print("\n=== 2. 测试登录功能 ===")
    login_data = {
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    }
    
    try:
        response = requests.post(f"{BASE_URL}{API_PREFIX}/auths/signin", 
                                json=login_data, timeout=10)
        log_response("登录", response)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            if token:
                print(f"✅ 登录成功，获取到token")
                return f"Bearer {token}" if not token.startswith("Bearer ") else token
            else:
                print("❌ 登录响应中未找到token")
                return None
        else:
            print(f"❌ 登录失败")
            return None
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        traceback.print_exc()
        return None

def test_folders_api(token):
    """测试获取目录接口"""
    print("\n=== 3. 测试获取目录接口 ===")
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/hsai/materials/folders", 
                              headers=headers, timeout=10)
        log_response("获取目录", response)
        
        if response.status_code == 200:
            folders = response.json()
            print(f"✅ 成功获取 {len(folders)} 个目录")
            
            # 检查回收站虚拟目录
            recovery_found = False
            for folder in folders:
                if folder.get('id') == 'recovery':
                    recovery_found = True
                    print(f"✅ 找到回收站虚拟目录: {folder.get('name')}")
                    break
            
            if not recovery_found:
                print("❌ 未找到回收站虚拟目录")
                print("目录列表:")
                for i, folder in enumerate(folders):
                    print(f"  [{i+1}] {folder.get('name')} (ID: {folder.get('id')})")
            
            return folders, recovery_found
        else:
            print(f"❌ 获取目录失败")
            return [], False
            
    except Exception as e:
        print(f"❌ 获取目录异常: {e}")
        traceback.print_exc()
        return [], False

def test_materials_list(token):
    """测试获取素材列表"""
    print("\n=== 4. 测试获取素材列表 ===")
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/hsai/materials/", 
                              headers=headers, timeout=10)
        log_response("获取素材", response)
        
        if response.status_code == 200:
            materials_data = response.json()
            
            # 处理不同的响应格式
            materials = []
            if isinstance(materials_data, list):
                materials = materials_data
            elif isinstance(materials_data, dict) and 'data' in materials_data:
                materials = materials_data['data']
            
            print(f"✅ 成功获取 {len(materials)} 个素材")
            
            if materials:
                # 显示前几个素材信息
                for i, material in enumerate(materials[:3]):
                    print(f"  [{i+1}] {material.get('name')} (ID: {material.get('id')}, 类型: {material.get('material_type')})")
                
                return materials[0]  # 返回第一个素材用于测试
            else:
                print("⚠️  没有素材可供测试")
                return None
        else:
            print(f"❌ 获取素材失败")
            return None
            
    except Exception as e:
        print(f"❌ 获取素材异常: {e}")
        traceback.print_exc()
        return None

def test_move_to_recovery(token, material):
    """测试移入回收站功能"""
    if not material:
        print("\n=== 5. 跳过移入回收站测试（无素材）===")
        return False
        
    print(f"\n=== 5. 测试移入回收站功能 ===")
    print(f"测试素材: {material.get('name')} (ID: {material.get('id')})")
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    delete_data = {"reason": "回收站功能调试测试"}
    
    try:
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/hsai/materials/{material.get('id')}/move-to-recovery",
            json=delete_data,
            headers=headers,
            timeout=10
        )
        log_response("移入回收站", response)
        
        if response.status_code == 200:
            print("✅ 移入回收站成功")
            return True
        else:
            print(f"❌ 移入回收站失败")
            return False
            
    except Exception as e:
        print(f"❌ 移入回收站异常: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试流程"""
    print("=== 回收站功能调试测试 ===")
    print("开始跟踪控制台输出...")
    
    # 1. 测试服务器连接
    if not test_connection():
        print("\n❌ 服务器连接失败，请确保后端服务正在运行")
        return
    
    # 2. 测试登录
    token = test_login()
    if not token:
        print("\n❌ 登录失败，无法继续测试")
        return
    
    # 3. 测试目录接口
    folders, recovery_found = test_folders_api(token)
    
    # 4. 测试素材列表
    test_material = test_materials_list(token)
    
    # 5. 测试移入回收站
    move_success = test_move_to_recovery(token, test_material)
    
    # 总结结果
    print("\n=== 测试结果总结 ===")
    print(f"🔌 服务器连接: ✅")
    print(f"🔑 用户登录: {'✅' if token else '❌'}")
    print(f"📁 目录接口: {'✅' if folders else '❌'}")
    print(f"🗂️  回收站虚拟目录: {'✅' if recovery_found else '❌'}")
    print(f"📄 素材列表: {'✅' if test_material else '❌'}")
    print(f"🗑️  移入回收站: {'✅' if move_success else '❌'}")
    
    # 问题诊断
    print("\n=== 问题诊断 ===")
    if not recovery_found:
        print("🔍 回收站虚拟目录问题:")
        print("   - 检查 hsai_materials.py 中的 get_material_folders 函数")
        print("   - 确认回收站虚拟目录代码是否正确添加")
    
    if test_material and not move_success:
        print("🔍 移入回收站问题:")
        print("   - 检查 hsai_materials_recovery.py 中的 move_material_to_recovery 函数")
        print("   - 确认 HSAIMaterialForm 是否包含所有必填字段")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断测试")
    except Exception as e:
        print(f"\n\n💥 测试过程中发生未处理异常: {e}")
        traceback.print_exc()