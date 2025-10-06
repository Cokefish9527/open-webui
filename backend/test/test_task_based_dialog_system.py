#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于任务的对话管理系统测试脚本
验证根据方案开发的功能是否达到开发目的
"""

import os
import sys
import random
import string
import time
import json
import urllib.request
import urllib.parse
import urllib.error
import sqlite3

# 添加项目路径到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open_webui_path = os.path.join(project_root, 'open_webui')

sys.path.insert(0, project_root)
sys.path.insert(0, open_webui_path)

print(f"项目根路径: {project_root}")
print(f"Open WebUI路径: {open_webui_path}")

# 设置环境变量确保注册功能启用
os.environ["WEBUI_AUTH"] = "True"
os.environ["ENABLE_SIGNUP"] = "True"

# 服务器配置
BASE_URL = "http://127.0.0.1:8080"
API_PREFIX = "/api/v1"

# 数据库路径
DB_PATH = os.path.join(project_root, "data", "webui.db")

class TaskBasedDialogSystemTester:
    def __init__(self):
        self.test_user_email = ""
        self.test_user_password = ""
        self.test_user_name = ""
        self.auth_token = ""
        self.user_id = ""
        self.company_id = ""
        self.project_id = ""
        self.default_project_id = ""
        self.main_tasks = []
        
    def generate_random_user(self):
        """生成随机用户信息"""
        # 生成随机用户名和邮箱
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        name = f"testuser_{random_suffix}"
        email = f"{name}@example.com"
        password = f"Password_{random_suffix}123"  # 确保密码符合复杂度要求
        
        self.test_user_name = name
        self.test_user_email = email
        self.test_user_password = password
        
        return {
            "name": name,
            "email": email,
            "password": password
        }
    
    def make_request(self, url, method="GET", data=None, headers=None):
        """发送HTTP请求（使用urllib）"""
        if headers is None:
            headers = {}
        
        # 添加认证头
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        # 处理数据
        data_bytes = None
        if data:
            data_bytes = json.dumps(data).encode('utf-8')
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(data_bytes))
        
        # 创建请求
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
        
        try:
            # 发送请求
            response = urllib.request.urlopen(req)
            content = response.read().decode('utf-8')
            return {
                "status_code": response.getcode(),
                "content": content,
                "json": json.loads(content) if content.strip().startswith('{') or content.strip().startswith('[') else None
            }
        except urllib.error.HTTPError as e:
            content = e.read().decode('utf-8')
            return {
                "status_code": e.code,
                "content": content,
                "json": json.loads(content) if content.strip().startswith('{') or content.strip().startswith('[') else None
            }
        except Exception as e:
            return {
                "status_code": 0,
                "content": str(e),
                "json": None
            }
    
    def register_user_via_api(self, user_data):
        """通过API注册新用户"""
        print(f"正在通过API注册用户: {user_data['email']}")
        
        url = f"{BASE_URL}{API_PREFIX}/auths/signup"
        payload = {
            "name": user_data["name"],
            "email": user_data["email"],
            "password": user_data["password"]
        }
        
        result = self.make_request(url, "POST", payload)
        print(f"注册响应状态码: {result['status_code']}")
        
        if result["status_code"] == 200:
            data = result["json"] or {}
            self.auth_token = data.get("token", "")
            self.user_id = data.get("id", "")
            print(f"✓ 用户注册成功，用户ID: {self.user_id}")
            return data
        else:
            print(f"✗ 用户注册失败，状态码: {result['status_code']}")
            print(f"响应内容: {result['content']}")
            return None
    
    def login_user_via_api(self, email, password):
        """通过API登录用户"""
        print(f"正在通过API登录用户: {email}")
        
        url = f"{BASE_URL}{API_PREFIX}/auths/signin"
        payload = {
            "email": email,
            "password": password
        }
        
        result = self.make_request(url, "POST", payload)
        print(f"登录响应状态码: {result['status_code']}")
        
        if result["status_code"] == 200:
            data = result["json"] or {}
            self.auth_token = data.get("token", "")
            self.user_id = data.get("id", "")
            print(f"✓ 用户登录成功，用户ID: {self.user_id}")
            return data
        else:
            print(f"✗ 用户登录失败，状态码: {result['status_code']}")
            print(f"响应内容: {result['content']}")
            return None
    
    def get_db_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
            return conn
        except Exception as e:
            print(f"✗ 连接数据库失败: {e}")
            return None
    
    def verify_user_in_database(self):
        """直接查询数据库验证用户创建"""
        print("\n=== 直接查询数据库验证用户创建 ===")
        
        try:
            # 连接数据库
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # 查询用户
            cursor.execute("SELECT * FROM user WHERE email = ?", (self.test_user_email.lower(),))
            user = cursor.fetchone()
            
            if user:
                print(f"✓ 数据库中找到用户: {user['name']} ({user['email']})")
                print(f"  用户ID: {user['id']}")
                print(f"  用户角色: {user['role']}")
                print(f"  创建时间: {user['created_at']}")
                print(f"  公司ID: {user['company_id']}")
                print(f"  公司名称: {user['business_name']}")
                self.user_id = user['id']
                self.company_id = user['company_id']
                conn.close()
                return True
            else:
                print("✗ 数据库中未找到用户")
                conn.close()
                return False
        except Exception as e:
            print(f"✗ 查询用户数据库时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def verify_company_in_database(self):
        """直接查询数据库验证公司创建"""
        print("\n=== 直接查询数据库验证公司创建 ===")
        
        try:
            # 连接数据库
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # 查询公司
            cursor.execute("SELECT * FROM companies WHERE owner_user_id = ?", (self.user_id,))
            companies = cursor.fetchall()
            
            if companies:
                company = companies[0]  # 取第一个公司
                self.company_id = company['id']
                print(f"✓ 数据库中找到公司: {company['name']}")
                print(f"  公司ID: {company['id']}")
                print(f"  公司描述: {company['description']}")
                print(f"  公司负责人ID: {company['owner_user_id']}")
                print(f"  公司状态: {company['status']}")
                print(f"  创建时间: {company['created_at']}")
                conn.close()
                return True
            else:
                print("✗ 数据库中未找到公司")
                conn.close()
                return False
        except Exception as e:
            print(f"✗ 查询公司数据库时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def verify_default_project_in_database(self):
        """直接查询数据库验证默认项目创建"""
        print("\n=== 直接查询数据库验证默认项目创建 ===")
        
        try:
            # 连接数据库
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # 查询默认项目
            cursor.execute("SELECT * FROM hsai_projects WHERE user_id = ? AND name LIKE ?", 
                          (self.user_id, f"{self.test_user_name}的默认项目%"))
            projects = cursor.fetchall()
            
            if projects:
                project = projects[0]  # 取第一个项目
                self.default_project_id = project['id']
                print(f"✓ 数据库中找到默认项目: {project['name']}")
                print(f"  项目ID: {project['id']}")
                print(f"  项目描述: {project['description']}")
                print(f"  企业名称: {project['business_name']}")
                print(f"  项目状态: {project['status']}")
                print(f"  公司ID: {project['company_id']}")
                print(f"  创建时间: {project['created_at']}")
                conn.close()
                return True
            else:
                print("✗ 数据库中未找到默认项目")
                conn.close()
                return False
        except Exception as e:
            print(f"✗ 查询默认项目数据库时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_project_via_api(self):
        """通过API创建项目"""
        print("\n=== 通过API创建项目 ===")
        
        url = f"{BASE_URL}{API_PREFIX}/hsai/projects"
        payload = {
            "name": f"测试项目_{int(time.time())}",
            "description": "这是一个测试项目",
            "business_name": "测试公司"
        }
        
        result = self.make_request(url, "POST", payload)
        print(f"创建项目响应状态码: {result['status_code']}")
        
        if result["status_code"] == 200:
            data = result["json"] or {}
            self.project_id = data.get("id", "")
            print(f"✓ 项目创建成功，项目ID: {self.project_id}")
            return data
        else:
            print(f"✗ 项目创建失败，状态码: {result['status_code']}")
            print(f"响应内容: {result['content']}")
            return None
    
    def verify_project_in_database(self):
        """直接查询数据库验证项目创建"""
        print("\n=== 直接查询数据库验证项目创建 ===")
        
        if not self.project_id:
            print("✗ 项目ID未设置，无法验证项目")
            return False
        
        try:
            # 连接数据库
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # 查询项目
            cursor.execute("SELECT * FROM hsai_projects WHERE id = ?", (self.project_id,))
            project = cursor.fetchone()
            
            if project:
                print(f"✓ 数据库中找到项目: {project['name']}")
                print(f"  项目ID: {project['id']}")
                print(f"  项目描述: {project['description']}")
                print(f"  企业名称: {project['business_name']}")
                print(f"  项目状态: {project['status']}")
                print(f"  用户ID: {project['user_id']}")
                print(f"  公司ID: {project['company_id']}")
                print(f"  创建时间: {project['created_at']}")
                conn.close()
                return True
            else:
                print("✗ 数据库中未找到项目")
                conn.close()
                return False
        except Exception as e:
            print(f"✗ 查询项目数据库时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def verify_main_tasks_in_database(self):
        """直接查询数据库验证主线任务创建"""
        print("\n=== 直接查询数据库验证主线任务创建 ===")
        
        project_id = self.project_id if self.project_id else self.default_project_id
        if not project_id:
            print("✗ 项目ID未设置，无法验证任务")
            return False
        
        try:
            # 连接数据库
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # 查询任务
            cursor.execute("SELECT * FROM hsai_tasks WHERE project_id = ?", (project_id,))
            tasks = cursor.fetchall()
            
            if tasks:
                # 预期的主线任务标题
                expected_main_tasks = ["完善企业信息", "完善项目信息", "素材库初始化"]
                task_titles = [task['title'] for task in tasks]
                
                print(f"项目任务列表:")
                for task in tasks:
                    status = "✓" if task['title'] in expected_main_tasks else " "
                    print(f"  {status} {task['title']} (状态: {task['status']}, 类型: {task['task_type']})")
                
                # 检查是否包含所有预期的主线任务
                missing_tasks = [task for task in expected_main_tasks if task not in task_titles]
                
                if not missing_tasks:
                    print(f"✓ 所有主线任务创建成功，共 {len(tasks)} 个任务")
                    self.main_tasks = tasks
                    conn.close()
                    return True
                else:
                    print(f"✗ 缺少以下主线任务: {missing_tasks}")
                    conn.close()
                    return False
            else:
                print("✗ 项目没有任何任务")
                conn.close()
                return False
        except Exception as e:
            print(f"✗ 查询任务数据库时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_task_status_via_api(self, task_id, status):
        """通过API更新任务状态"""
        print(f"\n=== 通过API更新任务状态 ===")
        print(f"任务ID: {task_id}, 新状态: {status}")
        
        url = f"{BASE_URL}{API_PREFIX}/hsai/tasks/{task_id}"
        payload = {
            "status": status
        }
        
        result = self.make_request(url, "PUT", payload)
        print(f"更新任务响应状态码: {result['status_code']}")
        
        if result["status_code"] == 200:
            data = result["json"] or {}
            print(f"✓ 任务状态更新成功")
            return data
        else:
            print(f"✗ 任务状态更新失败，状态码: {result['status_code']}")
            print(f"响应内容: {result['content']}")
            return None
    
    def verify_task_status_in_database(self, task_id, expected_status):
        """直接查询数据库验证任务状态"""
        print(f"\n=== 直接查询数据库验证任务状态 ===")
        print(f"任务ID: {task_id}, 期望状态: {expected_status}")
        
        try:
            # 连接数据库
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # 查询任务
            cursor.execute("SELECT * FROM hsai_tasks WHERE id = ?", (task_id,))
            task = cursor.fetchone()
            
            if task:
                current_status = task['status']
                print(f"✓ 数据库中找到任务: {task['title']}")
                print(f"  当前状态: {current_status}")
                print(f"  期望状态: {expected_status}")
                
                if current_status == expected_status:
                    print(f"✓ 任务状态验证成功")
                    conn.close()
                    return True
                else:
                    print(f"✗ 任务状态验证失败")
                    conn.close()
                    return False
            else:
                print("✗ 数据库中未找到任务")
                conn.close()
                return False
        except Exception as e:
            print(f"✗ 查询任务数据库时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_test(self):
        """运行完整的测试流程"""
        print("=== 开始基于任务的对话管理系统测试 ===")
        
        # 1. 生成随机用户
        user_data = self.generate_random_user()
        print(f"生成测试用户: {user_data['name']} ({user_data['email']})")
        
        # 2. 注册用户
        registration_result = self.register_user_via_api(user_data)
        if not registration_result:
            print("✗ 用户注册失败，测试终止")
            return False
        
        # 等待一段时间确保后台处理完成
        print("等待后台处理完成...")
        time.sleep(3)
        
        # 3. 验证用户创建（直接查询数据库）
        if not self.verify_user_in_database():
            print("✗ 用户数据库验证失败")
            return False
        
        # 4. 验证公司创建（直接查询数据库）
        if not self.verify_company_in_database():
            print("✗ 公司数据库验证失败")
            return False
        
        # 5. 验证默认项目创建（直接查询数据库）
        if not self.verify_default_project_in_database():
            print("✗ 默认项目数据库验证失败")
            return False
        
        # 6. 验证默认项目主线任务创建（直接查询数据库）
        if not self.verify_main_tasks_in_database():
            print("✗ 默认项目主线任务数据库验证失败")
            return False
        
        # 7. 登录用户
        login_result = self.login_user_via_api(self.test_user_email, self.test_user_password)
        if not login_result:
            print("✗ 用户登录失败，测试终止")
            return False
        
        # 8. 创建项目
        project_result = self.create_project_via_api()
        if not project_result:
            print("✗ 项目创建失败，测试终止")
            return False
        
        # 等待一段时间确保后台处理完成
        print("等待后台处理完成...")
        time.sleep(3)
        
        # 9. 验证项目创建（直接查询数据库）
        if not self.verify_project_in_database():
            print("✗ 项目数据库验证失败")
            return False
        
        # 10. 验证项目主线任务创建（直接查询数据库）
        if not self.verify_main_tasks_in_database():
            print("✗ 项目主线任务数据库验证失败")
            return False
        
        # 11. 更新任务状态测试
        if self.main_tasks:
            # 选择第一个任务进行状态更新测试
            task = self.main_tasks[0]
            task_id = task['id']
            
            # 更新任务状态为处理中
            update_result = self.update_task_status_via_api(task_id, "in_progress")
            if update_result:
                # 验证任务状态更新
                if not self.verify_task_status_in_database(task_id, "in_progress"):
                    print("✗ 任务状态更新验证失败")
                    return False
            else:
                print("✗ 任务状态更新失败")
                return False
        
        print("\n=== 所有测试通过 ===")
        return True

def main():
    """主函数"""
    tester = TaskBasedDialogSystemTester()
    
    try:
        success = tester.run_test()
        if success:
            print("\n✓ 基于任务的对话管理系统测试成功完成")
            print(f"测试用户: {tester.test_user_email}")
            print(f"用户ID: {tester.user_id}")
            print(f"公司ID: {tester.company_id}")
            print(f"默认项目ID: {tester.default_project_id}")
            print(f"项目ID: {tester.project_id}")
            return 0
        else:
            print("\n✗ 基于任务的对话管理系统测试失败")
            return 1
    except Exception as e:
        print(f"\n✗ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())