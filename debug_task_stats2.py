import sys
import os

# 添加项目路径
sys.path.append(r"d:\Work\hsch\open-webui\backend")

from open_webui.env import WEBUI_SECRET_KEY
from open_webui.utils.auth import decode_token
from open_webui.models.hsai_tasks import HSAITasks

print(f"WEBUI_SECRET_KEY: {WEBUI_SECRET_KEY}")

# 解码token
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc"
decoded = decode_token(token)
print(f"Decoded token: {decoded}")

if decoded and "id" in decoded:
    user_id = decoded["id"]
    print(f"User ID: {user_id}")
    
    # 直接调用任务统计方法
    try:
        tasks = HSAITasks.get_tasks_by_user_id(user_id)
        print(f"Found {len(tasks)} tasks for user {user_id}")
        for task in tasks:
            print(f"  Task ID: {task.id}, Title: {task.title}, Status: {task.status}")
            
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
            
        print(f"Stats: {stats}")
        
    except Exception as e:
        print(f"Error getting tasks: {e}")
        import traceback
        traceback.print_exc()
else:
    print("Invalid token or missing user ID")