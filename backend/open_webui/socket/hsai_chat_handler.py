"""
HSAI Chat Handler - n8n工作流集成的对话消息处理器

实现客户端 ←→ WebSocket ←→ OpenWebUI ←→ n8n webhook 的完整协同流程
"""

import json
import logging
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any
from fastapi import WebSocket
from pydantic import BaseModel, Field
from enum import Enum
from open_webui.config.n8n_workflows import (
    N8NWorkflowType, 
    get_workflow_config, 
    get_all_workflow_configs,
    WORKFLOW_TRIGGER_KEYWORDS,
    get_workflow_by_entry_type,
    is_scheduled_workflow
)
from open_webui.utils.n8n_response_processor import N8NResponseProcessor
from open_webui.utils.n8n_monitor import n8n_monitor
import uuid

log = logging.getLogger(__name__)

# 使用配置文件中的工作流类型
WorkflowType = N8NWorkflowType

class MessageType(str, Enum):
    """消息类型枚举"""
    CHAT = "chat"
    WORKFLOW_TRIGGER = "workflow_trigger"
    WORKFLOW_RESPONSE = "workflow_response"
    ERROR = "error"
    STATUS = "status"

class WorkflowConfig(BaseModel):
    """工作流配置模型"""
    name: str
    webhook_url: str
    description: str
    trigger_keywords: List[str] = []
    timeout: int = 30

class ChatMessage(BaseModel):
    """聊天消息模型"""
    type: MessageType
    content: str
    user_id: str
    session_id: Optional[str] = None
    workflow_type: Optional[WorkflowType] = None
    entry_type: Optional[str] = None  # 对话入口类型
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkflowResponse(BaseModel):
    """工作流响应模型"""
    success: bool
    data: Dict[str, Any]
    workflow_type: WorkflowType
    execution_time: float
    error_message: Optional[str] = None

