import sys
import os

# 添加项目路径
sys.path.append(r"d:\Work\hsch\open-webui\backend")

# 设置环境变量
os.environ['WEBUI_SECRET_KEY'] = 'your_secret_key_here'

from open_webui.utils.auth import decode_token
from open_webui.models.hsai_tasks import HSAITasks

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
    except Exception as e:
        print(f"Error getting tasks: {e}")
        import traceback
        traceback.print_exc()
else:
    print("Invalid token or missing user ID")