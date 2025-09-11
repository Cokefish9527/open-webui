import jwt

# 测试脚本中的JWT令牌
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc"

try:
    # 解码JWT令牌（使用默认的secret key，这里可能不正确）
    decoded = jwt.decode(token, options={"verify_signature": False})
    print("Decoded token:")
    print(decoded)
    
    user_id = decoded.get('id')
    print(f"\nUser ID from token: {user_id}")
    
except Exception as e:
    print(f"Error decoding token: {e}")