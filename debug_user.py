import sys
import os

# 添加项目路径
sys.path.append(r"d:\Work\hsch\open-webui\backend")

from open_webui.env import WEBUI_SECRET_KEY
from open_webui.utils.auth import decode_token
from open_webui.models.users import Users

print(f"WEBUI_SECRET_KEY: {WEBUI_SECRET_KEY}")

# 解码token
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc"
decoded = decode_token(token)
print(f"Decoded token: {decoded}")

if decoded and "id" in decoded:
    user_id = decoded["id"]
    print(f"User ID: {user_id}")
    
    # 检查用户是否存在
    try:
        user = Users.get_user_by_id(user_id)
        if user:
            print(f"User found: {user.email}, Role: {user.role}")
        else:
            print("User not found in database")
    except Exception as e:
        print(f"Error getting user: {e}")
        import traceback
        traceback.print_exc()
else:
    print("Invalid token or missing user ID")