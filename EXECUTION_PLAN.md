# Python 3.11环境下的端到端测试执行计划

## 目标
在Python 3.11环境下完成WebSocket工作流的端到端测试，验证三个关键节点：
1. WebSocket连接建立成功并能正确收发消息
2. 服务端能正确接收WebSocket消息并路由到工作流
3. 服务端能接收工作流响应并结构化处理

## 执行步骤

### 步骤1: 环境准备
1. 使用Python 3.11创建新的虚拟环境
2. 安装项目依赖
3. 安装额外需要的包（如jieba）

### 步骤2: 启动服务端
1. 运行start_server.py启动服务
2. 验证服务是否正常运行在8081端口

### 步骤3: 运行端到端测试
1. 执行test_full_websocket_workflow_flow.py测试脚本
2. 监控日志输出，验证三个关键节点

### 步骤4: 验证结果
1. 检查测试日志
2. 确认所有关键节点都通过验证
3. 分析任何失败的原因并提出解决方案

## 详细操作指南

### 1. 创建Python 3.11虚拟环境
```powershell
# 删除旧的虚拟环境（如果存在）
Remove-Item -Recurse -Force .\venv

# 使用Python 3.11创建新的虚拟环境
C:\Users\bmkz\AppData\Local\Programs\Python\Python311\python.exe -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 升级pip
python -m pip install --upgrade pip
```

### 2. 安装依赖
```powershell
# 进入backend目录
cd backend

# 安装项目依赖
pip install -r requirements.txt

# 安装额外需要的包
pip install jieba
```

### 3. 启动服务端
```powershell
# 确保在backend目录下
python start_server.py
```

### 4. 运行测试
在新的终端窗口中：
```powershell
# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 进入backend目录
cd backend

# 运行端到端测试
python test_full_websocket_workflow_flow.py
```

## 预期日志输出

### 连接建立阶段
```
[INFO] User test_user_123 connected to HSAI chat handler
[INFO] WebSocket连接建立成功
```

### 消息处理阶段
```
[INFO] Processing message from user test_user_123: chat
[INFO] Selected workflow main based on entry type: chat
[INFO] Calling n8n workflow: main
[INFO] n8n workflow main completed successfully
```

### 响应处理阶段
```
[INFO] Processed main workflow response: success
[INFO] 收到消息: {"success": true, "messageType": "main", "displayText": "...", ...}
```

## 关键节点验证清单

### 节点1: WebSocket连接建立
- [ ] 连接成功建立日志
- [ ] 用户认证通过
- [ ] 可用工作流列表发送给客户端

### 节点2: 消息接收和路由
- [ ] 消息正确接收日志
- [ ] 工作流类型正确识别
- [ ] n8n webhook调用日志

### 节点3: 响应处理
- [ ] 工作流响应接收日志
- [ ] 响应结构化处理日志
- [ ] 格式化响应发送给客户端日志

## 故障排除

### 连接问题
1. 检查服务端是否在8081端口运行
2. 检查防火墙设置
3. 验证JWT token是否正确

### 路由问题
1. 检查消息格式是否符合ChatMessage模型
2. 验证entry_type字段是否正确
3. 检查n8n工作流配置

### 工作流调用问题
1. 验证n8n webhook URL是否可达
2. 检查n8n工作流是否已激活
3. 查看n8n日志确认请求接收

### 响应处理问题
1. 检查n8n返回的响应格式
2. 验证响应处理器是否正确处理数据
3. 确认客户端能正确解析响应