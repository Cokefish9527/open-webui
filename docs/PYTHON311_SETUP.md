# Python 3.11 环境设置指南

## 目标
根据用户要求，我们需要在Python 3.11环境下继续当前的WebSocket工作流测试任务，而不是在Python 3.8.6版本上进行修改。

## 当前状态
- 系统中已安装Python 3.11.9 (路径: `C:\Users\bmkz\AppData\Local\Programs\Python\Python311\python.exe`)
- 项目目录: `D:\Work\hsch\open-webui`
- 当前虚拟环境需要重新创建以使用Python 3.11

## 设置步骤

### 1. 删除旧的虚拟环境
```powershell
# 在项目根目录下执行
Remove-Item -Recurse -Force .\venv
```

### 2. 创建新的Python 3.11虚拟环境
```powershell
C:\Users\bmkz\AppData\Local\Programs\Python\Python311\python.exe -m venv venv
```

### 3. 激活虚拟环境
```powershell
.\venv\Scripts\Activate.ps1
```

### 4. 升级pip
```powershell
python -m pip install --upgrade pip
```

### 5. 安装项目依赖
```powershell
cd backend
pip install -r requirements.txt
```

### 6. 安装额外需要的包
```powershell
pip install jieba
```

## 验证环境
创建一个检查脚本来验证环境设置:

```python
# check_environment.py
import sys
import os

print("Python版本:", sys.version)
print("Python路径:", sys.executable)

# 检查是否在虚拟环境中
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("当前在虚拟环境中")
else:
    print("当前不在虚拟环境中")

# 检查关键包
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
```

运行检查脚本:
```powershell
python check_environment.py
```

## 启动服务
在Python 3.11环境下启动服务:

```powershell
cd backend
python start_server.py
```

## 运行端到端测试
在新的终端窗口中运行端到端测试:

```powershell
cd backend
python test_full_websocket_workflow_flow.py
```

## 预期结果
1. WebSocket连接成功建立
2. 服务端能正确接收WebSocket消息
3. 消息能正确路由到对应的工作流Webhook
4. 工作流响应能被正确接收并结构化处理
5. 响应能正确返回给WebSocket客户端

## 注意事项
1. 确保使用Python 3.11环境而不是3.8.6
2. 所有依赖包都应安装在新的虚拟环境中
3. 测试过程中需要完整输出每个关键节点的日志
4. 如遇到类型注解兼容性问题，可能需要调整代码以适配Python 3.11