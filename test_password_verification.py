import sys
import os

# 添加项目路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# 直接导入需要的模块
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return (
        pwd_context.verify(plain_password, hashed_password) if hashed_password else None
    )

# 测试密码验证
test_email = "saiter2306@163.com"
test_password = "123456"
hashed_password = "$2b$12$tg8FbituyONkC6v0FltOvufDkzZAxVBWCahDgi3hybatWCaMVsJJO"

print(f"测试用户: {test_email}")
print(f"输入密码: {test_password}")
print(f"存储的哈希密码: {hashed_password}")

try:
    result = verify_password(test_password, hashed_password)
    print(f"密码验证结果: {result}")
    
    if result:
        print("✅ 密码验证成功")
    else:
        print("❌ 密码验证失败")
        
except Exception as e:
    print(f"密码验证时发生错误: {e}")
    import traceback
    traceback.print_exc()