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
    from open_webui.models.auths import Auth
    from open_webui.models.users import Users
    from open_webui.utils.auth import verify_password
    
    # 测试用户信息
    test_email = "saiter2306@163.com"
    test_password = "123456"
    
    print(f"测试认证用户: {test_email}")
    print(f"测试密码: {test_password}")
    
    # 步骤1: 检查用户是否存在
    print("\n步骤1: 检查用户是否存在...")
    user = Users.get_user_by_email(test_email)
    if user:
        print(f"✅ 找到用户: {user.name} ({user.email})")
        print(f"  用户ID: {user.id}")
        print(f"  用户角色: {user.role}")
    else:
        print("❌ 未找到用户")
        sys.exit(1)
    
    # 步骤2: 检查认证记录
    print("\n步骤2: 检查认证记录...")
    try:
        with get_db() as db:
            auth = db.query(Auth).filter_by(id=user.id, active=True).first()
            if auth:
                print(f"✅ 找到认证记录:")
                print(f"  邮箱: {auth.email}")
                print(f"  活跃: {auth.active}")
                print(f"  密码哈希: {auth.password}")
                
                # 步骤3: 验证密码
                print("\n步骤3: 验证密码...")
                password_result = verify_password(test_password, auth.password)
                print(f"  密码验证结果: {password_result}")
                
                if password_result:
                    print("✅ 密码验证成功!")
                else:
                    print("❌ 密码验证失败!")
            else:
                print("❌ 未找到认证记录或用户未激活")
    except Exception as e:
        print(f"查询认证记录时发生错误: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"认证过程中发生错误: {e}")
    import traceback
    traceback.print_exc()