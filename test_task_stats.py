import requests
import json

# 首先登录获取认证token
login_url = "http://localhost:8080/api/auth/login"
login_data = {
    "email": "admin@example.com",  # 替换为实际的管理员邮箱
    "password": "admin"  # 替换为实际的密码
}

try:
    # 登录获取token
    login_response = requests.post(login_url, json=login_data)
    print(f"Login Status Code: {login_response.status_code}")
    
    if login_response.status_code == 200:
        token_data = login_response.json()
        token = token_data.get('token')
        print(f"Token: {token}")
        
        # 使用token访问任务统计接口
        stats_url = "http://localhost:8080/api/v1/hsai/tasks/stats"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        stats_response = requests.get(stats_url, headers=headers)
        print(f"Stats Status Code: {stats_response.status_code}")
        print(f"Stats Response: {stats_response.text}")
    else:
        print(f"Login failed: {login_response.text}")
        
except Exception as e:
    print(f"Error: {e}")