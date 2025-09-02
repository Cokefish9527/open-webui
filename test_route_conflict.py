import sys
import os

# 添加项目路径
sys.path.append(r"d:\Work\hsch\open-webui\backend")

from fastapi import APIRouter

# 模拟路由器行为
router = APIRouter(prefix="/hsai/tasks", tags=["hsai_tasks"])

# 检查路由注册
print("Registering routes...")

@router.get("/stats")
def get_stats():
    print("Stats route called")
    return {"message": "stats"}

@router.get("/{task_id}")
def get_task(task_id: str):
    print(f"Task route called with id: {task_id}")
    if task_id == "stats":
        return {"message": "task stats"}
    return {"message": f"task {task_id}"}

# 检查路由
routes = []
for route in router.routes:
    if hasattr(route, 'path'):
        routes.append((route.methods, route.path))
        
print("Registered routes:")
for methods, path in routes:
    print(f"  {methods} {path}")

# 测试路由匹配
from fastapi.routing import APIRoute

print("\nTesting route matching:")
for route in router.routes:
    if isinstance(route, APIRoute) and hasattr(route, 'path'):
        path = route.path
        if path == "/stats":
            print(f"Exact match for /stats: {route.endpoint.__name__}")
        elif "/{task_id}" in path:
            print(f"Parameter route: {route.endpoint.__name__}")