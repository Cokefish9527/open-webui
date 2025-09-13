# OpenWebUI + n8n 通讯方案技术实现

## 1. 阶段一：HTTP协议优化方案

### 1.1 OpenWebUI后端扩展架构

```python
# backend/open_webui/routers/workflow.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import httpx
import json
import asyncio
from datetime import datetime

router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

class WorkflowRequest(BaseModel):
    message: str
    session_id: str
    user_id: str
    workflow_type: Optional[str] = "main"
    context: Optional[Dict[str, Any]] = {}

class WorkflowResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    error: Optional[str] = None

class WorkflowService:
    def __init__(self):
        self.n8n_webhooks = {
            "main": "https://webhook-n8n.hsai.cc/webhook/hROwwd7UTCzQeFxj",
            "company_info": "https://webhook-n8n.hsai.cc/webhook/cXeGsB422GErqFvi",
            "viral_learning": "https://webhook-n8n.hsai.cc/webhook/VuLYqKoSILQRHJ1r",
            "video_scraping": "https://webhook-n8n.hsai.cc/webhook/p8IAfFdOW4xfKICE"
        }
        self.llm_client = self._init_llm_client()
        
    def _init_llm_client(self):
        # 复用OpenWebUI现有的LLM配置
        from open_webui.models.models import Models
        return Models.get_model_by_id("gpt-4")
    
    async def process_workflow_request(self, request: WorkflowRequest) -> WorkflowResponse:
        """处理工作流请求的主入口"""
        try:
            # 1. 调用n8n工作流
            raw_response = await self._call_n8n_workflow(request)
            
            # 2. 结构化处理响应
            structured_response = await self._structure_response(raw_response, request)
            
            # 3. 验证和修复响应格式
            validated_response = await self._validate_and_fix_response(structured_response)
            
            return WorkflowResponse(
                success=True,
                data=validated_response,
                metadata={
                    "workflow_type": request.workflow_type,
                    "execution_time": datetime.now().isoformat(),
                    "session_id": request.session_id
                }
            )
            
        except Exception as e:
            return WorkflowResponse(
                success=False,
                data={},
                metadata={},
                error=str(e)
            )
    
    async def _call_n8n_workflow(self, request: WorkflowRequest) -> Dict[str, Any]:
        """调用n8n工作流"""
        webhook_url = self.n8n_webhooks.get(request.workflow_type, self.n8n_webhooks["main"])
        
        payload = {
            "message": request.message,
            "sessionId": request.session_id,
            "userId": request.user_id,
            "timestamp": datetime.now().isoformat(),
            "context": request.context
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Session-ID": request.session_id,
                    "X-User-ID": request.user_id
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"n8n workflow failed: {response.text}"
                )
            
            return response.json()
    
    async def _structure_response(self, raw_response: Dict[str, Any], request: WorkflowRequest) -> Dict[str, Any]:
        """使用LLM结构化处理n8n响应"""
        
        # 定义期望的响应结构
        expected_structure = {
            "type": "text|image|video|file|action",
            "content": "响应内容",
            "actions": ["可执行操作列表"],
            "metadata": {
                "workflow_step": "当前步骤",
                "next_steps": ["后续步骤"],
                "confidence": "置信度0-1",
                "source": "数据来源"
            },
            "ui_elements": {
                "show_typing": "是否显示打字效果",
                "enable_actions": "是否启用操作按钮",
                "display_mode": "显示模式"
            }
        }
        
        # 构建LLM提示
        prompt = f"""
        请将以下n8n工作流的原始响应数据转换为标准化的结构格式。

        原始响应数据:
        {json.dumps(raw_response, ensure_ascii=False, indent=2)}

        用户请求信息:
        - 消息: {request.message}
        - 工作流类型: {request.workflow_type}
        - 会话ID: {request.session_id}

        期望的输出格式:
        {json.dumps(expected_structure, ensure_ascii=False, indent=2)}

        要求:
        1. 确保所有必需字段都存在
        2. 内容要准确反映原始响应的意图
        3. 如果原始数据不完整，请合理推断和补充
        4. 输出必须是有效的JSON格式
        5. 保持原始响应的核心信息不变

        请直接输出JSON格式的结构化数据，不要包含其他说明文字:
        """
        
        try:
            # 调用LLM进行结构化处理
            llm_response = await self._call_llm(prompt)
            
            # 解析LLM返回的JSON
            structured_data = json.loads(llm_response)
            
            return structured_data
            
        except json.JSONDecodeError as e:
            # 如果LLM返回的不是有效JSON，使用备用方案
            return self._fallback_structure_response(raw_response)
        except Exception as e:
            # 其他错误，返回原始响应的安全包装
            return self._safe_wrap_response(raw_response)
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM进行文本处理"""
        # 这里集成OpenWebUI现有的LLM调用机制
        from open_webui.models.chats import Chats
        from open_webui.models.users import Users
        
        # 创建临时对话用于结构化处理
        chat_data = {
            "title": "Workflow Response Processing",
            "models": ["gpt-4"],
            "system": "You are a data structure processor. Always return valid JSON.",
            "messages": [{"role": "user", "content": prompt}],
            "history": {"messages": []},
            "tags": ["workflow", "internal"],
            "timestamp": datetime.now().timestamp()
        }
        
        # 调用现有的聊天处理逻辑
        response = await self._process_internal_chat(chat_data)
        return response.get("content", "{}")
    
    def _fallback_structure_response(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """备用结构化方案"""
        # 尝试从原始响应中提取关键信息
        content = ""
        if isinstance(raw_response, dict):
            # 常见的响应字段名
            content_fields = ["content", "message", "text", "response", "result", "output"]
            for field in content_fields:
                if field in raw_response:
                    content = str(raw_response[field])
                    break
            
            if not content:
                # 如果没找到内容字段，将整个响应转为字符串
                content = json.dumps(raw_response, ensure_ascii=False)
        else:
            content = str(raw_response)
        
        return {
            "type": "text",
            "content": content,
            "actions": [],
            "metadata": {
                "workflow_step": "unknown",
                "next_steps": [],
                "confidence": 0.5,
                "source": "fallback_processing"
            },
            "ui_elements": {
                "show_typing": False,
                "enable_actions": False,
                "display_mode": "simple"
            }
        }
    
    def _safe_wrap_response(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """安全包装原始响应"""
        return {
            "type": "text",
            "content": "处理中，请稍候...",
            "actions": [],
            "metadata": {
                "workflow_step": "error_recovery",
                "next_steps": ["retry"],
                "confidence": 0.0,
                "source": "error_handler",
                "raw_response": raw_response
            },
            "ui_elements": {
                "show_typing": False,
                "enable_actions": True,
                "display_mode": "error"
            }
        }
    
    async def _validate_and_fix_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """验证和修复响应格式"""
        # 必需字段检查
        required_fields = {
            "type": "text",
            "content": "无内容",
            "actions": [],
            "metadata": {},
            "ui_elements": {}
        }
        
        # 填充缺失字段
        for field, default_value in required_fields.items():
            if field not in response:
                response[field] = default_value
        
        # 验证字段类型
        if not isinstance(response["actions"], list):
            response["actions"] = []
        
        if not isinstance(response["metadata"], dict):
            response["metadata"] = {}
        
        if not isinstance(response["ui_elements"], dict):
            response["ui_elements"] = {}
        
        # 确保metadata有基本字段
        metadata_defaults = {
            "workflow_step": "completed",
            "next_steps": [],
            "confidence": 0.8,
            "source": "n8n_workflow"
        }
        
        for field, default_value in metadata_defaults.items():
            if field not in response["metadata"]:
                response["metadata"][field] = default_value
        
        # 确保ui_elements有基本字段
        ui_defaults = {
            "show_typing": False,
            "enable_actions": len(response["actions"]) > 0,
            "display_mode": "normal"
        }
        
        for field, default_value in ui_defaults.items():
            if field not in response["ui_elements"]:
                response["ui_elements"][field] = default_value
        
        return response

# 工作流服务实例
workflow_service = WorkflowService()

@router.post("/execute", response_model=WorkflowResponse)
async def execute_workflow(request: WorkflowRequest):
    """执行工作流"""
    return await workflow_service.process_workflow_request(request)

@router.get("/status/{session_id}")
async def get_workflow_status(session_id: str):
    """获取工作流状态"""
    # 这里可以添加状态查询逻辑
    return {"session_id": session_id, "status": "completed"}

@router.post("/batch")
async def batch_execute_workflows(requests: List[WorkflowRequest]):
    """批量执行工作流"""
    results = []
    for request in requests:
        result = await workflow_service.process_workflow_request(request)
        results.append(result)
    return {"results": results}
```

