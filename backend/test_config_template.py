# 测试配置文件模板
# 复制此文件为 test_config.py 并填入实际值

# 认证配置
AUTH_CONFIG = {
    # 方式1: 使用Token（推荐）
    "token": "your_actual_token_here",
    
    # 方式2: 使用用户名密码（token无效时使用）
    "email": "admin@example.com",
    "password": "admin123"
}

# 服务器配置
SERVER_CONFIG = {
    "base_url": "http://localhost:8080",
    "timeout": 30
}

# 测试配置
TEST_CONFIG = {
    "enterprise_id": "default",
    "test_folder_prefix": "回收站测试目录",
    "test_material_prefix": "回收站测试素材"
}

# 使用说明：
# 1. 将此文件复制为 test_config.py
# 2. 填入实际的token或用户名密码
# 3. 根据需要调整服务器地址和企业ID
# 4. 测试脚本会自动导入配置