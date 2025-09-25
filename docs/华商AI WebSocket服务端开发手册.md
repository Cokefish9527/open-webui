# 华商AI WebSocket服务端开发手册

## 概述
本文档为服务端开发人员提供华商AI WebSocket接口的开发指引，包括架构设计、核心组件、工作流集成等关键内容。

## 系统架构

### 整体架构图
```
客户端 ←→ Socket.IO ←→ OpenWebUI ←→ n8n webhook ←→ Redis信号
```

### 架构说明
1. **前端通信**: 使用OpenWebUI原生的Socket.IO与服务端通讯
2. **服务端转发**: 通过WebHook与n8n工作流通讯
3. **消息重组**: 服务端对n8n返回的字符串进行重新组织
4. **实时通知**: 通过Redis信号进行长任务的实时状态通知

### 核心组件
1. **Socket.IO路由器** (`routers/hsai_websocket.py`)
2. **聊天处理器** (`socket/hsai_chat_handler.py`) 
3. **工作流管理器** (`utils/n8n_workflow_manager.py`)
4. **响应处理器** (`utils/n8n_response_processor.py`)
5. **监控器** (`utils/n8n_monitor.py`)
6. **Redis信号处理器** (`utils/redis_signal_handler.py`)

## WebSocket路由器

### 路由端点
```python
@router.websocket("/hsai/ws/{user_id}")
async def hsai_websocket_endpoint(
    websocket: WebSocket, 
    user_id: str,
    token: str = Query(...),
    session_id: str = Query(None)
)
```

### 认证流程
1. 验证JWT令牌
2. 解析用户信息
3. 建立WebSocket连接

### 消息处理循环
```python
while True:
    data = await websocket.receive_text()
    message_data = json.loads(data)
    await chat_handler.handle_message(user_id, message_data)
```

## 聊天处理器

### 核心方法
```python
class HSAIChatHandler:
    async def connect(self, websocket: WebSocket, user_id: str)
    async def disconnect(self, user_id: str)
    async def handle_message(self, user_id: str, message_data: Dict[str, Any])
    async def _handle_chat_message(self, user_id: str, message: ChatMessage)
```

### 消息路由逻辑
1. 根据入口类型选择工作流
2. 获取或创建会话
3. 调用n8n工作流
4. 处理响应并返回客户端

### 工作流选择策略
```python
def _select_workflow_by_entry(self, message: ChatMessage) -> WorkflowType:
    # 1. 优先使用明确指定的工作流类型
    if message.workflow_type:
        return message.workflow_type
    
    # 2. 根据入口类型选择工作流
    if message.entry_type:
        return get_workflow_by_entry_type(message.entry_type)
    
    # 3. 基于关键词的智能选择
    return self._select_workflow_by_keywords(message.content)
```

## Redis信号机制

### 长任务处理流程
```python
class RedisSignalHandler:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.signal_patterns = {
            'workflow_status': 'n8n:workflow:status:*',
            'task_complete': 'n8n:task:complete:*',
            'video_synthesis': 'n8n:video:synthesis:*'
        }
    
    async def monitor_signals(self):
        """监听Redis信号变化"""
        pubsub = self.redis_client.pubsub()
        
        # 订阅相关信号频道
        for pattern in self.signal_patterns.values():
            pubsub.psubscribe(pattern)
        
        async for message in pubsub.listen():
            if message['type'] == 'pmessage':
                await self._handle_signal(message)
    
    async def _handle_signal(self, message):
        """处理Redis信号"""
        channel = message['channel'].decode('utf-8')
        data = json.loads(message['data'].decode('utf-8'))
        
        if 'workflow:status' in channel:
            await self._handle_workflow_status(data)
        elif 'task:complete' in channel:
            await self._handle_task_complete(data)
        elif 'video:synthesis' in channel:
            await self._handle_video_synthesis(data)
    
    async def _handle_workflow_status(self, data):
        """处理工作流状态更新"""
        user_id = data.get('user_id')
        status = data.get('status')
        progress = data.get('progress', 0)
        
        # 通过Socket.IO向前端发送状态更新
        await sio.emit('workflow_status', {
            'status': status,
            'progress': progress,
            'timestamp': datetime.now().isoformat()
        }, room=f'user_{user_id}')
    
    async def _handle_task_complete(self, data):
        """处理任务完成信号"""
        user_id = data.get('user_id')
        task_result = data.get('result')
        
        # 从数据库读取n8n计算的KPI数据
        kpi_data = await self._fetch_kpi_data(user_id)
        
        # 发送任务完成通知
        await sio.emit('task_complete', {
            'result': task_result,
            'kpi_data': kpi_data,
            'timestamp': datetime.now().isoformat()
        }, room=f'user_{user_id}')

# 全局Redis信号处理器
redis_signal_handler = RedisSignalHandler()
```