### 1.2 前端集成方案

```javascript
// src/lib/apis/workflow.js
class WorkflowAPI {
  constructor() {
    this.baseURL = '/api/v1/workflow';
  }

  async executeWorkflow(message, sessionId, workflowType = 'main', context = {}) {
    try {
      const response = await fetch(`${this.baseURL}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          message,
          session_id: sessionId,
          user_id: this.getCurrentUserId(),
          workflow_type: workflowType,
          context
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || 'Workflow execution failed');
      }

      return result.data;
    } catch (error) {
      console.error('Workflow execution error:', error);
      throw error;
    }
  }

  getCurrentUserId() {
    // 获取当前用户ID的逻辑
    return localStorage.getItem('user_id') || 'anonymous';
  }

  async getWorkflowStatus(sessionId) {
    const response = await fetch(`${this.baseURL}/status/${sessionId}`);
    return await response.json();
  }

  async batchExecuteWorkflows(requests) {
    const response = await fetch(`${this.baseURL}/batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(requests)
    });
    
    return await response.json();
  }
}

// 导出单例
export const workflowAPI = new WorkflowAPI();
```

```javascript
// src/lib/components/chat/WorkflowChatHandler.js
import { workflowAPI } from '../../apis/workflow.js';

class WorkflowChatHandler {
  constructor() {
    this.activeRequests = new Map();
    this.retryAttempts = new Map();
    this.maxRetries = 3;
  }

  async handleMessage(message, sessionId, chatContainer) {
    const requestId = this.generateRequestId();
    
    try {
      // 显示处理中状态
      this.showProcessingIndicator(chatContainer, requestId);
      
      // 执行工作流
      const response = await workflowAPI.executeWorkflow(
        message, 
        sessionId, 
        this.detectWorkflowType(message)
      );
      
      // 处理响应
      await this.processWorkflowResponse(response, chatContainer, requestId);
      
    } catch (error) {
      await this.handleError(error, message, sessionId, chatContainer, requestId);
    } finally {
      this.hideProcessingIndicator(chatContainer, requestId);
      this.activeRequests.delete(requestId);
    }
  }

  detectWorkflowType(message) {
    // 根据消息内容检测工作流类型
    const keywords = {
      'company_info': ['公司信息', '企业资料', '战略地图', '关键词'],
      'viral_learning': ['爆款', '学习', '视频分析', '热门'],
      'video_scraping': ['视频爬取', '数据收集', '批量分析']
    };

    for (const [type, keywordList] of Object.entries(keywords)) {
      if (keywordList.some(keyword => message.includes(keyword))) {
        return type;
      }
    }

    return 'main'; // 默认主工作流
  }

  async processWorkflowResponse(response, chatContainer, requestId) {
    const { type, content, actions, metadata, ui_elements } = response;

    // 根据响应类型处理显示
    switch (type) {
      case 'text':
        await this.displayTextResponse(content, chatContainer, ui_elements);
        break;
      case 'image':
        await this.displayImageResponse(content, chatContainer);
        break;
      case 'video':
        await this.displayVideoResponse(content, chatContainer);
        break;
      case 'action':
        await this.displayActionResponse(content, actions, chatContainer);
        break;
      default:
        await this.displayTextResponse(content, chatContainer, ui_elements);
    }

    // 处理可执行操作
    if (actions && actions.length > 0) {
      this.addActionButtons(actions, chatContainer, metadata);
    }
  }

  async displayTextResponse(content, chatContainer, uiElements = {}) {
    const messageElement = this.createMessageElement('assistant', content);
    
    if (uiElements.show_typing) {
      // 显示打字效果
      await this.typewriterEffect(messageElement, content);
    } else {
      messageElement.textContent = content;
    }
    
    chatContainer.appendChild(messageElement);
    this.scrollToBottom(chatContainer);
  }

  async typewriterEffect(element, text, speed = 50) {
    element.textContent = '';
    for (let i = 0; i < text.length; i++) {
      element.textContent += text.charAt(i);
      await new Promise(resolve => setTimeout(resolve, speed));
    }
  }

  showProcessingIndicator(chatContainer, requestId) {
    const indicator = document.createElement('div');
    indicator.className = 'processing-indicator';
    indicator.id = `processing-${requestId}`;
    indicator.innerHTML = `
      <div class="flex items-center space-x-2 p-3 bg-gray-100 rounded-lg">
        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
        <span class="text-sm text-gray-600">AI正在处理您的请求...</span>
      </div>
    `;
    
    chatContainer.appendChild(indicator);
    this.scrollToBottom(chatContainer);
  }

  hideProcessingIndicator(chatContainer, requestId) {
    const indicator = document.getElementById(`processing-${requestId}`);
    if (indicator) {
      indicator.remove();
    }
  }

  addActionButtons(actions, chatContainer, metadata) {
    const actionsContainer = document.createElement('div');
    actionsContainer.className = 'action-buttons flex flex-wrap gap-2 mt-2';
    
    actions.forEach(action => {
      const button = document.createElement('button');
      button.className = 'px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm';
      button.textContent = action;
      button.onclick = () => this.handleActionClick(action, metadata);
      actionsContainer.appendChild(button);
    });
    
    chatContainer.appendChild(actionsContainer);
  }

  async handleActionClick(action, metadata) {
    // 处理操作按钮点击
    const sessionId = metadata.session_id || this.getCurrentSessionId();
    
    try {
      const response = await workflowAPI.executeWorkflow(
        `执行操作: ${action}`,
        sessionId,
        'main',
        { action, metadata }
      );
      
      // 处理操作响应
      await this.processWorkflowResponse(response, this.getChatContainer(), this.generateRequestId());
      
    } catch (error) {
      this.showError(`操作执行失败: ${error.message}`);
    }
  }

  async handleError(error, originalMessage, sessionId, chatContainer, requestId) {
    const retryCount = this.retryAttempts.get(requestId) || 0;
    
    if (retryCount < this.maxRetries) {
      // 重试机制
      this.retryAttempts.set(requestId, retryCount + 1);
      
      console.log(`Retrying request ${requestId}, attempt ${retryCount + 1}`);
      
      // 延迟重试
      await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
      
      try {
        const response = await workflowAPI.executeWorkflow(originalMessage, sessionId);
        await this.processWorkflowResponse(response, chatContainer, requestId);
        return;
      } catch (retryError) {
        console.error(`Retry ${retryCount + 1} failed:`, retryError);
      }
    }

    // 显示错误信息
    this.showError(`请求处理失败: ${error.message}`, chatContainer);
    
    // 添加重试按钮
    this.addRetryButton(originalMessage, sessionId, chatContainer);
  }

  showError(message, chatContainer) {
    const errorElement = this.createMessageElement('error', message);
    errorElement.className += ' bg-red-100 border-red-300 text-red-700';
    chatContainer.appendChild(errorElement);
    this.scrollToBottom(chatContainer);
  }

  addRetryButton(originalMessage, sessionId, chatContainer) {
    const retryContainer = document.createElement('div');
    retryContainer.className = 'retry-container mt-2';
    
    const retryButton = document.createElement('button');
    retryButton.className = 'px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600';
    retryButton.textContent = '重试';
    retryButton.onclick = () => {
      retryContainer.remove();
      this.handleMessage(originalMessage, sessionId, chatContainer);
    };
    
    retryContainer.appendChild(retryButton);
    chatContainer.appendChild(retryContainer);
  }

  createMessageElement(role, content) {
    const element = document.createElement('div');
    element.className = `message ${role} p-3 mb-2 rounded-lg`;
    
    if (role === 'assistant') {
      element.className += ' bg-gray-100';
    } else if (role === 'user') {
      element.className += ' bg-blue-100 ml-auto max-w-xs';
    }
    
    element.textContent = content;
    return element;
  }

  generateRequestId() {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  getCurrentSessionId() {
    return localStorage.getItem('current_session_id') || 'default_session';
  }

  getChatContainer() {
    return document.querySelector('.chat-container') || document.body;
  }

  scrollToBottom(container) {
    container.scrollTop = container.scrollHeight;
  }
}

// 导出单例
export const workflowChatHandler = new WorkflowChatHandler();
```

## 2. 阶段二：WebSocket双向通信方案

### 2.1 WebSocket服务端实现

```python
# backend/open_webui/socket/workflow_socket.py
import socketio
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# 创建Socket.IO服务器
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True
)

class WorkflowSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.workflow_sessions: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
    async def register_connection(self, sid: str, session_data: Dict[str, Any]):
        """注册新连接"""
        self.active_connections[sid] = {
            "session_id": session_data.get("session_id"),
            "user_id": session_data.get("user_id"),
            "connected_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        
        self.logger.info(f"New connection registered: {sid}")
        
        # 发送连接确认
        await sio.emit('connection_confirmed', {
            "status": "connected",
            "session_id": session_data.get("session_id"),
            "timestamp": datetime.now().isoformat()
        }, room=sid)
    
    async def handle_message(self, sid: str, message_data: Dict[str, Any]):
        """处理消息请求"""
        session_id = message_data.get("session_id")
        message = message_data.get("message")
        
        try:
            # 更新最后活动时间
            if sid in self.active_connections:
                self.active_connections[sid]["last_activity"] = datetime.now().isoformat()
            
            # 发送处理开始通知
            await sio.emit('workflow_status', {
                "status": "processing",
                "message": "正在处理您的请求...",
                "progress": 0,
                "timestamp": datetime.now().isoformat()
            }, room=sid)
            
            # 启动工作流处理任务
            task = asyncio.create_task(
                self._process_workflow_async(sid, message_data)
            )
            
            # 启动进度更新任务
            progress_task = asyncio.create_task(
                self._update_progress(sid, session_id)
            )
            
            # 等待工作流完成
            result = await task
            progress_task.cancel()
            
            # 发送最终结果
            await sio.emit('workflow_complete', {
                "status": "completed",
                "data": result,
                "timestamp": datetime.now().isoformat()
            }, room=sid)
            
        except Exception as e:
            self.logger.error(f"Error processing message for {sid}: {str(e)}")
            await sio.emit('workflow_error', {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }, room=sid)
    
    async def _process_workflow_async(self, sid: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """异步处理工作流"""
        from .workflow import workflow_service
        from .workflow import WorkflowRequest
        
        # 创建工作流请求
        request = WorkflowRequest(
            message=message_data.get("message"),
            session_id=message_data.get("session_id"),
            user_id=message_data.get("user_id"),
            workflow_type=message_data.get("workflow_type", "main"),
            context=message_data.get("context", {})
        )
        
        # 处理请求
        response = await workflow_service.process_workflow_request(request)
        
        if not response.success:
            raise Exception(response.error)
        
        return response.data
    
    async def _update_progress(self, sid: str, session_id: str):
        """定期更新进度"""
        progress = 10
        messages = [
            "正在分析您的请求...",
            "正在调用AI工作流...",
            "正在处理数据...",
            "正在生成响应...",
            "即将完成..."
        ]
        
        try:
            for i, message in enumerate(messages):
                await asyncio.sleep(2)  # 每2秒更新一次
                progress = min(90, 10 + (i + 1) * 15)
                
                await sio.emit('workflow_status', {
                    "status": "processing",
                    "message": message,
                    "progress": progress,
                    "timestamp": datetime.now().isoformat()
                }, room=sid)
                
        except asyncio.CancelledError:
            # 任务被取消，正常结束
            pass
    
    async def disconnect_user(self, sid: str):
        """处理用户断开连接"""
        if sid in self.active_connections:
            connection_info = self.active_connections[sid]
            self.logger.info(f"User disconnected: {sid}, session: {connection_info.get('session_id')}")
            del self.active_connections[sid]
    
    async def broadcast_system_message(self, message: str):
        """广播系统消息"""
        await sio.emit('system_message', {
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        return {
            "total_connections": len(self.active_connections),
            "active_sessions": len(set(
                conn.get("session_id") for conn in self.active_connections.values()
                if conn.get("session_id")
            )),
            "connections": list(self.active_connections.values())
        }

# 创建管理器实例
workflow_socket_manager = WorkflowSocketManager()

# Socket.IO 事件处理
@sio.event
async def connect(sid, environ):
    """客户端连接事件"""
    print(f"Client {sid} connected")

@sio.event
async def disconnect(sid):
    """客户端断开连接事件"""
    await workflow_socket_manager.disconnect_user(sid)
    print(f"Client {sid} disconnected")

@sio.event
async def register_session(sid, data):
    """注册会话事件"""
    await workflow_socket_manager.register_connection(sid, data)

@sio.event
async def send_message(sid, data):
    """发送消息事件"""
    await workflow_socket_manager.handle_message(sid, data)

@sio.event
async def get_status(sid, data):
    """获取状态事件"""
    session_id = data.get("session_id")
    # 返回当前状态
    await sio.emit('status_response', {
        "session_id": session_id,
        "status": "ready",
        "timestamp": datetime.now().isoformat()
    }, room=sid)

# 集成到FastAPI应用
def setup_socketio(app):
    """设置Socket.IO"""
    import socketio
    
    # 创建ASGI应用
    socket_app = socketio.ASGIApp(sio, app)
    return socket_app
```

### 2.2 前端WebSocket客户端

```javascript
// src/lib/socket/WorkflowSocketClient.js
import { io } from 'socket.io-client';

class WorkflowSocketClient {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.eventHandlers = new Map();
    this.messageQueue = [];
    this.currentSessionId = null;
  }

  async connect(sessionId, userId) {
    try {
      this.socket = io('/', {
        transports: ['websocket', 'polling'],
        upgrade: true,
        rememberUpgrade: true,
        timeout: 20000,
        forceNew: true
      });

      this.currentSessionId = sessionId;
      this.setupEventHandlers();
      
      // 等待连接建立
      await this.waitForConnection();
      
      // 注册会话
      await this.registerSession(sessionId, userId);
      
      console.log('WebSocket connected successfully');
      return true;
      
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      return false;
    }
  }

  setupEventHandlers() {
    this.socket.on('connect', () => {
      console.log('Socket connected:', this.socket.id);
      this.isConnected = true;
      this.reconnectAttempts = 0;
      
      // 处理排队的消息
      this.processMessageQueue();
    });

    this.socket.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason);
      this.isConnected = false;
      
      if (reason === 'io server disconnect') {
        // 服务器主动断开，需要重新连接
        this.reconnect();
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('Connection error:', error);
      this.handleConnectionError();
    });

    this.socket.on('connection_confirmed', (data) => {
      console.log('Connection confirmed:', data);
      this.emit('connection_ready', data);
    });

    this.socket.on('workflow_status', (data) => {
      this.emit('workflow_status', data);
    });

    this.socket.on('workflow_complete', (data) => {
      this.emit('workflow_complete', data);
    });

    this.socket.on('workflow_error', (data) => {
      this.emit('workflow_error', data);
    });

    this.socket.on('system_message', (data) => {
      this.emit('system_message', data);
    });
  }

  async waitForConnection(timeout = 10000) {
    return new Promise((resolve, reject) => {
      if (this.isConnected) {
        resolve();
        return;
      }

      const timer = setTimeout(() => {
        reject(new Error('Connection timeout'));
      }, timeout);

      this.socket.once('connect', () => {
        clearTimeout(timer);
        resolve();
      });

      this.socket.once('connect_error', (error) => {
        clearTimeout(timer);
        reject(error);
      });
    });
  }

  async registerSession(sessionId, userId) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Session registration timeout'));
      }, 5000);

      this.socket.once('connection_confirmed', (data) => {
        clearTimeout(timeout);
        resolve(data);
      });

      this.socket.emit('register_session', {
        session_id: sessionId,
        user_id: userId,
        timestamp: new Date().toISOString()
      });
    });
  }

  async sendMessage(message, workflowType = 'main', context = {}) {
    const messageData = {
      message,
      session_id: this.currentSessionId,
      user_id: this.getCurrentUserId(),
      workflow_type: workflowType,
      context,
      timestamp: new Date().toISOString()
    };

    if (this.isConnected) {
      this.socket.emit('send_message', messageData);
    } else {
      // 连接断开时，将消息加入队列
      this.messageQueue.push(messageData);
      console.log('Message queued, connection not ready');
    }
  }

  processMessageQueue() {
    while (this.messageQueue.length > 0 && this.isConnected) {
      const message = this.messageQueue.shift();
      this.socket.emit('send_message', message);
    }
  }

  handleConnectionError() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      
      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      
      setTimeout(() => {
        this.reconnect();
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
      this.emit('connection_failed', {
        message: 'Unable to establish connection after multiple attempts'
      });
    }
  }

  reconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
    
    this.connect(this.currentSessionId, this.getCurrentUserId());
  }

  on(event, handler) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event).push(handler);
  }

  off(event, handler) {
    if (this.eventHandlers.has(event)) {
      const handlers = this.eventHandlers.get(event);
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.eventHandlers.has(event)) {
      this.eventHandlers.get(event).forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }

  getCurrentUserId() {
    return localStorage.getItem('user_id') || 'anonymous';
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.isConnected = false;
    this.eventHandlers.clear();
    this.messageQueue = [];
  }

  getConnectionStatus() {
    return {
      connected: this.isConnected,
      socketId: this.socket?.id,
      sessionId: this.currentSessionId,
      queuedMessages: this.messageQueue.length,
      reconnectAttempts: this.reconnectAttempts
    };
  }
}

// 导出单例
export const workflowSocketClient = new WorkflowSocketClient();
```

### 2.3 前端UI组件集成

```javascript
// src/lib/components/chat/EnhancedChatInterface.js
import { workflowSocketClient } from '../../socket/WorkflowSocketClient.js';

class EnhancedChatInterface {
  constructor(containerElement) {
    this.container = containerElement;
    this.isSocketMode = false;
    this.currentSessionId = this.generateSessionId();
    this.setupUI();
    this.setupSocketHandlers();
  }

  setupUI() {
    // 添加连接状态指示器
    this.createConnectionIndicator();
    
    // 添加模式切换按钮
    this.createModeToggle();
    
    // 设置消息输入处理
    this.setupMessageInput();
  }

  createConnectionIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'connection-indicator';
    indicator.className = 'connection-indicator flex items-center space-x-2 p-2 bg-gray-100 rounded-lg mb-4';
    indicator.innerHTML = `
      <div class="status-dot w-3 h-3 rounded-full bg-gray-400"></div>
      <span class="status-text text-sm text-gray-600">未连接</span>
      <button class="connect-btn px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600">
        连接
      </button>
    `;
    
    this.container.prepend(indicator);
    
    // 绑定连接按钮事件
    indicator.querySelector('.connect-btn').onclick = () => {
      this.toggleConnection();
    };
  }

  createModeToggle() {
    const toggle = document.createElement('div');
    toggle.className = 'mode-toggle flex items-center space-x-2 mb-4';
    toggle.innerHTML = `
      <span class="text-sm text-gray-600">通信模式:</span>
      <label class="flex items-center space-x-2">
        <input type="radio" name="comm-mode" value="http" checked>
        <span class="text-sm">HTTP</span>
      </label>
      <label class="flex items-center space-x-2">
        <input type="radio" name="comm-mode" value="websocket">
        <span class="text-sm">WebSocket</span>
      </label>
    `;
    
    this.container.appendChild(toggle);
    
    // 绑定模式切换事件
    toggle.querySelectorAll('input[name="comm-mode"]').forEach(radio => {
      radio.onchange = (e) => {
        this.switchMode(e.target.value);
      };
    });
  }

  setupMessageInput() {
    const inputContainer = this.container.querySelector('.message-input-container');
    if (inputContainer) {
      const input = inputContainer.querySelector('input, textarea');
      if (input) {
        input.addEventListener('keypress', (e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage(input.value);
            input.value = '';
          }
        });
      }
    }
  }

  setupSocketHandlers() {
    workflowSocketClient.on('connection_ready', (data) => {
      this.updateConnectionStatus('connected', '已连接');
      this.showSystemMessage('WebSocket连接已建立');
    });

    workflowSocketClient.on('workflow_status', (data) => {
      this.updateProcessingStatus(data);
    });

    workflowSocketClient.on('workflow_complete', (data) => {
      this.displayWorkflowResponse(data.data);
      this.hideProcessingStatus();
    });

    workflowSocketClient.on('workflow_error', (data) => {
      this.showError(data.message);
      this.hideProcessingStatus();
    });

    workflowSocketClient.on('connection_failed', (data) => {
      this.updateConnectionStatus('error', '连接失败');
      this.showError(data.message);
    });
  }

  async toggleConnection() {
    if (workflowSocketClient.isConnected) {
      workflowSocketClient.disconnect();
      this.updateConnectionStatus('disconnected', '已断开');
    } else {
      this.updateConnectionStatus('connecting', '连接中...');
      const success = await workflowSocketClient.connect(
        this.currentSessionId,
        this.getCurrentUserId()
      );
      
      if (!success) {
        this.updateConnectionStatus('error', '连接失败');
      }
    }
  }

  switchMode(mode) {
    this.isSocketMode = (mode === 'websocket');
    
    if (this.isSocketMode && !workflowSocketClient.isConnected) {
      this.showMessage('WebSocket模式需要先建立连接', 'warning');
    }
    
    console.log(`Switched to ${mode} mode`);
  }

  async sendMessage(message) {
    if (!message.trim()) return;
    
    // 显示用户消息
    this.displayMessage('user', message);
    
    try {
      if (this.isSocketMode && workflowSocketClient.isConnected) {
        // WebSocket模式
        await workflowSocketClient.sendMessage(message);
        this.showProcessingStatus('正在处理您的请求...');
      } else {
        // HTTP模式 (fallback)
        await this.sendMessageHTTP(message);
      }
    } catch (error) {
      this.showError(`发送消息失败: ${error.message}`);
    }
  }

  async sendMessageHTTP(message) {
    // 使用原有的HTTP方式
    const { workflowAPI } = await import('../../apis/workflow.js');
    
    this.showProcessingStatus('正在处理您的请求...');
    
    try {
      const response = await workflowAPI.executeWorkflow(
        message,
        this.currentSessionId
      );
      
      this.displayWorkflowResponse(response);
    } catch (error) {
      throw error;
    } finally {
      this.hideProcessingStatus();
    }
  }

  updateConnectionStatus(status, text) {
    const indicator = document.getElementById('connection-indicator');
    const dot = indicator.querySelector('.status-dot');
    const statusText = indicator.querySelector('.status-text');
    const connectBtn = indicator.querySelector('.connect-btn');
    
    // 更新状态点颜色
    dot.className = 'status-dot w-3 h-3 rounded-full';
    switch (status) {
      case 'connected':
        dot.classList.add('bg-green-400');
        connectBtn.textContent = '断开';
        break;
      case 'connecting':
        dot.classList.add('bg-yellow-400');
        connectBtn.textContent = '连接中...';
        connectBtn.disabled = true;
        break;
      case 'error':
        dot.classList.add('bg-red-400');
        connectBtn.textContent = '重连';
        connectBtn.disabled = false;
        break;
      default:
        dot.classList.add('bg-gray-400');
        connectBtn.textContent = '连接';
        connectBtn.disabled = false;
    }
    
    statusText.textContent = text;
  }

  showProcessingStatus(message, progress = 0) {
    let statusElement = document.getElementById('processing-status');
    
    if (!statusElement) {
      statusElement = document.createElement('div');
      statusElement.id = 'processing-status';
      statusElement.className = 'processing-status p-3 bg-blue-50 border border-blue-200 rounded-lg mb-4';
      this.container.appendChild(statusElement);
    }
    
    statusElement.innerHTML = `
      <div class="flex items-center space-x-3">
        <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
        <div class="flex-1">
          <div class="text-sm text-blue-700">${message}</div>
          ${progress > 0 ? `
            <div class="w-full bg-blue-200 rounded-full h-2 mt-2">
              <div class="bg-blue-500 h-2 rounded-full transition-all duration-300" style="width: ${progress}%"></div>
            </div>
          ` : ''}
        </div>
      </div>
    `;
    
    this.scrollToBottom();
  }

  updateProcessingStatus(data) {
    this.showProcessingStatus(data.message, data.progress);
  }

  hideProcessingStatus() {
    const statusElement = document.getElementById('processing-status');
    if (statusElement) {
      statusElement.remove();
    }
  }

  displayMessage(role, content) {
    const messageElement = document.createElement('div');
    messageElement.className = `message ${role} p-3 mb-3 rounded-lg max-w-4xl`;
    
    if (role === 'user') {
      messageElement.classList.add('bg-blue-100', 'ml-auto');
    } else {
      messageElement.classList.add('bg-gray-100');
    }
    
    messageElement.textContent = content;
    this.container.appendChild(messageElement);
    this.scrollToBottom();
  }

  displayWorkflowResponse(response) {
    const { type, content, actions, ui_elements } = response;
    
    // 显示主要内容
    if (ui_elements?.show_typing) {
      this.typewriterEffect(content);
    } else {
      this.displayMessage('assistant', content);
    }
    
    // 显示操作按钮
    if (actions && actions.length > 0) {
      this.displayActionButtons(actions);
    }
  }

  async typewriterEffect(text, speed = 50) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message assistant p-3 mb-3 rounded-lg max-w-4xl bg-gray-100';
    this.container.appendChild(messageElement);
    
    for (let i = 0; i <= text.length; i++) {
      messageElement.textContent = text.substring(0, i);
      this.scrollToBottom();
      await new Promise(resolve => setTimeout(resolve, speed));
    }
  }

  displayActionButtons(actions) {
    const actionsContainer = document.createElement('div');
    actionsContainer.className = 'action-buttons flex flex-wrap gap-2 mb-4';
    
    actions.forEach(action => {
      const button = document.createElement('button');
      button.className = 'px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors';
      button.textContent = action;
      button.onclick = () => this.handleActionClick(action);
      actionsContainer.appendChild(button);
    });
    
    this.container.appendChild(actionsContainer);
    this.scrollToBottom();
  }

  async handleActionClick(action) {
    try {
      await this.sendMessage(`执行操作: ${action}`);
    } catch (error) {
      this.showError(`操作执行失败: ${error.message}`);
    }
  }

  showMessage(message, type = 'info') {
    const messageElement = document.createElement('div');
    messageElement.className = `system-message p-3 mb-3 rounded-lg`;
    
    switch (type) {
      case 'error':
        messageElement.classList.add('bg-red-100', 'border', 'border-red-300', 'text-red-700');
        break;
      case 'warning':
        messageElement.classList.add('bg-yellow-100', 'border', 'border-yellow-300', 'text-yellow-700');
        break;
      case 'success':
        messageElement.classList.add('bg-green-100', 'border', 'border-green-300', 'text-green-700');
        break;
      default:
        messageElement.classList.add('bg-blue-100', 'border', 'border-blue-300', 'text-blue-700');
    }
    
    messageElement.textContent = message;
    this.container.appendChild(messageElement);
    this.scrollToBottom();
    
    // 3秒后自动移除系统消息
    setTimeout(() => {
      if (messageElement.parentNode) {
        messageElement.remove();
      }
    }, 3000);
  }

  showError(message) {
    this.showMessage(message, 'error');
  }

  showSystemMessage(message) {
    this.showMessage(message, 'info');
  }

  scrollToBottom() {
    this.container.scrollTop = this.container.scrollHeight;
  }

  generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  getCurrentUserId() {
    return localStorage.getItem('user_id') || 'anonymous';
  }
}

// 导出类
export { EnhancedChatInterface };
```

这个通讯方案提供了完整的阶段一和阶段二实现，包括：

1. **阶段一HTTP优化**：结构化处理、错误恢复、重试机制
2. **阶段二WebSocket升级**：双向通信、实时状态、进度反馈
3. **渐进式迁移**：支持两种模式并存，平滑切换
4. **完整的错误处理**：连接管理、重连机制、降级方案