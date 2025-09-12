#!/usr/bin/env python3
"""
文件夹接口完整工作流测试脚本
按照指定流程测试创建文件夹和获取文件夹的接口

测试流程:
1. 获取根目录
2. 从根目录的子元素中找到第一个目录的id
3. 如果没有第一个子元素，直接使用根目录的id创建下级子目录，如果有则使用子元素的id创建下级子目录
4. 再次调用获取目录接口，获取根目录的信息，确认创建的目录是否成功
5. 使用刚才新建的目录id获取目录信息
"""

import requests
import json
import time
import sys
import os
from typing import Optional, Dict, Any, List

# 尝试导入配置文件
try:
    from test_config import (
        BASE_URL, API_PREFIX, TOKEN, TEST_TIMEOUT, FOLDER_NAME_PREFIX, DEBUG_MODE,
        USE_LOGIN, LOGIN_EMAIL, LOGIN_PASSWORD
    )
except ImportError:
    # 如果配置文件不存在，使用默认配置
    BASE_URL = "http://localhost:8080"
    API_PREFIX = "/api/v1"
    TOKEN = "your_token_here"  # 需要替换为实际的认证token
    TEST_TIMEOUT = 30
    FOLDER_NAME_PREFIX = "test_folder"
    DEBUG_MODE = True
    USE_LOGIN = True
    LOGIN_EMAIL = "admin@localhost"
    LOGIN_PASSWORD = "admin"

