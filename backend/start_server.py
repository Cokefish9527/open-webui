import uvicorn
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    uvicorn.run(
        "open_webui.main:app",
        host="0.0.0.0",
        port=8081,
        forwarded_allow_ips="*",
        workers=1,
        ws="auto"
    )