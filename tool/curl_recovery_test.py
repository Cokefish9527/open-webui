#!/usr/bin/env python3
"""
验证回收站修复的最小测试脚本
"""

import subprocess
import sys
import json

def run_curl_test():
    """使用curl测试API"""
    print("=== 使用curl测试回收站功能 ===")
    
    # 1. 测试登录
    print("1. 测试登录...")
    login_cmd = [
        'curl', '-s', '-X', 'POST',
        'http://localhost:8080/api/v1/auths/signin',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            "email": "saiter2306@163.com",
            "password": "123456"
        })
    ]
    
    try:
        result = subprocess.run(login_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            try:
                login_data = json.loads(result.stdout)
                token = login_data.get("token")
                if token:
                    print(f"✅ 登录成功")
                    if not token.startswith("Bearer "):
                        token = f"Bearer {token}"
                else:
                    print(f"❌ 登录响应中未找到token: {result.stdout}")
                    return False
            except json.JSONDecodeError:
                print(f"❌ 登录响应格式错误: {result.stdout}")
                return False
        else:
            print(f"❌ 登录请求失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ 登录请求超时")
        return False
    except Exception as e:
        print(f"❌ 登录请求异常: {e}")
        return False
    
    # 2. 测试获取目录接口
    print("\n2. 测试获取目录接口...")
    folders_cmd = [
        'curl', '-s', '-X', 'GET',
        'http://localhost:8080/api/v1/hsai/materials/folders',
        '-H', 'Content-Type: application/json',
        '-H', f'Authorization: {token}'
    ]
    
    try:
        result = subprocess.run(folders_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            try:
                folders_data = json.loads(result.stdout)
                if isinstance(folders_data, list):
                    print(f"✅ 成功获取 {len(folders_data)} 个目录")
                    
                    # 检查回收站虚拟目录
                    recovery_found = any(folder.get('id') == 'recovery' for folder in folders_data)
                    if recovery_found:
                        print("✅ 找到回收站虚拟目录")
                        recovery_folder = next(folder for folder in folders_data if folder.get('id') == 'recovery')
                        print(f"   回收站名称: {recovery_folder.get('name')}")
                        return True
                    else:
                        print("❌ 未找到回收站虚拟目录")
                        print("目录列表:")
                        for i, folder in enumerate(folders_data):
                            print(f"  [{i+1}] {folder.get('name')} (ID: {folder.get('id')})")
                        return False
                else:
                    print(f"❌ 目录响应格式错误: {result.stdout}")
                    return False
            except json.JSONDecodeError:
                print(f"❌ 目录响应格式错误: {result.stdout}")
                return False
        else:
            print(f"❌ 获取目录请求失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ 获取目录请求超时")
        return False
    except Exception as e:
        print(f"❌ 获取目录请求异常: {e}")
        return False

def check_server():
    """检查服务器是否运行"""
    print("检查服务器状态...")
    try:
        result = subprocess.run(['curl', '-s', '-m', '5', 'http://localhost:8080/health'], 
                              capture_output=True, text=True)
        if result.returncode == 0 or "404" in result.stdout:
            print("✅ 服务器正在运行")
            return True
        else:
            print("❌ 服务器未响应")
            return False
    except:
        print("❌ 无法连接到服务器")
        return False

def main():
    print("=== 回收站功能验证测试 ===")
    
    # 检查服务器
    if not check_server():
        print("\n❌ 请确保后端服务正在 http://localhost:8080 运行")
        return
    
    # 运行测试
    if run_curl_test():
        print("\n🎉 回收站虚拟目录修复成功！")
    else:
        print("\n❌ 回收站功能仍需修复")

if __name__ == "__main__":
    main()