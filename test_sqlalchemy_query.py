import sys
import os

# 添加项目路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# 设置环境变量
os.environ['DATABASE_URL'] = 'sqlite:///backend/data/webui.db'

try:
    # 导入需要的模块
    from open_webui.internal.db import get_db
    from open_webui.models.users import User
    from open_webui.models.auths import Auth
    
    # 测试用户信息
    test_email = "saiter2306@163.com"
    
    print(f"测试SQLAlchemy查询: {test_email}")
    
    # 尝试直接使用SQLAlchemy查询
    print("\n步骤1: 使用SQLAlchemy查询用户表...")
    try:
        with get_db() as db:
            user = db.query(User).filter_by(email=test_email).first()
            if user:
                print("✅ 用户表查询成功!")
                print(f"用户ID: {user.id}")
                print(f"用户名: {user.name}")
                print(f"用户邮箱: {user.email}")
                print(f"用户角色: {user.role}")
            else:
                print("❌ 用户表查询失败 - 未找到用户")
    except Exception as e:
        print(f"用户表查询错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 尝试查询认证表
    print("\n步骤2: 使用SQLAlchemy查询认证表...")
    try:
        with get_db() as db:
            auth = db.query(Auth).filter_by(email=test_email).first()
            if auth:
                print("✅ 认证表查询成功!")
                print(f"认证ID: {auth.id}")
                print(f"认证邮箱: {auth.email}")
                print(f"活跃状态: {auth.active}")
            else:
                print("❌ 认证表查询失败 - 未找到认证记录")
    except Exception as e:
        print(f"认证表查询错误: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"查询过程中发生错误: {e}")
    import traceback
    traceback.print_exc()