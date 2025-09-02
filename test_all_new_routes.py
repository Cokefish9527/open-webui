import requests
import json

# 使用您提供的token测试所有新路由
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc"
headers = {
    "Authorization": f"Bearer {token}"
}

# 测试路由列表
routes = [
    ("任务统计", "http://localhost:8080/api/v1/hsai/tasks/statistics"),
    ("素材统计", "http://localhost:8080/api/v1/hsai/materials/statistics"),
    ("对话统计", "http://localhost:8080/api/v1/hsai/chat/statistics"),
    ("工作台统计", "http://localhost:8080/api/v1/hsai/dashboard/stats")  # 这个应该已经正常工作
]

for name, url in routes:
    try:
        response = requests.get(url, headers=headers)
        print(f"{name} - URL: {url}")
        print(f"  Status Code: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  Success: {json.dumps(data, indent=2, ensure_ascii=False)[:100]}...")
            except json.JSONDecodeError:
                print(f"  Success: Response is not JSON")
        else:
            print(f"  Error: {response.text}")
        print()
    except Exception as e:
        print(f"{name} - URL: {url}")
        print(f"  Request failed with exception: {e}")
        print()