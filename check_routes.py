import sys
import os

# 添加项目路径
sys.path.append(r"d:\Work\hsch\open-webui\backend")

# 设置环境变量
os.environ['WEBUI_SECRET_KEY'] = 't0p-s3cr3t'

# 简化导入，避免依赖问题
import importlib.util

# 动态导入main模块
spec = importlib.util.spec_from_file_location("main", r"d:\Work\hsch\open-webui\backend\open_webui\main.py")
main_module = importlib.util.module_from_spec(spec)

# 手动设置一些必要的环境变量来避免导入错误
os.environ['ENABLE_WEB_SEARCH'] = 'False'
os.environ['ENABLE_RAG_HYBRID_SEARCH'] = 'False'

try:
    spec.loader.exec_module(main_module)
    app = main_module.app
    
    # 打印所有路由
    print("All routes in the application:")
    for route in app.routes:
        if hasattr(route, 'path') and 'hsai' in route.path:
            print(f"  {route.methods} {route.path}")
            
    # 特别检查任务统计路由
    print("\nTask-related routes:")
    for route in app.routes:
        if hasattr(route, 'path') and 'task' in route.path:
            print(f"  {route.methods} {route.path}")
            
except Exception as e:
    print(f"Error loading app: {e}")
    import traceback
    traceback.print_exc()