import sys
import os

print("Python版本:", sys.version)
print("Python路径:", sys.executable)

# 检查是否在虚拟环境中
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("当前在虚拟环境中")
else:
    print("当前不在虚拟环境中")

# 检查一些关键包是否可以导入
try:
    import fastapi
    print("FastAPI版本:", fastapi.__version__)
except ImportError:
    print("FastAPI未安装")

try:
    import uvicorn
    print("Uvicorn已安装")
except ImportError:
    print("Uvicorn未安装")

try:
    import pydantic
    print("Pydantic版本:", pydantic.__version__)
except ImportError:
    print("Pydantic未安装")