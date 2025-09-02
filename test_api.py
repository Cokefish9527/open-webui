import requests
import json

# 测试任务统计接口
url = "http://localhost:8080/api/v1/hsai/tasks/stats"

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")