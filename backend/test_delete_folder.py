#!/usr/bin/env python3
"""
删除目录功能专项测试脚本
专门用于验证删除目录接口的功能是否正常
"""

import requests
import json
import time
import sys
import os
from typing import Optional, Dict, Any

# 测试配置
BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"
USE_LOGIN = True
LOGIN_EMAIL = "saiter2306@163.com"
LOGIN_PASSWORD = "123456"
TEST_TIMEOUT = 30

class DeleteFolderTester:
    """删除目录功能测试器"""
    
    def __init__(self):
        self.token = None
        self.headers = {"Content-Type": "application/json"}
        self.test_folder_id = None
        
    def _url(self, path: str) -> str:
        """构建完整的API URL"""
        return f"{BASE_URL}{API_PREFIX}{path}"
        
    def _make_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """发送HTTP请求"""
        url = self._url(path)
        timeout = kwargs.pop('timeout', TEST_TIMEOUT)
        
        if self.token and "headers" not in kwargs:
            kwargs["headers"] = {"Authorization": self.token}
        elif self.token and "headers" in kwargs:
            kwargs["headers"]["Authorization"] = self.token
        
        response = requests.request(method, url, timeout=timeout, **kwargs)
        return response
    
    def login(self) -> bool:
        """登录获取token"""
        print("=== 步骤1: 用户登录 ===")
        
        login_data = {
            "email": LOGIN_EMAIL,
            "password": LOGIN_PASSWORD
        }
        
        try:
            response = self._make_request("POST", "/auths/signin", json=login_data)
            
            if response.status_code == 200:
                login_result = response.json()
                token = login_result.get("token")
                if token:
                    if not token.startswith("Bearer "):
                        self.token = f"Bearer {token}"
                    else:
                        self.token = token
                    
                    print(f"✅ 登录成功: {login_result.get('email')}")
                    return True
                else:
                    print(f"❌ 登录响应中未找到token")
                    return False
            else:
                print(f"❌ 登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return False
    
    def create_test_folder(self) -> bool:
        """创建测试用的文件夹"""
        print("\n=== 步骤2: 创建测试文件夹 ===")
        
        timestamp = int(time.time())
        folder_name = f"delete_test_folder_{timestamp}"
        
        folder_data = {
            "name": folder_name,
            "description": f"删除测试专用文件夹 - 创建于 {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "parent_id": None  # 创建在根目录下
        }
        
        try:
            response = self._make_request("POST", "/hsai/materials/folders", json=folder_data)
            
            if response.status_code == 200:
                new_folder = response.json()
                self.test_folder_id = new_folder['id']
                print(f"✅ 创建测试文件夹成功: {new_folder['name']} (ID: {self.test_folder_id})")
                return True
            else:
                print(f"❌ 创建测试文件夹失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 创建测试文件夹异常: {e}")
            return False
    
    def verify_folder_exists(self) -> bool:
        """验证文件夹存在"""
        print("\n=== 步骤3: 验证文件夹存在 ===")
        
        try:
            response = self._make_request("GET", "/hsai/materials/folders")
            
            if response.status_code == 200:
                folders = response.json()
                
                def find_folder_in_tree(folder_list, target_id):
                    for folder in folder_list:
                        if folder['id'] == target_id:
                            return folder
                        children = folder.get('children', [])
                        if children:
                            result = find_folder_in_tree(children, target_id)
                            if result:
                                return result
                    return None
                
                found_folder = find_folder_in_tree(folders, self.test_folder_id)
                if found_folder:
                    print(f"✅ 文件夹存在: {found_folder['name']} (ID: {self.test_folder_id})")
                    return True
                else:
                    print(f"❌ 文件夹不存在: ID {self.test_folder_id}")
                    return False
            else:
                print(f"❌ 获取文件夹列表失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 验证文件夹存在异常: {e}")
            return False
    
    def delete_folder(self) -> bool:
        """删除文件夹"""
        print("\n=== 步骤4: 删除文件夹 ===")
        
        try:
            response = self._make_request("DELETE", f"/hsai/materials/folders/{self.test_folder_id}")
            
            print(f"删除请求状态码: {response.status_code}")
            print(f"删除请求响应: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result is True:
                    print(f"✅ 删除文件夹成功 (ID: {self.test_folder_id})")
                    return True
                else:
                    print(f"❌ 删除结果异常: {result}")
                    return False
            elif response.status_code == 404:
                print(f"❌ 文件夹不存在或无权限访问")
                return False
            elif response.status_code == 400:
                print(f"❌ 删除请求错误: {response.text}")
                try:
                    error_detail = response.json().get('detail', '未知错误')
                    print(f"   错误详情: {error_detail}")
                except:
                    pass
                return False
            else:
                print(f"❌ 删除文件夹失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 删除文件夹异常: {e}")
            return False
    
    def verify_folder_deleted(self) -> bool:
        """验证文件夹已删除"""
        print("\n=== 步骤5: 验证文件夹已删除 ===")
        
        try:
            response = self._make_request("GET", "/hsai/materials/folders")
            
            if response.status_code == 200:
                folders = response.json()
                
                def find_folder_in_tree(folder_list, target_id):
                    for folder in folder_list:
                        if folder['id'] == target_id:
                            return folder
                        children = folder.get('children', [])
                        if children:
                            result = find_folder_in_tree(children, target_id)
                            if result:
                                return result
                    return None
                
                found_folder = find_folder_in_tree(folders, self.test_folder_id)
                if found_folder:
                    print(f"❌ 验证失败: 文件夹仍然存在: {found_folder['name']}")
                    return False
                else:
                    print(f"✅ 验证成功: 文件夹已从目录树中移除")
                    return True
            else:
                print(f"❌ 获取文件夹列表失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 验证文件夹删除异常: {e}")
            return False
    
    def run_test(self) -> bool:
        """运行完整的删除测试流程"""
        print("🚀 开始删除目录功能专项测试")
        print("=" * 50)
        
        success_count = 0
        total_steps = 5
        
        # 步骤1: 登录
        if self.login():
            success_count += 1
        else:
            print("\n❌ 登录失败，测试终止")
            return False
        
        # 步骤2: 创建测试文件夹
        if self.create_test_folder():
            success_count += 1
        else:
            print("\n❌ 创建测试文件夹失败，测试终止")
            return False
        
        # 步骤3: 验证文件夹存在
        if self.verify_folder_exists():
            success_count += 1
        else:
            print("\n❌ 验证文件夹存在失败")
        
        # 步骤4: 删除文件夹
        if self.delete_folder():
            success_count += 1
        else:
            print("\n❌ 删除文件夹失败")
        
        # 步骤5: 验证文件夹已删除
        if self.verify_folder_deleted():
            success_count += 1
        else:
            print("\n❌ 验证文件夹删除失败")
        
        # 输出测试结果
        print("\n" + "=" * 50)
        print("🏁 删除目录功能测试完成")
        print(f"📊 测试结果: {success_count}/{total_steps} 步骤成功")
        
        if success_count == total_steps:
            print("🎉 所有测试步骤都成功完成！删除目录功能正常工作")
            return True
        else:
            print("❌ 部分测试步骤失败，删除目录功能可能存在问题")
            return False

def main():
    """主函数"""
    print("删除目录功能专项测试脚本")
    print("请确保:")
    print("1. 后端服务正在运行 (http://localhost:8080)")
    print("2. 已配置有效的登录凭据")
    print("3. 具有删除目录的权限")
    print()
    
    tester = DeleteFolderTester()
    success = tester.run_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())