class HSAIChatHandler:
    """HSAI聊天处理器 - 集成n8n工作流调度"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.session_workflows: Dict[str, WorkflowType] = {}  # session_id -> workflow_type
        
        # 从配置文件加载n8n工作流配置
        self.workflow_configs = {}
        for workflow_type in WorkflowType:
            config_data = get_workflow_config(workflow_type)
            self.workflow_configs[workflow_type] = WorkflowConfig(
                name=config_data["description"].split(" - ")[0],
                webhook_url=config_data["webhook_url"],
                description=config_data["description"],
                trigger_keywords=config_data["keywords"],
                timeout=config_data["timeout"]
            )
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        log.info(f"User {user_id} connected to HSAI chat handler")
        
        # 发送连接成功消息
        await self._send_to_user(user_id, {
            "type": MessageType.STATUS,
            "content": "连接成功",
            "timestamp": time.time(),
            "available_workflows": [
                {
                    "type": wf_type.value,
                    "name": config.name,
                    "description": config.description
                }
                for wf_type, config in self.workflow_configs.items()
            ]
        })
    
    async def disconnect(self, user_id: str):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]
            del self.user_sessions[user_id]
            if session_id in self.session_workflows:
                del self.session_workflows[session_id]
        log.info(f"User {user_id} disconnected from HSAI chat handler")
    
    async def handle_message(self, user_id: str, message_data: Dict[str, Any]):
        """处理客户端消息 - 核心n8n集成逻辑"""
        try:
            # 解析消息
            message = ChatMessage(**message_data)
            log.debug(f"Processing message from user {user_id}: {message.type}")
            
            if message.type == MessageType.CHAT:
                await self._handle_chat_message(user_id, message)
            elif message.type == MessageType.WORKFLOW_TRIGGER:
                await self._handle_workflow_trigger(user_id, message)
            else:
                await self._send_error(user_id, f"Unsupported message type: {message.type}")
                
        except Exception as e:
            log.error(f"Error handling message from user {user_id}: {e}")
            await self._send_error(user_id, f"Message processing failed: {str(e)}")
    
    async def _handle_chat_message(self, user_id: str, message: ChatMessage):
        """处理聊天消息 - 基于入口类型的工作流路由"""
        # 1. 根据入口类型选择工作流
        workflow_type = self._select_workflow_by_entry(message)
        
        # 2. 获取或创建会话
        session_id = message.session_id or self._get_or_create_session(user_id)
        self.session_workflows[session_id] = workflow_type
        
        # 3. 调用n8n工作流（带监控）
        execution_id = str(uuid.uuid4())
        execution = n8n_monitor.start_execution(execution_id, workflow_type, user_id, session_id)
        
        try:
            workflow_response = await self._call_n8n_workflow_with_retry(
                workflow_type, 
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "content": message.content,
                    "metadata": message.metadata,
                    "timestamp": execution.start_time,
                    "execution_id": execution_id
                },
                execution_id
            )
            
            # 4. 使用专门的响应处理器
            processed_response = await N8NResponseProcessor.process_response(
                workflow_response, workflow_type, execution.start_time, execution_id
            )
            
            # 5. 格式化并发送给客户端
            client_response = N8NResponseProcessor.format_for_client(processed_response)
            client_response.update({
                "session_id": session_id,
                "user_id": user_id,
                "execution_id": execution_id
            })
            
            await self._send_to_user(user_id, client_response)
            
            # 记录成功执行
            response_size = len(json.dumps(workflow_response, ensure_ascii=False))
            n8n_monitor.record_execution(workflow_type.value, True, response_size)
            
        except Exception as e:
            log.error(f"Error in workflow processing: {e}")
            n8n_monitor.record_execution(workflow_type.value, False, 0, str(e))
            await self._send_error(user_id, f"工作流处理失败: {str(e)}")
    
    async def _handle_workflow_trigger(self, user_id: str, message: ChatMessage):
        """处理工作流触发消息"""
        if not message.workflow_type:
            await self._send_error(user_id, "Missing workflow_type for workflow trigger")
            return
        
        session_id = message.session_id or self._get_or_create_session(user_id)
        
        try:
            execution_start_time = time.time()
            workflow_response = await self._call_n8n_workflow(
                message.workflow_type,
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "content": message.content,
                    "metadata": message.metadata,
                    "timestamp": execution_start_time
                }
            )
            
            processed_response = await N8NResponseProcessor.process_response(
                workflow_response, message.workflow_type, execution_start_time
            )
            
            client_response = N8NResponseProcessor.format_for_client(processed_response)
            client_response.update({
                "session_id": session_id,
                "user_id": user_id
            })
            
            await self._send_to_user(user_id, client_response)
            
        except Exception as e:
            log.error(f"Error in workflow trigger: {e}")
            await self._send_error(user_id, f"工作流触发失败: {str(e)}")
    
    def _select_workflow_by_entry(self, message: ChatMessage) -> WorkflowType:
        """根据入口类型选择工作流"""
        # 1. 优先使用明确指定的工作流类型
        if message.workflow_type:
            log.debug(f"Using explicitly specified workflow: {message.workflow_type.value}")
            return message.workflow_type
        
        # 2. 根据入口类型选择工作流
        if message.entry_type:
            workflow_type = get_workflow_by_entry_type(message.entry_type)
            log.debug(f"Selected workflow {workflow_type.value} based on entry type: {message.entry_type}")
            return workflow_type
        
        # 3. 基于关键词的智能选择（作为后备方案）
        workflow_type = self._select_workflow_by_keywords(message.content)
        log.debug(f"Selected workflow {workflow_type.value} based on keywords")
        return workflow_type
    
    def _select_workflow_by_keywords(self, content: str) -> WorkflowType:
        """基于关键词智能选择工作流（后备方案）"""
        content_lower = content.lower()
        
        # 计算每个工作流的匹配分数（排除定时调用的工作流）
        workflow_scores = {}
        for workflow_type in WorkflowType:
            if is_scheduled_workflow(workflow_type):
                continue  # 跳过定时调用的工作流
                
            score = 0
            keywords = WORKFLOW_TRIGGER_KEYWORDS[workflow_type]
            for keyword in keywords:
                if keyword in content_lower:
                    score += 1
            workflow_scores[workflow_type] = score
        
        # 选择得分最高的工作流
        if workflow_scores:
            best_workflow = max(workflow_scores, key=workflow_scores.get)
            if workflow_scores[best_workflow] > 0:
                return best_workflow
        
        # 默认使用主工作流
        return WorkflowType.MAIN
    
    async def _call_n8n_workflow_with_retry(
        self, 
        workflow_type: WorkflowType, 
        payload: Dict[str, Any],
        execution_id: str
    ) -> Dict[str, Any]:
        """调用n8n工作流webhook（带重试机制）"""
        last_error = None
        
        while True:
            try:
                return await self._call_n8n_workflow(workflow_type, payload)
            except Exception as e:
                last_error = e
                error_message = str(e)
                
                # 检查是否应该重试
                if n8n_monitor.should_retry(execution_id, error_message):
                    log.warning(f"n8n workflow {workflow_type.value} failed, retrying: {error_message}")
                    await n8n_monitor.retry_execution(execution_id)
                    continue
                else:
                    log.error(f"n8n workflow {workflow_type.value} failed permanently: {error_message}")
                    raise last_error
    
    async def _call_n8n_workflow(self, workflow_type: WorkflowType, payload: Dict[str, Any]) -> Dict[str, Any]:
        """调用n8n工作流webhook"""
        config = self.workflow_configs[workflow_type]
        
        async with aiohttp.ClientSession() as session:
            try:
                log.debug(f"Calling n8n workflow: {workflow_type.value}")
                
                async with session.post(
                    config.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=config.timeout),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "OpenWebUI-HSAI/1.0",
                        "X-Execution-ID": payload.get("execution_id", "")
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        log.debug(f"n8n workflow {workflow_type.value} completed successfully")
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"n8n workflow failed with status {response.status}: {error_text}")
                        
            except asyncio.TimeoutError:
                raise Exception(f"n8n workflow {workflow_type.value} timeout after {config.timeout}s")
            except Exception as e:
                log.error(f"Error calling n8n workflow {workflow_type.value}: {e}")
                raise
    

    
    def _get_or_create_session(self, user_id: str) -> str:
        """获取或创建用户会话"""
        if user_id in self.user_sessions:
            return self.user_sessions[user_id]
        
        session_id = f"session_{user_id}_{int(time.time())}"
        self.user_sessions[user_id] = session_id
        return session_id
    
    async def _send_to_user(self, user_id: str, message: Dict[str, Any]):
        """发送消息给指定用户"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                log.error(f"Error sending message to user {user_id}: {e}")
                await self.disconnect(user_id)
    
    async def _send_error(self, user_id: str, error_message: str):
        """发送错误消息给用户"""
        await self._send_to_user(user_id, {
            "type": MessageType.ERROR,
            "content": error_message,
            "timestamp": time.time()
        })
    
    def get_active_users(self) -> List[str]:
        """获取活跃用户列表"""
        return list(self.active_connections.keys())
    
    def get_session_users(self, session_id: str) -> List[str]:
        """获取指定会话的用户"""
        return [
            user_id for user_id, sess_id in self.user_sessions.items()
            if sess_id == session_id
        ]
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """向会话中的所有用户广播消息"""
        users = self.get_session_users(session_id)
        for user_id in users:
            await self._send_to_user(user_id, message)

# 全局chat_handler实例
chat_handler = HSAIChatHandler()