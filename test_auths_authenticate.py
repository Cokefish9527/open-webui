import sys
import os

# 添加项目路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# 设置环境变量
os.environ['DATABASE_URL'] = 'sqlite:///backend/data/webui.db'

try:
    # 导入认证模块
    from open_webui.models.auths import Auths
    
    # 测试用户信息
    test_email = "saiter2306@163.com"
    test_password = "123456"
    
    print(f"测试认证用户: {test_email}")
    print(f"测试密码: {test_password}")
    
    # 尝试认证用户
    print("\n正在尝试认证用户...")
    user = Auths.authenticate_user(test_email, test_password)
    
    if user:
        print("✅ 认证成功!")
        print(f"用户ID: {user.id}")
        print(f"用户名: {user.name}")
        print(f"用户邮箱: {user.email}")
        print(f"用户角色: {user.role}")
    else:
        print("❌ 认证失败!")
        print("可能的原因:")
        print("1. 邮箱或密码不正确")
        print("2. 用户未激活")
        print("3. 数据库连接问题")
        
except Exception as e:
    print(f"认证过程中发生错误: {e}")
    import traceback
    traceback.print_exc()