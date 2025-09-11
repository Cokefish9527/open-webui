# OpenWebUI与n8n协同模式分析与修正方案

## 🎯 需求分析

### 预期协同模式
```
客户端 ←→ WebSocket ←→ OpenWebUI服务端 ←→ n8n Webhook ←→ n8n工作流
```

**核心流程**:
1. 客户端通过WebSocket与OpenWebUI服务端直连
2. 服务端接收客户端对话消息
3. 服务端转发消息到对应的n8n webhook
4. n8n处理后返回结果
5. 服务端进行结构化处理
6. 通过WebSocket返回给客户端

## 🔍 当前设计问题分析

### ❌ 问题1: WebSocket集成不完整
**当前状态**: WebSocket事件处理存在，但缺少与对话系统的深度集成
```python
# 现有实现 - 仅有基础事件处理
class HSAIWebSocketNotifier:
    async def send_to_user(self, user_id: str, message: dict):
        # 基础消息发送
```

**缺失功能**:
- 对话消息的WebSocket处理
- 实时消息转发机制
- n8n响应的WebSocket回传

### ❌ 问题2: n8n集成方式不符合需求
**当前设计**: 工作流作为独立服务调用
```python
# 现有实现 - 独立工作流触发
@router.post("/trigger")
async def trigger_workflow(workflow_id: str, input_data: dict):
    # 独立的工作流调用
```

**设计偏差**:
- 没有与对话系统集成
- 缺少webhook回调处理
- 没有实时消息转发机制

### ❌ 问题3: 对话处理缺少n8n集成
**当前设计**: 对话管理独立于工作流
```python
# 现有实现 - 独立对话处理
@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, content: str):
    # 直接AI对话，没有n8n集成
```

**缺失功能**:
- 消息到n8n的自动转发
- n8n响应的结构化处理
- WebSocket实时通信

## ✅ 修正方案设计

### 1. WebSocket对话处理器

```python
# backend/open_webui/socket/hsai_chat_handler.py
import asyncio
import json
import logging
from typing import Dict, Optional
from fastapi import WebSocket
import httpx

log = logging.getLogger(__name__)

class HSAIChatWebSocketHandler:
    """HSAI对话WebSocket处理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.n8n_webhooks: Dict[str, str] = {}   # session_id -> webhook_url
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        log.info(f"WebSocket connected for user: {user_id}")
    
    async def disconnect(self, user_id: str):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        log.info(f"WebSocket disconnected for user: {user_id}")
    
    async def handle_message(self, user_id: str, message_data: dict):
        """处理客户端消息"""
        try:
            message_type = message_data.get("type")
            
            if message_type == "chat_message":
                await self._handle_chat_message(user_id, message_data)
            elif message_type == "session_config":
                await self._handle_session_config(user_id, message_data)
            else:
                await self._send_error(user_id, f"Unknown message type: {message_type}")
                
        except Exception as e:
            log.error(f"Error handling message: {e}")
            await self._send_error(user_id, str(e))
    
    async def _handle_chat_message(self, user_id: str, message_data: dict):
        """处理对话消息 - 核心协同逻辑"""
        session_id = message_data.get("session_id")
        content = message_data.get("content")
        
        if not session_id or not content:
            await self._send_error(user_id, "Missing session_id or content")
            return
        
        # 1. 发送消息状态给客户端
        await self._send_to_user(user_id, {
            "type": "message_status",
            "status": "processing",
            "message_id": message_data.get("message_id")
        })
        
        # 2. 获取对应的n8n webhook
        webhook_url = self.n8n_webhooks.get(session_id)
        if not webhook_url:
            await self._send_error(user_id, "No n8n webhook configured for this session")
            return
        
        # 3. 转发消息到n8n
        try:
            n8n_response = await self._forward_to_n8n(webhook_url, {
                "user_id": user_id,
                "session_id": session_id,
                "message": content,
                "timestamp": message_data.get("timestamp"),
                "metadata": message_data.get("metadata", {})
            })
            
            # 4. 结构化处理n8n响应
            processed_response = await self._process_n8n_response(n8n_response)
            
            # 5. 通过WebSocket返回给客户端
            await self._send_to_user(user_id, {
                "type": "chat_response",
                "session_id": session_id,
                "response": processed_response,
                "timestamp": asyncio.get_event_loop().time()
            })
            
        except Exception as e:
            log.error(f"Error in n8n communication: {e}")
            await self._send_error(user_id, f"n8n processing failed: {str(e)}")
    
    async def _forward_to_n8n(self, webhook_url: str, payload: dict) -> dict:
        """转发消息到n8n webhook"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def _process_n8n_response(self, n8n_response: dict) -> dict:
        """结构化处理n8n响应"""
        # 标准化n8n响应格式
        processed = {
            "content": n8n_response.get("content", ""),
            "type": n8n_response.get("type", "text"),
            "metadata": {
                "model": n8n_response.get("model"),
                "tokens": n8n_response.get("tokens"),
                "processing_time": n8n_response.get("processing_time"),
                "workflow_id": n8n_response.get("workflow_id"),
                "execution_id": n8n_response.get("execution_id")
            },
            "attachments": n8n_response.get("attachments", []),
            "actions": n8n_response.get("suggested_actions", [])
        }
        
        # 处理特殊响应类型
        if processed["type"] == "structured":
            processed["structured_data"] = n8n_response.get("structured_data", {})
        elif processed["type"] == "media":
            processed["media_urls"] = n8n_response.get("media_urls", [])
        
        return processed
    
    async def _handle_session_config(self, user_id: str, config_data: dict):
        """配置会话的n8n webhook"""
        session_id = config_data.get("session_id")
        webhook_url = config_data.get("webhook_url")
        
        if session_id and webhook_url:
            self.n8n_webhooks[session_id] = webhook_url
            self.user_sessions[user_id] = session_id
            
            await self._send_to_user(user_id, {
                "type": "session_configured",
                "session_id": session_id,
                "status": "ready"
            })
    
    async def _send_to_user(self, user_id: str, message: dict):
        """发送消息给指定用户"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                log.error(f"Failed to send message to user {user_id}: {e}")
                await self.disconnect(user_id)
    
    async def _send_error(self, user_id: str, error_message: str):
        """发送错误消息"""
        await self._send_to_user(user_id, {
            "type": "error",
            "message": error_message,
            "timestamp": asyncio.get_event_loop().time()
        })

# 全局处理器实例
chat_handler = HSAIChatWebSocketHandler()
```

