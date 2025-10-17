#!/usr/bin/env python3
"""
直接测试数据库功能，绕过服务器
"""

import sys
import os
import random
import string
import time
import json
import sqlite3
from datetime import datetime

# 添加项目路径到系统路径
project_root = os.path.dirname(os.path.abspath(__file__))
open_webui_path = os.path.join(project_root, 'open_webui')

sys.path.insert(0, project_root)
sys.path.insert(0, open_webui_path)

print(f"项目根路径: {project_root}")
print(f"Open WebUI路径: {open_webui_path}")

# 设置环境变量
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(project_root, 'data', 'webui.db')}"

# 导入模型
try:
    from open_webui.models.users import Users, User
    from open_webui.models.hsai_companies import Companies, Company
    from open_webui.models.hsai_projects import HSAIProjects, HSAIProject
    from open_webui.models.hsai_tasks import HSAITasks, HSAITask
    from open_webui.internal.db import get_db
    print("✓ 成功导入模型")
except Exception as e:
    print(f"✗ 导入模型失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

class DirectDBTest:
    def __init__(self):
        self.user_id = ""
        self.company_id = ""
        self.project_id = ""
        
    def generate_random_user(self):
        """生成随机用户信息"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        name = f"testuser_{random_suffix}"
        email = f"{name}@example.com"
        return name, email
    
    def test_user_creation(self):
        """测试用户创建"""
        print("\n=== 测试用户创建 ===")
        
        name, email = self.generate_random_user()
        print(f"创建用户: {name} ({email})")
        
        try:
            # 创建用户
            user = Users.insert_new_user(
                id=str(int(time.time())),
                name=name,
                email=email,
                profile_image_url="/user.png",
                role="user"
            )
            
            if user:
                self.user_id = user.id
                print(f"✓ 用户创建成功，用户ID: {self.user_id}")
                
                # 验证用户是否在数据库中
                with get_db() as db:
                    db_user = db.query(User).filter_by(id=self.user_id).first()
                    if db_user:
                        print(f"✓ 数据库中找到用户: {db_user.name}")
                        return True
                    else:
                        print("✗ 数据库中未找到用户")
                        return False
            else:
                print("✗ 用户创建失败")
                return False
        except Exception as e:
            print(f"✗ 用户创建异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_company_creation(self):
        """测试公司创建"""
        print("\n=== 测试公司创建 ===")
        
        if not self.user_id:
            print("✗ 用户ID未设置，无法创建公司")
            return False
            
        try:
            # 创建公司
            from open_webui.models.hsai_companies import CompanyForm
            company_form = CompanyForm(
                name="测试公司",
                description="这是一个测试公司"
            )
            
            company = Companies.insert_new_company(self.user_id, company_form)
            
            if company:
                self.company_id = company.id
                print(f"✓ 公司创建成功，公司ID: {self.company_id}")
                
                # 验证公司是否在数据库中
                with get_db() as db:
                    db_company = db.query(Company).filter_by(id=self.company_id).first()
                    if db_company:
                        print(f"✓ 数据库中找到公司: {db_company.name}")
                        # 更新用户关联的公司ID
                        db_user = db.query(User).filter_by(id=self.user_id).first()
                        if db_user:
                            setattr(db_user, 'company_id', self.company_id)
                            db.commit()
                            print(f"✓ 用户公司关联更新成功")
                        return True
                    else:
                        print("✗ 数据库中未找到公司")
                        return False
            else:
                print("✗ 公司创建失败")
                return False
        except Exception as e:
            print(f"✗ 公司创建异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_project_creation(self):
        """测试项目创建"""
        print("\n=== 测试项目创建 ===")
        
        if not self.user_id:
            print("✗ 用户ID未设置，无法创建项目")
            return False
            
        try:
            # 创建项目
            from open_webui.models.hsai_projects import HSAIProjectForm
            project_form = HSAIProjectForm(
                name="测试项目",
                description="这是一个测试项目",
                business_name="测试公司"
            )
            
            project = HSAIProjects.insert_new_project(self.user_id, project_form)
            
            if project:
                self.project_id = project.id
                print(f"✓ 项目创建成功，项目ID: {self.project_id}")
                
                # 验证项目是否在数据库中
                with get_db() as db:
                    db_project = db.query(HSAIProject).filter_by(id=self.project_id).first()
                    if db_project:
                        print(f"✓ 数据库中找到项目: {db_project.name}")
                        # 更新项目关联的公司ID
                        if self.company_id:
                            setattr(db_project, 'company_id', self.company_id)
                            db.commit()
                            print(f"✓ 项目公司关联更新成功")
                        return True
                    else:
                        print("✗ 数据库中未找到项目")
                        return False
            else:
                print("✗ 项目创建失败")
                return False
        except Exception as e:
            print(f"✗ 项目创建异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_task_creation(self):
        """测试任务创建"""
        print("\n=== 测试任务创建 ===")
        
        if not self.user_id or not self.project_id:
            print("✗ 用户ID或项目ID未设置，无法创建任务")
            return False
            
        try:
            # 创建任务
            from open_webui.models.hsai_tasks import HSAITaskForm
            task_form = HSAITaskForm(
                title="测试任务",
                description="这是一个测试任务",
                task_type="workflow_execution",
                task_category="main",
                project_id=self.project_id,
                priority=10,
                prompt_config={
                    "system_prompt": "测试系统提示",
                    "initial_message": "测试初始消息"
                }
            )
            
            task = HSAITasks.insert_new_task(self.user_id, task_form)
            
            if task:
                task_id = task.id
                print(f"✓ 任务创建成功，任务ID: {task_id}")
                
                # 验证任务是否在数据库中
                with get_db() as db:
                    db_task = db.query(HSAITask).filter_by(id=task_id).first()
                    if db_task:
                        print(f"✓ 数据库中找到任务: {db_task.title}")
                        print(f"  任务类型: {db_task.task_type}")
                        print(f"  任务状态: {db_task.status}")
                        print(f"  项目ID: {db_task.project_id}")
                        print(f"  提示配置: {db_task.prompt_config}")
                        return True
                    else:
                        print("✗ 数据库中未找到任务")
                        return False
            else:
                print("✗ 任务创建失败")
                return False
        except Exception as e:
            print(f"✗ 任务创建异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_test(self):
        """运行完整的测试流程"""
        print("=== 开始直接数据库测试 ===")
        
        # 1. 测试用户创建
        if not self.test_user_creation():
            print("✗ 用户创建测试失败")
            return False
        
        # 2. 测试公司创建
        if not self.test_company_creation():
            print("✗ 公司创建测试失败")
            return False
        
        # 3. 测试项目创建
        if not self.test_project_creation():
            print("✗ 项目创建测试失败")
            return False
        
        # 4. 测试任务创建
        if not self.test_task_creation():
            print("✗ 任务创建测试失败")
            return False
        
        print("\n=== 所有测试通过 ===")
        return True

def main():
    """主函数"""
    tester = DirectDBTest()
    
    try:
        success = tester.run_test()
        if success:
            print("\n✓ 直接数据库测试成功完成")
            print(f"用户ID: {tester.user_id}")
            print(f"公司ID: {tester.company_id}")
            print(f"项目ID: {tester.project_id}")
            return 0
        else:
            print("\n✗ 直接数据库测试失败")
            return 1
    except Exception as e:
        print(f"\n✗ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())