import os
import sys

# 设置数据库URL环境变量
os.environ['DATABASE_URL'] = 'sqlite:///webui.db'

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入并运行uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "open_webui.main:app",
        host="0.0.0.0",
        port=8080,
        forwarded_allow_ips="*",
        workers=1,
        ws="auto"
    )