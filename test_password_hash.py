import sys
import os

# 添加项目路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# 直接导入需要的模块
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

# 测试生成密码哈希
test_password = "123456"

print(f"输入密码: {test_password}")

try:
    hashed = get_password_hash(test_password)
    print(f"生成的哈希密码: {hashed}")
    
    # 尝试验证
    result = pwd_context.verify(test_password, hashed)
    print(f"验证结果: {result}")
    
except Exception as e:
    print(f"密码哈希处理时发生错误: {e}")
    import traceback
    traceback.print_exc()