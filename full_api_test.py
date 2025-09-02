import sys
import os

# 添加项目路径
sys.path.append(r"d:\Work\hsch\open-webui\backend")

import asyncio
from fastapi import Request, Response
from fastapi.background import BackgroundTasks
from open_webui.env import WEBUI_SECRET_KEY
from open_webui.utils.auth import get_current_user, get_verified_user
from open_webui.models.hsai_tasks import HSAITasks

print(f"WEBUI_SECRET_KEY: {WEBUI_SECRET_KEY}")

# 模拟请求对象
class MockRequest:
    def __init__(self, token):
        self.headers = {}
        self.cookies = {"token": token}
        self.url = type('URL', (), {'path': '/api/v1/hsai/tasks/stats'})()
        self.state = type('State', (), {'enable_api_key': False})()
        self.app = type('App', (), {
            'state': type('State', (), {
                'config': type('Config', (), {
                    'ENABLE_API_KEY_ENDPOINT_RESTRICTIONS': False,
                    'API_KEY_ALLOWED_ENDPOINTS': ''
                })()
            })()
        })()

class MockResponse:
    def __init__(self):
        self.cookies = {}
        
    def delete_cookie(self, name):
        if name in self.cookies:
            del self.cookies[name]

class MockBackgroundTasks:
    def add_task(self, func, *args):
        pass

async def test_full_api_call():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc"
    
    request = MockRequest(token)
    response = MockResponse()
    background_tasks = MockBackgroundTasks()
    
    try:
        # 模拟认证过程
        print("Testing authentication...")
        user = get_current_user(request, response, background_tasks)
        print(f"Authenticated user: {user.email}, Role: {user.role}")
        
        # 模拟验证过程
        verified_user = get_verified_user(user)
        print(f"Verified user: {verified_user.email}")
        
        # 模拟任务统计调用
        print("Testing task stats...")
        tasks = HSAITasks.get_tasks_by_user_id(verified_user.id)
        print(f"Found {len(tasks)} tasks")
        
        # 统计任务
        stats = {
            "total_tasks": len(tasks),
            "pending_tasks": 0,
            "in_progress_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "tasks_by_type": {}
        }
        
        for task in tasks:
            # 按状态统计
            if task.status == "pending":
                stats["pending_tasks"] += 1
            elif task.status == "in_progress":
                stats["in_progress_tasks"] += 1
            elif task.status == "completed":
                stats["completed_tasks"] += 1
            elif task.status == "failed":
                stats["failed_tasks"] += 1
            
            # 按类型统计
            if task.task_type not in stats["tasks_by_type"]:
                stats["tasks_by_type"][task.task_type] = 0
            stats["tasks_by_type"][task.task_type] += 1
            
        print(f"Stats result: {stats}")
        return stats
        
    except Exception as e:
        print(f"Error in full API call: {e}")
        import traceback
        traceback.print_exc()
        return None

# 运行异步测试
if __name__ == "__main__":
    result = asyncio.run(test_full_api_call())
    print(f"Final result: {result}")