### 信号类型定义
1. **工作流状态信号**: `n8n:workflow:status:{execution_id}`
2. **任务完成信号**: `n8n:task:complete:{task_id}`
3. **视频合成信号**: `n8n:video:synthesis:{video_id}`
4. **KPI计算信号**: `n8n:kpi:calculated:{user_id}`

## 工作流集成

### 配置文件
```python
# config/n8n_workflows.py
N8N_WORKFLOW_WEBHOOKS = {
    N8NWorkflowType.MAIN: "https://webhook-n8n.hsai.cc/webhook/n8n_chat",
    N8NWorkflowType.COMPANY_INFO: "https://webhook-n8n.hsai.cc/webhook/business_information_get01",
    N8NWorkflowType.VIRAL_LEARNING: "https://webhook-n8n.hsai.cc/webhook/keywords2video"
}

# 工作流任务描述
WORKFLOW_DESCRIPTIONS = {
    N8NWorkflowType.MAIN: "协助用户完成视频合成发布的任务",
    N8NWorkflowType.COMPANY_INFO: "用户初始信息收集及项目创建",
    N8NWorkflowType.VIRAL_LEARNING: "爆款视频抓取和学习分析"
}
```

### 工作流调用
```python
async def _call_n8n_workflow(self, workflow_type: WorkflowType, payload: Dict[str, Any]) -> Dict[str, Any]:
    config = self.workflow_configs[workflow_type]
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            config.webhook_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=config.timeout)
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"n8n workflow failed with status {response.status}")
```

### 重试机制
```python
async def _call_n8n_workflow_with_retry(
    self, 
    workflow_type: WorkflowType, 
    payload: Dict[str, Any],
    execution_id: str
) -> Dict[str, Any]:
    while True:
        try:
            return await self._call_n8n_workflow(workflow_type, payload)
        except Exception as e:
            if n8n_monitor.should_retry(execution_id, str(e)):
                await n8n_monitor.retry_execution(execution_id)
                continue
            else:
                raise
```

## 响应处理

### 响应处理器
```python
class N8NResponseProcessor:
    @staticmethod
    async def process_response(
        raw_response: Dict[str, Any], 
        workflow_type: str,
        execution_start_time: float,
        execution_id: Optional[str] = None
    ) -> ProcessedResponse
    
    @staticmethod
    def format_for_client(processed_response: ProcessedResponse) -> Dict[str, Any]
```

### 格式化规则
```javascript
// 符合华商AI工作流前端对接规范的响应格式
{
  "success": true,
  "messageType": "main",
  "displayText": "响应内容",
  "data": {},
  "status": "success",
  "timestamp": "2023-01-01T00:00:00.000Z"
}
```

## 监控系统

### 监控器功能
```python
class N8NMonitor:
    def start_execution(self, execution_id: str, workflow_type: N8NWorkflowType, user_id: str, session_id: str)
    def record_execution(self, workflow_type: str, success: bool, response_time: float, error_message: Optional[str] = None)
    def get_system_health(self) -> Dict[str, Any]
    def should_retry(self, execution_id: str, error_message: str) -> bool
```

