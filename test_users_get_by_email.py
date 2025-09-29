import sys
import os

# 添加项目路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# 设置环境变量
os.environ['DATABASE_URL'] = 'sqlite:///backend/data/webui.db'

try:
    # 导入用户模型
    from open_webui.models.users import Users
    
    # 测试用户信息
    test_email = "saiter2306@163.com"
    
    print(f"测试获取用户: {test_email}")
    
    # 尝试获取用户
    print("\n正在尝试获取用户...")
    user = Users.get_user_by_email(test_email)
    
    if user:
        print("✅ 获取用户成功!")
        print(f"用户ID: {user.id}")
        print(f"用户名: {user.name}")
        print(f"用户邮箱: {user.email}")
        print(f"用户角色: {user.role}")
    else:
        print("❌ 获取用户失败!")
        print("可能的原因:")
        print("1. 数据库连接问题")
        print("2. 查询逻辑问题")
        print("3. 用户不存在")
        
except Exception as e:
    print(f"获取用户过程中发生错误: {e}")
    import traceback
    traceback.print_exc()