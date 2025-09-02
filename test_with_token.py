import requests
import json

# 使用您提供的token访问任务统计接口
stats_url = "http://localhost:8080/api/v1/hsai/tasks/stats"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc"
}

try:
    response = requests.get(stats_url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"Parsed JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            print("Response is not valid JSON")
    else:
        print(f"Error response: {response.text}")
        
except Exception as e:
    print(f"Request failed with exception: {e}")