### 健康检查
```python
def get_system_health(self) -> Dict[str, Any]:
    return {
        "overall_status": overall_status.value,
        "workflow_statuses": workflow_statuses,
        "uptime_seconds": uptime,
        "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None
    }
```

## 开发规范

### 代码结构
```
backend/open_webui/
├── config/
│   └── n8n_workflows.py          # 工作流配置
├── routers/
│   └── hsai_websocket.py          # WebSocket路由
├── socket/
│   └── hsai_chat_handler.py       # 聊天处理器
└── utils/
    ├── n8n_workflow_manager.py    # 工作流管理器
    ├── n8n_response_processor.py  # 响应处理器
    └── n8n_monitor.py             # 监控器
```

### 日志规范
```python
import logging
log = logging.getLogger(__name__)

# 信息日志
log.info(f"User {user_id} connected to HSAI chat handler")

# 调试日志
log.debug(f"Processing message from user {user_id}: {message.type}")

# 错误日志
log.error(f"Error processing message from user {user_id}: {e}")
```

### 异常处理
```python
try:
    # 业务逻辑
    await chat_handler.handle_message(user_id, message_data)
except json.JSONDecodeError as e:
    log.error(f"Invalid JSON from user {user_id}: {e}")
    await websocket.send_text(json.dumps({
        "type": "error",
        "content": "Invalid JSON format",
        "timestamp": time.time()
    }, ensure_ascii=False))
except Exception as e:
    log.error(f"Error processing message from user {user_id}: {e}")
    await websocket.send_text(json.dumps({
        "type": "error",
        "content": f"Message processing failed: {str(e)}",
        "timestamp": time.time()
    }, ensure_ascii=False))
```

## 测试指南

### 单元测试
```python
def test_select_workflow_by_entry():
    # 测试入口类型选择工作流
    message = ChatMessage(
        type=MessageType.CHAT,
        content="请帮我收集公司信息",
        user_id="test_user",
        entry_type="company"
    )
    
    workflow_type = chat_handler._select_workflow_by_entry(message)
    assert workflow_type == WorkflowType.COMPANY_INFO
```

### 集成测试
```python
async def test_websocket_workflow():
    # 测试WebSocket端到端流程
    token = generate_test_token("test_user")
    websocket_url = f"ws://localhost:8081/api/v1/ws/hsai/ws/test_user?token={token}"
    
    async with websockets.connect(websocket_url) as websocket:
        # 发送测试消息
        await websocket.send(json.dumps({
            "type": "chat",
            "content": "你好",
            "user_id": "test_user",
            "entry_type": "chat"
        }))
        
        # 接收响应
        response = await websocket.recv()
        response_data = json.loads(response)
        
        assert response_data["success"] == True
        assert response_data["messageType"] == "main"
```

## 部署配置

### 环境变量
```bash
# Socket.IO支持
ENABLE_SOCKETIO_SUPPORT=True

# n8n工作流URL
N8N_MAIN_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/n8n_chat
N8N_COMPANY_INFO_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/business_information_get01
N8N_VIRAL_LEARNING_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/keywords2video

# Redis配置（用于信号机制）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# 长任务处理配置
LONG_TASK_TIMEOUT=300
REDIS_SIGNAL_TIMEOUT=60
```

### 启动服务
```bash
cd backend
python start_server.py
```

## HSAI WebSocket交互协议说明

### 协议版本与兼容性
**版本**: v1.1.0  
**更新日期**: 2025-09-13  
**适用范围**: 前端 ↔ 后端 ↔ n8n工作流  

### 文档结构说明
1. 快速开始指南
2. 连接建立（握手/认证/心跳/重连）
3. 客户端请求消息格式Schema与示例
4. 服务端 WebSocket接口清单（功能/参数/返回/错误）
5. 服务端主动推送通知类型与数据结构
6. 常见错误与排查
7. 版本与兼容性说明
8. 术语与接口口径一致性校验

