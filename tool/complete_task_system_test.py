#!/usr/bin/env python3
"""
完整的任务系统测试，模拟项目创建时自动创建主线任务的过程
"""

import sqlite3
import os
import random
import string
import time
import json

# 数据库路径
db_path = r"data/webui.db"

# 检查数据库文件是否存在
if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    exit(1)

# 连接数据库
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
cursor = conn.cursor()

print(f"连接到数据库: {db_path}")

# 检查数据库中的表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("数据库中的表:")
for table in tables:
    print(f"  - {table[0]}")

# 项目主线任务模板
PROJECT_MAIN_TASK_TEMPLATES = {
    "company_info": {
        "title": "完善企业信息",
        "description": "请提供您企业的基本信息，包括企业名称、行业、规模等",
        "task_type": "workflow_execution",
        "task_category": "main",
        "priority": 10,
        "prompt_config": {
            "system_prompt": "您是一个企业信息收集助手，请引导用户完善企业基本信息",
            "initial_message": "您好！为了更好地为您服务，我们需要收集一些您企业的基本信息。"
        }
    },
    "project_info": {
        "title": "完善项目信息",
        "description": "请提供项目的基本信息，包括项目目标、预期成果、时间规划等",
        "task_type": "workflow_execution",
        "task_category": "main",
        "priority": 9,
        "prompt_config": {
            "system_prompt": "您是一个项目信息收集助手，请引导用户完善项目基本信息",
            "initial_message": "接下来我们需要了解您的项目基本信息，以便为您提供更好的服务。"
        }
    },
    "material_init": {
        "title": "素材库初始化",
        "description": "初始化项目素材库，上传相关素材文件",
        "task_type": "material_processing",
        "task_category": "main",
        "priority": 8,
        "prompt_config": {
            "system_prompt": "您是一个素材管理助手，请引导用户完成素材库初始化",
            "initial_message": "现在让我们初始化您的项目素材库，请上传相关素材文件。"
        }
    }
}

