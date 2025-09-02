import sys
import os

# 添加项目路径
sys.path.append(r"d:\Work\hsch\open-webui\backend")

# 设置环境变量
os.environ['WEBUI_SECRET_KEY'] = 't0p-s3cr3t'

from fastapi.testclient import TestClient
from open_webui.main import app

# 创建测试客户端
client = TestClient(app)

def test_task_stats():
    # 使用您的token测试任务统计接口
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # 测试任务统计接口
    response = client.get("/api/v1/hsai/tasks/stats", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # 测试其他统计接口作为对比
    response2 = client.get("/api/v1/hsai/dashboard/stats", headers=headers)
    print(f"Dashboard Stats Status Code: {response2.status_code}")
    if response2.status_code == 200:
        print(f"Dashboard Stats Response: {response2.json()}")
    else:
        print(f"Dashboard Stats Error: {response2.text}")

if __name__ == "__main__":
    test_task_stats()