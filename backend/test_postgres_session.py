import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

# 测试PostgreSQL会话管理器
try:
    from open_webui.models.hsai_business_good_video_v1 import get_postgres_session
    
    # 测试上下文管理器
    with get_postgres_session() as db:
        print("PostgreSQL会话管理器测试成功!")
        print(f"会话对象类型: {type(db)}")
    
    print("上下文管理器协议工作正常!")
    
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()