class CompleteTaskSystemTest:
    def __init__(self, conn):
        self.conn = conn
        self.user_id = ""
        self.company_id = ""
        self.project_id = ""
        self.main_tasks = []
    
    def generate_random_string(self, length=8):
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def test_user_creation(self):
        """测试用户创建"""
        print("\n=== 测试用户创建 ===")
        
        random_suffix = self.generate_random_string()
        user_id = str(int(time.time()))
        name = f"testuser_{random_suffix}"
        email = f"{name}@example.com"
        
        print(f"创建用户: {name} ({email})")
        
        try:
            # 插入用户
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO user (id, name, email, role, profile_image_url, created_at, updated_at, last_active_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, name, email, "user", "/user.png", int(time.time()), int(time.time()), int(time.time())))
            
            self.conn.commit()
            self.user_id = user_id
            print(f"✓ 用户创建成功，用户ID: {self.user_id}")
            
            # 验证用户是否在数据库中
            cursor.execute("SELECT * FROM user WHERE id = ?", (self.user_id,))
            user = cursor.fetchone()
            
            if user:
                print(f"✓ 数据库中找到用户: {user['name']} ({user['email']})")
                return True
            else:
                print("✗ 数据库中未找到用户")
                return False
        except Exception as e:
            print(f"✗ 用户创建异常: {e}")
            return False
    
    def test_company_creation(self):
        """测试公司创建"""
        print("\n=== 测试公司创建 ===")
        
        if not self.user_id:
            print("✗ 用户ID未设置，无法创建公司")
            return False
        
        try:
            company_id = str(int(time.time()))
            name = "测试公司"
            description = "这是一个测试公司"
            
            # 插入公司
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO companies (id, name, description, owner_user_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (company_id, name, description, self.user_id, "active", int(time.time()), int(time.time())))
            
            self.conn.commit()
            self.company_id = company_id
            print(f"✓ 公司创建成功，公司ID: {self.company_id}")
            
            # 验证公司是否在数据库中
            cursor.execute("SELECT * FROM companies WHERE id = ?", (self.company_id,))
            company = cursor.fetchone()
            
            if company:
                print(f"✓ 数据库中找到公司: {company['name']}")
                
                # 更新用户关联的公司ID
                cursor.execute("UPDATE user SET company_id = ? WHERE id = ?", (self.company_id, self.user_id))
                self.conn.commit()
                print(f"✓ 用户公司关联更新成功")
                return True
            else:
                print("✗ 数据库中未找到公司")
                return False
        except Exception as e:
            print(f"✗ 公司创建异常: {e}")
            return False
    
    def test_project_creation_with_main_tasks(self):
        """测试项目创建及主线任务自动创建"""
        print("\n=== 测试项目创建及主线任务自动创建 ===")
        
        if not self.user_id:
            print("✗ 用户ID未设置，无法创建项目")
            return False
        
        try:
            project_id = str(int(time.time()))
            name = "测试项目"
            description = "这是一个测试项目"
            business_name = "测试公司"
            
            # 插入项目
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO hsai_projects (id, name, description, business_name, user_id, status, created_at, updated_at, company_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, name, description, business_name, self.user_id, "active", int(time.time()), int(time.time()), self.company_id))
            
            self.conn.commit()
            self.project_id = project_id
            print(f"✓ 项目创建成功，项目ID: {self.project_id}")
            
            # 验证项目是否在数据库中
            cursor.execute("SELECT * FROM hsai_projects WHERE id = ?", (self.project_id,))
            project = cursor.fetchone()
            
            if project:
                print(f"✓ 数据库中找到项目: {project['name']}")
                
                # 自动创建主线任务
                print("  自动创建主线任务...")
                main_tasks_created = self.create_main_tasks()
                if not main_tasks_created:
                    print("✗ 主线任务创建失败")
                    return False
                
                return True
            else:
                print("✗ 数据库中未找到项目")
                return False
        except Exception as e:
            print(f"✗ 项目创建异常: {e}")
            return False
    
    def create_main_tasks(self):
        """创建主线任务"""
        if not self.user_id or not self.project_id:
            print("✗ 用户ID或项目ID未设置，无法创建主线任务")
            return False
        
        try:
            cursor = self.conn.cursor()
            created_tasks = []
            
            for template_key, template in PROJECT_MAIN_TASK_TEMPLATES.items():
                task_id = f"{int(time.time())}_{template_key}"
                title = template["title"]
                description = template["description"]
                task_type = template["task_type"]
                task_category = template["task_category"]
                priority = template["priority"]
                prompt_config = json.dumps(template["prompt_config"]) if template.get("prompt_config") else None
                
                # 插入任务
                cursor.execute("""
                    INSERT INTO hsai_tasks (id, title, description, task_type, task_category, status, user_id, project_id, priority, progress, prompt_config, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (task_id, title, description, task_type, task_category, "pending", self.user_id, self.project_id, priority, 0, prompt_config, int(time.time()), int(time.time())))
                
                created_tasks.append({
                    "id": task_id,
                    "title": title
                })
                print(f"    ✓ 创建主线任务: {title}")
            
            self.conn.commit()
            self.main_tasks = created_tasks
            print(f"  ✓ 共创建 {len(created_tasks)} 个主线任务")
            return True
        except Exception as e:
            print(f"✗ 主线任务创建异常: {e}")
            return False
    
    def verify_main_tasks(self):
        """验证主线任务"""
        print("\n=== 验证主线任务 ===")
        
        if not self.project_id:
            print("✗ 项目ID未设置，无法验证主线任务")
            return False
        
        expected_tasks = ["完善企业信息", "完善项目信息", "素材库初始化"]
        print(f"预期的主线任务: {expected_tasks}")
        
        try:
            # 查询项目关联的任务
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, title, task_type, status, task_category FROM hsai_tasks WHERE project_id = ?", (self.project_id,))
            tasks = cursor.fetchall()
            
            if tasks:
                print(f"项目实际任务:")
                task_titles = []
                for task in tasks:
                    task_titles.append(task['title'])
                    print(f"  - {task['title']} (类型: {task['task_type']}, 状态: {task['status']}, 分类: {task['task_category']})")
                
                # 检查是否包含所有预期的主线任务
                missing_tasks = [task for task in expected_tasks if task not in task_titles]
                
                if not missing_tasks:
                    print(f"✓ 所有预期的主线任务都已创建")
                    self.main_tasks = tasks
                    return True
                else:
                    print(f"✗ 缺少以下主线任务: {missing_tasks}")
                    return False
            else:
                print("✗ 项目没有任何任务")
                return False
        except Exception as e:
            print(f"✗ 主线任务验证异常: {e}")
            return False
    
    def test_task_status_update(self):
        """测试任务状态更新"""
        print("\n=== 测试任务状态更新 ===")
        
        if not self.main_tasks:
            print("✗ 没有主线任务，无法测试状态更新")
            return False
        
        try:
            # 选择第一个任务进行状态更新测试
            task = self.main_tasks[0]
            task_id = task['id'] if isinstance(task, dict) and 'id' in task else task[0]  # 兼容不同格式
            
            print(f"更新任务ID {task_id} 的状态为 'in_progress'")
            
            # 更新任务状态
            cursor = self.conn.cursor()
            cursor.execute("UPDATE hsai_tasks SET status = ?, updated_at = ? WHERE id = ?", ("in_progress", int(time.time()), task_id))
            self.conn.commit()
            
            # 验证状态更新
            cursor.execute("SELECT status FROM hsai_tasks WHERE id = ?", (task_id,))
            updated_task = cursor.fetchone()
            
            if updated_task and updated_task['status'] == 'in_progress':
                print(f"✓ 任务状态更新成功，当前状态: {updated_task['status']}")
                return True
            else:
                print("✗ 任务状态更新失败")
                return False
        except Exception as e:
            print(f"✗ 任务状态更新异常: {e}")
            return False
    
    def run_test(self):
        """运行完整的测试流程"""
        print("=== 开始完整的任务系统测试 ===")
        
        # 1. 测试用户创建
        if not self.test_user_creation():
            print("✗ 用户创建测试失败")
            return False
        
        # 2. 测试公司创建
        if not self.test_company_creation():
            print("✗ 公司创建测试失败")
            return False
        
        # 3. 测试项目创建及主线任务自动创建
        if not self.test_project_creation_with_main_tasks():
            print("✗ 项目创建及主线任务自动创建测试失败")
            return False
        
        # 4. 验证主线任务
        if not self.verify_main_tasks():
            print("✗ 主线任务验证测试失败")
            return False
        
        # 5. 测试任务状态更新
        if not self.test_task_status_update():
            print("✗ 任务状态更新测试失败")
            return False
        
        print("\n=== 所有测试通过 ===")
        return True

def main():
    """主函数"""
    tester = CompleteTaskSystemTest(conn)
    
    try:
        success = tester.run_test()
        if success:
            print("\n✓ 完整的任务系统测试成功完成")
            print(f"用户ID: {tester.user_id}")
            print(f"公司ID: {tester.company_id}")
            print(f"项目ID: {tester.project_id}")
            print(f"主线任务数量: {len(tester.main_tasks)}")
            
            # 清理测试数据
            print("\n=== 清理测试数据 ===")
            try:
                cursor = conn.cursor()
                # 删除任务
                if tester.project_id:
                    cursor.execute("DELETE FROM hsai_tasks WHERE project_id = ?", (tester.project_id,))
                # 删除项目
                if tester.project_id:
                    cursor.execute("DELETE FROM hsai_projects WHERE id = ?", (tester.project_id,))
                # 删除公司
                if tester.company_id:
                    cursor.execute("DELETE FROM companies WHERE id = ?", (tester.company_id,))
                # 删除用户
                if tester.user_id:
                    cursor.execute("DELETE FROM user WHERE id = ?", (tester.user_id,))
                conn.commit()
                print("✓ 测试数据清理完成")
            except Exception as e:
                print(f"✗ 测试数据清理失败: {e}")
            
            conn.close()
            return 0
        else:
            print("\n✗ 完整的任务系统测试失败")
            conn.close()
            return 1
    except Exception as e:
        print(f"\n✗ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return 1

if __name__ == "__main__":
    exit(main())