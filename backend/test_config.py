# 文件夹接口测试配置文件
# 请根据您的实际环境修改以下配置

# API服务器配置
BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1"

# 认证配置 - 可以选择使用TOKEN或用户名密码登录
# 方式1: 直接使用TOKEN（如果已有有效TOKEN）
TOKEN = "your_token_here"  # 请替换为您的实际TOKEN，格式：Bearer eyJhbGciOiJIUzI1NiIs...

# 方式2: 使用用户名密码登录获取TOKEN（推荐）
USE_LOGIN = True  # 设置为True时使用用户名密码登录，False时使用上面的TOKEN
LOGIN_EMAIL = "saiter2306@163.com"  # 登录邮箱
LOGIN_PASSWORD = "123456"  # 登录密码

# 测试配置
TEST_TIMEOUT = 30  # 请求超时时间（秒）
FOLDER_NAME_PREFIX = "test_folder"  # 测试文件夹名称前缀

# 调试配置
DEBUG_MODE = True  # 是否启用详细调试输出
PRINT_RESPONSE_DETAILS = True  # 是否打印API响应详情