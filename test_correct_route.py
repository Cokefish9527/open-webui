import requests
import json

# 使用您提供的token访问正确的任务统计接口
stats_url = "http://localhost:8080/api/v1/hsai/tasks/stats"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc"
}

try:
    response = requests.get(stats_url, headers=headers)
    print(f"URL: {stats_url}")
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

# 同时测试其他可能的统计接口
other_stats_urls = [
    "http://localhost:8080/api/v1/hsai/materials/stats",
    "http://localhost:8080/api/v1/hsai/dashboard/stats",
    "http://localhost:8080/api/v1/hsai/chat/stats"
]

for url in other_stats_urls:
    try:
        response = requests.get(url, headers=headers)
        print(f"\nURL: {url}")
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Request to {url} failed with exception: {e}")