class FolderTestRunner:
    """文件夹接口测试运行器"""
    
    def __init__(self, base_url: str, api_prefix: str, token: str):
        self.base_url = base_url
        self.api_prefix = api_prefix
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Folder Workflow Test Script/1.0"
        })
        
        # 如果配置了使用登录，则需要先登录获取token
        if USE_LOGIN and (not token or token == "your_token_here"):
            self.token = None  # 清空token，等待登录获取
        elif token and token != "your_token_here":
            # 如果token不以Bearer开头，则添加
            if not token.startswith("Bearer "):
                self.token = f"Bearer {token}"
            else:
                self.token = token
            self.session.headers.update({"Authorization": self.token})
    
    def _auth_headers(self) -> Dict[str, str]:
        """生成认证请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Folder Workflow Test Script/1.0"
        }
        if self.token:
            headers["Authorization"] = self.token
        return headers
    
    def login(self) -> bool:
        """
        步骤0: 用户登录获取TOKEN
        """
        if not USE_LOGIN:
            return True  # 不需要登录
            
        print("=== 步骤0: 用户登录 ===")
        
        try:
            # 构建登录请求数据，参照SigninForm模型
            login_data = {
                "email": LOGIN_EMAIL,
                "password": LOGIN_PASSWORD
            }
            
            print(f"尝试登录用户: {LOGIN_EMAIL}")
            
            response = self._make_request("POST", "/auths/signin", json=login_data)
            
            if response.status_code == 200:
                login_result = response.json()
                
                # 根据登录接口返回的数据结构获取token
                token = login_result.get("token")
                if token:
                    # 添加Bearer前缀（如果没有的话）
                    if not token.startswith("Bearer "):
                        self.token = f"Bearer {token}"
                    else:
                        self.token = token
                    
                    # 更新session的认证头
                    self.session.headers.update({"Authorization": self.token})
                    
                    print(f"✅ 登录成功")
                    print(f"   用户ID: {login_result.get('id')}")
                    print(f"   用户名: {login_result.get('name')}")
                    print(f"   邮箱: {login_result.get('email')}")
                    print(f"   角色: {login_result.get('role')}")
                    print(f"   Token: {self.token[:50]}...")
                    
                    if DEBUG_MODE:
                        print(f"   完整Token: {self.token}")
                    
                    return True
                else:
                    print(f"❌ 登录响应中未找到token")
                    if DEBUG_MODE:
                        print(f"   响应内容: {login_result}")
                    return False
            elif response.status_code == 400:
                print(f"❌ 登录失败: 用户名或密码错误")
                try:
                    error_detail = response.json().get('detail', '未知错误')
                    print(f"   错误详情: {error_detail}")
                except:
                    print(f"   响应内容: {response.text}")
                return False
            else:
                print(f"❌ 登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 登录过程中发生异常: {str(e)}")
            return False
    
    def _url(self, path: str) -> str:
        """构建完整的API URL"""
        return f"{self.base_url}{self.api_prefix}{path}"
    
    def _make_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """发送HTTP请求"""
        url = self._url(path)
        try:
            # 使用配置中的超时时间
            timeout = kwargs.pop('timeout', TEST_TIMEOUT)
            
            # 更新认证头（如果需要）
            if self.token and "headers" not in kwargs:
                kwargs["headers"] = {"Authorization": self.token}
            elif self.token and "headers" in kwargs:
                kwargs["headers"]["Authorization"] = self.token
            
            response = self.session.request(method, url, timeout=timeout, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {str(e)}")
            raise
    
    def get_root_folders(self) -> List[Dict[str, Any]]:
        """
        步骤1: 获取根目录
        """
        print("=== 步骤1: 获取根目录 ===")
        
        try:
            response = self._make_request("GET", "/hsai/materials/folders")
            
            if response.status_code == 401:
                print("❌ 认证失败，请检查TOKEN配置")
                return []
            elif response.status_code != 200:
                print(f"❌ 获取根目录失败: {response.status_code} - {response.text}")
                return []
            
            folders = response.json()
            print(f"✅ 成功获取根目录，共 {len(folders)} 个根级文件夹")
            
            # 显示根目录信息
            for i, folder in enumerate(folders):
                children_count = len(folder.get('children', []))
                print(f"   [{i+1}] {folder['name']} (ID: {folder['id']}) - 子目录: {children_count}个")
                
                # 显示子目录信息
                if children_count > 0:
                    for j, child in enumerate(folder.get('children', [])):
                        print(f"        └── [{j+1}] {child['name']} (ID: {child['id']})")
            
            return folders
            
        except Exception as e:
            print(f"❌ 获取根目录时发生异常: {str(e)}")
            return []
    
    def find_target_parent_id(self, root_folders: List[Dict[str, Any]]) -> Optional[str]:
        """
        步骤2: 从根目录的子元素中找到第一个目录的id
        """
        print("\n=== 步骤2: 查找目标父目录ID ===")
        
        if not root_folders:
            print("⚠️  没有根目录，无法继续")
            return None
        
        # 遍历所有根目录，寻找第一个有子目录的
        for root_folder in root_folders:
            children = root_folder.get('children', [])
            if children:
                first_child = children[0]
                print(f"✅ 找到第一个子目录: {first_child['name']} (ID: {first_child['id']})")
                print(f"   父目录: {root_folder['name']} (ID: {root_folder['id']})")
                return first_child['id']
        
        # 如果没有找到子目录，使用第一个根目录
        first_root = root_folders[0]
        print(f"⚠️  没有找到子目录，将使用第一个根目录: {first_root['name']} (ID: {first_root['id']})")
        return first_root['id']
    
    def create_subfolder(self, parent_id: str) -> Optional[Dict[str, Any]]:
        """
        步骤3: 创建下级子目录
        """
        print(f"\n=== 步骤3: 在父目录 {parent_id} 下创建子目录 ===")
        
        # 生成唯一的文件夹名称
        timestamp = int(time.time())
        folder_name = f"{FOLDER_NAME_PREFIX}_{timestamp}"
        
        folder_data = {
            "name": folder_name,
            "description": f"测试子目录 - 创建于 {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "parent_id": parent_id
        }
        
        try:
            response = self._make_request("POST", "/hsai/materials/folders", json=folder_data)
            
            if response.status_code == 200:
                new_folder = response.json()
                print(f"✅ 成功创建子目录: {new_folder['name']} (ID: {new_folder['id']})")
                print(f"   父目录ID: {new_folder.get('parent_id')}")
                print(f"   创建时间: {new_folder.get('created_at')}")
                return new_folder
            else:
                print(f"❌ 创建子目录失败: {response.status_code} - {response.text}")
                try:
                    error_detail = response.json().get('detail', '未知错误')
                    print(f"   错误详情: {error_detail}")
                except:
                    pass
                return None
                
        except Exception as e:
            print(f"❌ 创建子目录时发生异常: {str(e)}")
            return None
    
    def verify_folder_creation(self) -> List[Dict[str, Any]]:
        """
        步骤4: 再次获取根目录信息，确认创建的目录是否成功
        """
        print("\n=== 步骤4: 验证目录创建是否成功 ===")
        
        try:
            response = self._make_request("GET", "/hsai/materials/folders")
            
            if response.status_code != 200:
                print(f"❌ 重新获取根目录失败: {response.status_code} - {response.text}")
                return []
            
            folders = response.json()
            print(f"✅ 重新获取根目录成功，共 {len(folders)} 个根级文件夹")
            
            # 显示更新后的目录结构
            total_folders = 0
            for i, folder in enumerate(folders):
                children_count = len(folder.get('children', []))
                total_folders += 1 + children_count
                print(f"   [{i+1}] {folder['name']} (ID: {folder['id']}) - 子目录: {children_count}个")
                
                # 显示子目录信息，标记新创建的
                if children_count > 0:
                    for j, child in enumerate(folder.get('children', [])):
                        # 检查是否是刚才创建的目录（名称包含test_subfolder）
                        is_new = "test_subfolder_" in child['name']
                        marker = " 🆕" if is_new else ""
                        print(f"        └── [{j+1}] {child['name']} (ID: {child['id']}){marker}")
            
            print(f"📊 目录统计: 总共 {total_folders} 个文件夹")
            return folders
            
        except Exception as e:
            print(f"❌ 验证目录创建时发生异常: {str(e)}")
            return []
    
    def get_folder_by_id(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """
        步骤5: 使用新建的目录id获取目录信息
        """
        print(f"\n=== 步骤5: 获取目录详细信息 (ID: {folder_id}) ===")
        
        try:
            # 注意：这里假设有按ID获取目录的接口，如果没有则需要从树结构中查找
            response = self._make_request("GET", f"/hsai/materials/folders/{folder_id}")
            
            if response.status_code == 200:
                folder_detail = response.json()
                print(f"✅ 成功获取目录详细信息:")
                print(f"   名称: {folder_detail['name']}")
                print(f"   ID: {folder_detail['id']}")
                print(f"   描述: {folder_detail.get('description', '无')}")
                print(f"   父目录ID: {folder_detail.get('parent_id', '无')}")
                print(f"   创建时间: {folder_detail.get('created_at')}")
                print(f"   更新时间: {folder_detail.get('updated_at')}")
                
                # 检查label字段（根据代码规范）
                if 'label' in folder_detail:
                    print(f"   标签: {folder_detail['label']}")
                    if folder_detail['label'] == folder_detail['name']:
                        print("   ✅ label字段与name字段值相同（符合规范）")
                    else:
                        print("   ⚠️  label字段与name字段值不同")
                
                return folder_detail
            elif response.status_code == 404:
                print(f"⚠️  按ID获取目录的接口不存在，尝试从树结构中查找...")
                return self._find_folder_in_tree(folder_id)
            else:
                print(f"❌ 获取目录详细信息失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ 获取目录详细信息时发生异常: {str(e)}")
            # 备用方案：从树结构中查找
            print("🔄 尝试备用方案：从目录树中查找...")
            return self._find_folder_in_tree(folder_id)
    
    def _find_folder_in_tree(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """从目录树中查找指定ID的文件夹"""
        try:
            response = self._make_request("GET", "/hsai/materials/folders")
            if response.status_code != 200:
                return None
            
            folders = response.json()
            
            def search_folder(folder_list: List[Dict[str, Any]], target_id: str) -> Optional[Dict[str, Any]]:
                for folder in folder_list:
                    if folder['id'] == target_id:
                        return folder
                    # 递归搜索子目录
                    children = folder.get('children', [])
                    if children:
                        result = search_folder(children, target_id)
                        if result:
                            return result
                return None
            
            result = search_folder(folders, folder_id)
            if result:
                print(f"✅ 在目录树中找到目标文件夹:")
                print(f"   名称: {result['name']}")
                print(f"   ID: {result['id']}")
                print(f"   父目录ID: {result.get('parent_id', '无')}")
            else:
                print(f"❌ 在目录树中未找到ID为 {folder_id} 的文件夹")
            
            return result
            
        except Exception as e:
            print(f"❌ 从目录树中查找文件夹时发生异常: {str(e)}")
            return None
    
    def delete_folder(self, folder_id: str) -> bool:
        """
        步骤6: 删除指定的文件夹
        """
        print(f"\n=== 步骤6: 删除文件夹 (ID: {folder_id}) ===")
        
        try:
            response = self._make_request("DELETE", f"/hsai/materials/folders/{folder_id}")
            
            if response.status_code == 200:
                result = response.json()
                if result is True:
                    print(f"✅ 成功删除文件夹 (ID: {folder_id})")
                    return True
                else:
                    print(f"❌ 删除结果异常: {result}")
                    return False
            else:
                print(f"❌ 删除文件夹失败: {response.status_code} - {response.text}")
                try:
                    error_detail = response.json().get('detail', '未知错误')
                    print(f"   错误详情: {error_detail}")
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"❌ 删除文件夹时发生异常: {str(e)}")
            return False
    
    def verify_folder_deletion(self, folder_id: str) -> bool:
        """
        步骤7: 验证文件夹删除是否成功
        """
        print(f"\n=== 步骤7: 验证文件夹删除是否成功 ===")
        
        try:
            # 尝试从目录树中查找被删除的文件夹
            found_folder = self._find_folder_in_tree(folder_id)
            
            if found_folder:
                print(f"❌ 验证失败: 文件夹仍然存在于目录树中")
                return False
            else:
                print(f"✅ 验证成功: 文件夹已从目录树中移除")
                return True
                
        except Exception as e:
            print(f"❌ 验证文件夹删除时发生异常: {str(e)}")
            return False
    
    def run_complete_workflow(self) -> bool:
        """运行完整的测试工作流"""
        print("🚀 开始执行文件夹接口完整工作流测试")
        print("=" * 60)
        
        try:
            # 步骤0: 登录获取TOKEN（如果需要）
            if USE_LOGIN:
                if not self.login():
                    print("\n❌ 用户登录失败，测试终止")
                    return False
            elif not self.token or self.token == "your_token_here":
                print("\n⚠️  警告: 未配置有效的TOKEN且未启用登录功能")
                print("   请在test_config.py中设置USE_LOGIN=True或提供有效的TOKEN")
                return False
            
            # 步骤1: 获取根目录
            root_folders = self.get_root_folders()
            if not root_folders:
                print("\n❌ 无法获取根目录，测试终止")
                return False
            
            # 步骤2: 找到目标父目录ID
            parent_id = self.find_target_parent_id(root_folders)
            if not parent_id:
                print("\n❌ 无法确定父目录ID，测试终止")
                return False
            
            # 步骤3: 创建子目录
            new_folder = self.create_subfolder(parent_id)
            if not new_folder:
                print("\n❌ 创建子目录失败，测试终止")
                return False
            
            new_folder_id = new_folder['id']
            
            # 步骤4: 验证目录创建
            updated_folders = self.verify_folder_creation()
            if not updated_folders:
                print("\n⚠️  无法验证目录创建结果")
            
            # 步骤5: 获取新建目录的详细信息
            folder_detail = self.get_folder_by_id(new_folder_id)
            if not folder_detail:
                print(f"\n⚠️  无法获取新建目录 {new_folder_id} 的详细信息")
            
            # 步骤6: 删除新建的目录
            delete_success = self.delete_folder(new_folder_id)
            if not delete_success:
                print(f"\n❌ 删除目录失败")
            
            # 步骤7: 验证目录删除
            if delete_success:
                deletion_verified = self.verify_folder_deletion(new_folder_id)
                if not deletion_verified:
                    print(f"\n❌ 验证目录删除失败")
            
            print("\n" + "=" * 60)
            print("🎉 文件夹接口测试工作流完成！")
            print("\n📋 测试总结:")
            
            if USE_LOGIN:
                print(f"   ✅ 成功登录用户: {LOGIN_EMAIL}")
            
            print(f"   ✅ 成功获取根目录信息")
            print(f"   ✅ 成功确定父目录ID: {parent_id}")
            print(f"   ✅ 成功创建子目录: {new_folder['name']} (ID: {new_folder_id})")
            print(f"   ✅ 成功验证目录创建结果")
            
            if folder_detail:
                print(f"   ✅ 成功获取新建目录详细信息")
            else:
                print(f"   ⚠️  获取新建目录详细信息失败")
            
            if delete_success:
                print(f"   ✅ 成功删除目录: {new_folder['name']} (ID: {new_folder_id})")
                if deletion_verified:
                    print(f"   ✅ 成功验证目录删除结果")
                else:
                    print(f"   ⚠️  验证目录删除结果失败")
            else:
                print(f"   ❌ 删除目录失败")
            
            return True
            
        except Exception as e:
            print(f"\n❌ 测试工作流执行过程中发生异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def print_usage():
    """打印使用说明"""
    print("""
