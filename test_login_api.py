import requests
import json

# 测试登录API
url = "http://localhost:8080/api/v1/auths/signin"
headers = {"Content-Type": "application/json"}

# 测试用户凭据
payload = {
    "email": "saiter2306@163.com",
    "password": "123456"
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    print(f"状态码: {response.status_code}")
    print(f"响应头: {response.headers}")
    
    if response.status_code == 200:
        print("登录成功!")
        print(f"响应数据: {response.json()}")
    else:
        print(f"登录失败: {response.status_code}")
        try:
            print(f"错误信息: {response.json()}")
        except:
            print(f"响应内容: {response.text}")
            
except Exception as e:
    print(f"请求失败: {e}")