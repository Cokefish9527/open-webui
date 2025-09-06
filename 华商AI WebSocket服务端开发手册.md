# 华商AI WebSocket服务端开发手册

## 概述
本文档为服务端开发人员提供华商AI WebSocket接口的开发指引，包括架构设计、核心组件、工作流集成等关键内容。

## 系统架构

### 整体架构图
```
客户端 ←→ WebSocket ←→ OpenWebUI ←→ n8n webhook
```

### 核心组件
1. **WebSocket路由器** (`routers/hsai_websocket.py`)
2. **聊天处理器** (`socket/hsai_chat_handler.py`)
3. **工作流管理器** (`utils/n8n_workflow_manager.py`)
4. **响应处理器** (`utils/n8n_response_processor.py`)
5. **监控器** (`utils/n8n_monitor.py`)

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

## 工作流集成

### 配置文件
```python
# config/n8n_workflows.py
N8N_WORKFLOW_WEBHOOKS = {
    N8NWorkflowType.MAIN: "https://webhook-n8n.hsai.cc/webhook/n8n_chat",
    N8NWorkflowType.COMPANY_INFO: "https://webhook-n8n.hsai.cc/webhook/business_information_get"
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
# WebSocket支持
ENABLE_WEBSOCKET_SUPPORT=True

# n8n工作流URL
N8N_MAIN_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/n8n_chat
N8N_COMPANY_INFO_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/business_information_get
```

### 启动服务
```bash
cd backend
python start_server.py
```

## 故障排除

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