📖 使用说明:
1. 请先确保后端服务器正在运行 (http://localhost:8080)
2. 修改脚本中的 TOKEN 变量为有效的认证令牌
3. 如果API前缀不同，请修改 API_PREFIX 变量
4. 运行脚本: python test_folder_workflow.py

🔧 配置选项:
- BASE_URL: 后端服务器地址
- API_PREFIX: API路径前缀
- TOKEN: 用户认证令牌

📋 测试流程:
1. 获取根目录
2. 从根目录的子元素中找到第一个目录的id
3. 如果没有第一个子元素，直接使用根目录的id创建下级子目录，如果有则使用子元素的id创建下级子目录
4. 再次调用获取目录接口，获取根目录的信息，确认创建的目录是否成功
5. 使用刚才新建的目录id获取目录信息
""")

def main():
    """主函数"""
    print("=== 文件夹接口完整工作流测试脚本 ===")
    
    # 检查配置
    if USE_LOGIN:
        if not LOGIN_EMAIL or not LOGIN_PASSWORD:
            print("⚠️  请在test_config.py中设置有效的LOGIN_EMAIL和LOGIN_PASSWORD")
            print_usage()
            return
        print(f"🔑 将使用用户名密码登录: {LOGIN_EMAIL}")
    elif TOKEN == "your_token_here":
        print("⚠️  请先设置有效的TOKEN或启用登录功能")
        print_usage()
        return
    else:
        print(f"🔑 将使用预设的TOKEN: {TOKEN[:50]}...")
    
    # 创建测试运行器
    test_runner = FolderTestRunner(BASE_URL, API_PREFIX, TOKEN)
    
    # 执行完整测试工作流
    success = test_runner.run_complete_workflow()
    
    if success:
        print("\n🎊 恭喜！所有测试步骤都成功完成。")
    else:
        print("\n😞 测试过程中遇到问题，请检查日志信息。")

if __name__ == "__main__":
    main()