### 核心功能特性
- 客户端-服务端连接步骤与示例代码
- 客户端请求消息格式规范与示例
- 服务端 WebSocket接口清单（功能与参数）
- 服务端主动推送通知类型与数据结构
- 错误处理与重连建议
- 术语与接口口径一致性校验

### 连接建立协议
**连接URL**: `ws://<host>:<port>/hsai/ws/{user_id}?token=<auth_token>[&session_id=<session_id>]`

**参数说明**:
- `user_id`: 用户唯一标识符
- `token`: 认证令牌
- `session_id`: (可选) 会话 ID

**连接流程**:
1. 前端通过WebSocket连接到指定 URL
2. 后端验证 token和 user_id
3. 验证通过后建立连接并发送连接确认消息

### 连接确认消息
```json
{
  "type": "status",
  "content": "连接成功",
  "timestamp": 1640995200.0,
  "available_workflows": [
    {
      "type": "main",
      "name": "主工作流",
      "description": "主工作流 - 处理通用对话和任务分发"
    },
    {
      "type": "company_info",
      "name": "公司信息收集及作战地图梳理",
      "description": "公司信息收集及作战地图梳理 - 收集公司信息并生成作战地图"
    }
  ]
}
```

### 消息格式协议

#### 客户端发送消息格式
```json
{
  "type": "消息类型",
  "content": "消息内容",
  "user_id": "用户 ID",
  "session_id": "会话 ID(可选)",
  "workflow_type": "工作流类型(可选)",
  "entry_type": "对话入口类型(可选)",
  "metadata": {
    "额外元数据": "值"
  }
}
```

**消息类型**:
- `chat`: 聊天消息
- `workflow_trigger`: 工作流触发消息

#### 服务端响应消息格式
```json
{
  "type": "消息类型",
  "content": "消息内容",
  "timestamp": 1640995200.0,
  "session_id": "会话 ID",
  "user_id": "用户 ID",
  "execution_id": "执行 ID",
  "data": {
    "响应数据": "值"
  }
}
```

**消息类型**:
- `status`: 状态消息
- `workflow_response`: 工作流响应消息
- `error`: 错误消息

### 工作流交互协议

#### 主要工作流
1. **主工作流** (`main`)
   - URL: `https://webhook-n8n.hsai.cc/webhook/main-workflow`
   - 用途: 处理通用对话和任务分发

2. **公司信息收集工作流** (`company_info`)
   - URL: `https://webhook-n8n.hsai.cc/webhook/company-info`
   - 用途: 收集公司信息并生成作战地图

#### 工作流触发方式
1. **聊天消息触发**:
   - 发送 `type` 为 `chat` 的消息
   - 系统根据入口类型或关键词自动选择工作流

2. **直接工作流触发**:
   - 发送 `type` 为 `workflow_trigger` 的消息
   - 明确指定 `workflow_type`

### 错误处理协议

#### 错误消息格式
```json
{
  "type": "error",
  "content": "错误描述",
  "timestamp": 1640995200.0
}
```

#### 常见错误类型
- 认证失败
- 消息格式错误
- 工作流执行失败
- 网络超时

### 会话管理协议

#### 会话创建
- 系统自动为每个用户创建会话
- 会话 ID在首次交互时生成并返回

#### 会话维持
- WebSocket连接保持期间会话有效
- 连接断开后会话信息保留一段时间

### 常见问题
1. **认证失败(403)**: 检查JWT令牌是否有效且与用户ID匹配
2. **连接拒绝**: 确认服务端是否正常运行
3. **响应超时**: 检查n8n工作流是否可访问

### 日志查看
```bash
# 查看服务端日志
tail -f backend/error_log.txt

# 查看WebSocket相关日志
grep "SOCKET" backend/error_log.txt
```

### 性能监控
```python
# 监控工作流执行情况
curl http://localhost:8081/api/v1/ws/hsai/ws/health

# 查看活跃连接
curl http://localhost:8081/api/v1/ws/hsai/ws/status
```