### 2. WebSocket路由集成

```python
# backend/open_webui/routers/hsai_websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from open_webui.utils.auth import get_verified_user_from_token
from open_webui.socket.hsai_chat_handler import chat_handler
import json
import logging

log = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/hsai/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """HSAI WebSocket端点 - 对话协同核心"""
    
    # 验证用户身份（通过query参数传递token）
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return
    
    try:
        # 验证token（需要适配现有认证系统）
        user = await get_verified_user_from_token(token)
        if not user or user.id != user_id:
            await websocket.close(code=4003, reason="Invalid authentication")
            return
    except Exception as e:
        await websocket.close(code=4003, reason="Authentication failed")
        return
    
    # 建立连接
    await chat_handler.connect(websocket, user_id)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 处理消息（包含n8n转发逻辑）
            await chat_handler.handle_message(user_id, message_data)
            
    except WebSocketDisconnect:
        log.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        log.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await chat_handler.disconnect(user_id)
```

### 3. 修正后的对话管理接口

```python
# backend/open_webui/routers/hsai_chat.py (修正版本)
@router.post("/sessions", response_model=HSAIChatSessionResponse)
async def create_chat_session(
    form_data: HSAIChatSessionForm,
    user=Depends(get_verified_user)
):
    """创建对话会话 - 支持n8n集成"""
    try:
        # 创建会话记录
        session = HSAIChatSessions.insert_new_session(user.id, form_data)
        
        # 如果指定了n8n工作流，配置webhook
        if form_data.n8n_workflow_id:
            webhook_url = f"{N8N_BASE_URL}/webhook/{form_data.n8n_workflow_id}"
            
            # 通知WebSocket处理器配置webhook
            from open_webui.socket.hsai_chat_handler import chat_handler
            if user.id in chat_handler.active_connections:
                await chat_handler._handle_session_config(user.id, {
                    "session_id": session.id,
                    "webhook_url": webhook_url
                })
        
        return HSAIChatSessionResponse(**session.model_dump())
        
    except Exception as e:
        log.exception(f"Error creating chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

# 新增：n8n webhook回调处理
@router.post("/webhook/n8n/{session_id}")
async def handle_n8n_webhook(
    session_id: str,
    response_data: dict,
    user=Depends(get_verified_user)  # 或使用webhook签名验证
):
    """处理n8n webhook回调"""
    try:
        # 验证会话存在且属于用户
        session = HSAIChatSessions.get_session_by_id(session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 保存n8n响应到数据库
        message_data = HSAIMessageForm(
            session_id=session_id,
            role="assistant",
            content=response_data.get("content", ""),
            metadata={
                "source": "n8n",
                "workflow_id": response_data.get("workflow_id"),
                "execution_id": response_data.get("execution_id"),
                "processing_time": response_data.get("processing_time")
            }
        )
        
        message = HSAIMessages.insert_new_message(message_data)
        
        # 通过WebSocket发送给客户端
        from open_webui.socket.hsai_chat_handler import chat_handler
        await chat_handler._send_to_user(session.user_id, {
            "type": "n8n_response",
            "session_id": session_id,
            "message": message.model_dump(),
            "timestamp": message.created_at
        })
        
        return {"status": "success", "message_id": message.id}
        
    except Exception as e:
        log.exception(f"Error handling n8n webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

### 4. 客户端协同示例

```javascript
// 前端WebSocket客户端示例
class HSAIChatClient {
    constructor(userId, token) {
        this.userId = userId;
        this.token = token;
        this.ws = null;
        this.messageHandlers = new Map();
    }
    
