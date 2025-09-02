import sys
import os

# 添加项目路径
sys.path.append(r"d:\Work\hsch\open-webui\backend")

from open_webui.env import WEBUI_SECRET_KEY
from open_webui.utils.auth import decode_token
from open_webui.models.users import Users
from open_webui.models.hsai_tasks import HSAITasks

print(f"WEBUI_SECRET_KEY: {WEBUI_SECRET_KEY}")

def test_api_call():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc"
    
    try:
        # 直接解码token（模拟FastAPI的认证过程）
        data = decode_token(token)
        print(f"Decoded token data: {data}")
        
        if data is not None and "id" in data:
            user_id = data["id"]
            print(f"User ID from token: {user_id}")
            
            # 获取用户（模拟get_current_user的部分逻辑）
            user = Users.get_user_by_id(user_id)
            if user is None:
                print("User not found")
                return None
                
            print(f"User found: {user.email}, Role: {user.role}")
            
            # 验证用户权限（模拟get_verified_user）
            if user.role not in {"user", "admin"}:
                print("User role not allowed")
                return None
                
            print("User verified")
            
            # 调用任务统计接口逻辑
            print("Calling task stats logic...")
            tasks = HSAITasks.get_tasks_by_user_id(user.id)
            print(f"Found {len(tasks)} tasks for user {user.id}")
            
            # 统计任务
            stats = {
                "total_tasks": len(tasks),
                "pending_tasks": 0,
                "in_progress_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "tasks_by_type": {}
            }
            
            completion_times = []
            
            for task in tasks:
                # 按状态统计
                if task.status == "pending":
                    stats["pending_tasks"] += 1
                elif task.status == "in_progress":
                    stats["in_progress_tasks"] += 1
                elif task.status == "completed":
                    stats["completed_tasks"] += 1
                    # 计算完成时间
                    if task.started_at and task.completed_at:
                        completion_times.append(task.completed_at - task.started_at)
                elif task.status == "failed":
                    stats["failed_tasks"] += 1
                
                # 按类型统计
                if task.task_type not in stats["tasks_by_type"]:
                    stats["tasks_by_type"][task.task_type] = 0
                stats["tasks_by_type"][task.task_type] += 1
            
            # 计算平均完成时间
            if completion_times:
                stats["avg_completion_time"] = sum(completion_times) / len(completion_times)
            
            print(f"Final stats: {stats}")
            return stats
        else:
            print("Invalid token")
            return None
            
    except Exception as e:
        print(f"Error in API call: {e}")
        import traceback
        traceback.print_exc()
        return None

# 运行测试
if __name__ == "__main__":
    result = test_api_call()
    print(f"Final result: {result}")