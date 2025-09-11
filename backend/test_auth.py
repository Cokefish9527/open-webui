import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.utils.auth import decode_token
from open_webui.models.users import Users

# 测试脚本中的JWT令牌
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc"

print("Testing JWT token authentication...")
print(f"Token: {token}")

try:
    # 解码JWT令牌
    data = decode_token(token)
    print(f"Decoded token data: {data}")
    
    if data is not None and "id" in data:
        user_id = data["id"]
        print(f"User ID from token: {user_id}")
        
        # 尝试获取用户信息
        user = Users.get_user_by_id(user_id)
        if user:
            print(f"User found: {user.name} ({user.email})")
            print(f"User role: {user.role}")
        else:
            print("User not found in database")
    else:
        print("Invalid token data")
        
except Exception as e:
    print(f"Error during authentication: {e}")