    connect() {
        const wsUrl = `ws://localhost:8080/hsai/ws/${this.userId}?token=${this.token}`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
        };
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
        };
    }
    
    // 发送对话消息（自动转发到n8n）
    sendChatMessage(sessionId, content, messageId = null) {
        const message = {
            type: "chat_message",
            session_id: sessionId,
            content: content,
            message_id: messageId || this.generateMessageId(),
            timestamp: Date.now(),
            metadata: {}
        };
        
        this.ws.send(JSON.stringify(message));
    }
    
    // 配置会话的n8n webhook
    configureSession(sessionId, workflowId) {
        const config = {
            type: "session_config",
            session_id: sessionId,
            webhook_url: `${N8N_BASE_URL}/webhook/${workflowId}`
        };
        
        this.ws.send(JSON.stringify(config));
    }
    
    handleMessage(message) {
        switch (message.type) {
            case "chat_response":
                // 处理n8n返回的结构化响应
                this.onChatResponse(message);
                break;
            case "message_status":
                // 处理消息状态更新
                this.onMessageStatus(message);
                break;
            case "error":
                // 处理错误
                this.onError(message);
                break;
        }
    }
    
    onChatResponse(message) {
        const { session_id, response } = message;
        
        // 显示AI响应
        this.displayMessage(session_id, {
            role: "assistant",
            content: response.content,
            type: response.type,
            metadata: response.metadata,
            attachments: response.attachments
        });
        
        // 处理建议操作
        if (response.actions && response.actions.length > 0) {
            this.displaySuggestedActions(response.actions);
        }
    }
}
```

## 🔄 协同流程图

```
客户端                    OpenWebUI服务端              n8n工作流
  │                           │                         │
  │ 1. WebSocket连接           │                         │
  ├─────────────────────────→ │                         │
  │                           │                         │
  │ 2. 发送对话消息             │                         │
  ├─────────────────────────→ │                         │
  │                           │ 3. 转发到webhook         │
  │                           ├─────────────────────────→│
  │                           │                         │
  │                           │ 4. n8n处理并返回         │
  │                           │←─────────────────────────┤
  │                           │                         │
  │ 5. 结构化处理后返回         │                         │
  │←─────────────────────────┤                         │
  │                           │                         │
```

## ✅ 修正后的优势

### 1. 完全符合协同模式
- ✅ WebSocket直连通信
- ✅ 消息自动转发到n8n
- ✅ 结构化响应处理
- ✅ 实时状态同步

### 2. 灵活的工作流集成
- ✅ 支持多个n8n工作流
- ✅ 动态webhook配置
- ✅ 会话级别的工作流绑定
- ✅ 错误处理和重试机制

### 3. 完整的消息生命周期
- ✅ 消息状态跟踪
- ✅ 处理进度反馈
- ✅ 结果持久化存储
- ✅ 历史记录查询

## 📋 部署配置

### 环境变量
```bash
# n8n集成配置
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=your_n8n_api_key
N8N_WEBHOOK_SECRET=your_webhook_secret

# WebSocket配置
WEBSOCKET_TIMEOUT=30
MAX_WEBSOCKET_CONNECTIONS=1000
```

### n8n工作流配置
```json
{
  "webhook_config": {
    "method": "POST",
    "path": "/webhook/chat-workflow",
    "response_mode": "responseNode"
  },
  "expected_payload": {
    "user_id": "string",
    "session_id": "string", 
    "message": "string",
    "timestamp": "number",
    "metadata": "object"
  }
}
```

## 🎯 总结

修正后的设计完全符合您要求的协同模式：

1. ✅ **WebSocket直连** - 客户端与服务端直接WebSocket通信
2. ✅ **消息转发** - 服务端自动转发对话消息到n8n webhook
3. ✅ **结构化处理** - n8n响应经过标准化处理后返回
4. ✅ **实时通信** - 全程通过WebSocket保持实时连接
5. ✅ **灵活配置** - 支持动态配置不同会话的n8n工作流

**建议立即按此方案修正现有实现，确保OpenWebUI与n8n的协同符合设计要求。**