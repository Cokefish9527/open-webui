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
from open_webui.config import BUSINESS_NAME
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
    task_id: Optional[str] = None  # 关联的任务ID
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
        log.info(f"[WebSocket连接] 用户 {user_id} 已连接到HSAI聊天处理器")
        
        # 发送连接成功消息
        status_message = {
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
        }
        
        log.info(f"[WebSocket连接] 发送连接成功消息给用户 {user_id}: {status_message}")
        await self._send_to_user(user_id, status_message)
    
    async def disconnect(self, user_id: str):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]
            del self.user_sessions[user_id]
            if session_id in self.session_workflows:
                del self.session_workflows[session_id]
        log.info(f"[WebSocket断开] 用户 {user_id} 已从HSAI聊天处理器断开连接")
    
    async def handle_message(self, user_id: str, message_data: Dict[str, Any]):
        """处理客户端消息 - 核心n8n集成逻辑"""
        try:
            log.info(f"[消息处理] 开始处理用户 {user_id} 的消息: {message_data}")
            
            # 解析消息
            message = ChatMessage(**message_data)
            log.info(f"[消息处理] 解析用户 {user_id} 的消息成功，消息类型: {message.type}")
            
            if message.type == MessageType.CHAT:
                log.info(f"[消息处理] 识别为聊天消息，调用聊天消息处理器")
                await self._handle_chat_message(user_id, message)
            elif message.type == MessageType.WORKFLOW_TRIGGER:
                log.info(f"[消息处理] 识别为工作流触发消息，调用工作流触发处理器")
                await self._handle_workflow_trigger(user_id, message)
            else:
                error_msg = f"不支持的消息类型: {message.type}"
                log.warning(f"[消息处理] {error_msg}")
                await self._send_error(user_id, error_msg)
                
        except Exception as e:
            error_msg = f"消息处理失败: {str(e)}"
            log.error(f"[消息处理] {error_msg}", exc_info=True)
            await self._send_error(user_id, error_msg)
    
    async def _handle_chat_message(self, user_id: str, message: ChatMessage):
        """处理聊天消息 - 基于入口类型的工作流路由"""
        log.info(f"[聊天消息处理] 开始处理用户 {user_id} 的聊天消息: {message.content}")
        
        # 1. 根据入口类型选择工作流
        workflow_type = self._select_workflow_by_entry(message)
        log.info(f"[工作流选择] 为用户 {user_id} 选择的工作流: {workflow_type.value}")
        
        # 2. 获取或创建会话
        session_id = message.session_id or self._get_or_create_session(user_id)
        self.session_workflows[session_id] = workflow_type
        log.info(f"[会话管理] 会话 {session_id} 已分配给用户 {user_id}，工作流类型: {workflow_type.value}")
        
        # 3. 如果消息指定了任务ID，检查用户是否有权限访问该任务
        task_id = message.task_id
        if task_id:
            log.info(f"[任务权限检查] 检查用户 {user_id} 对任务 {task_id} 的访问权限")
            if not self._verify_task_access(user_id, task_id, session_id):
                error_msg = f"您没有权限访问任务 {task_id}"
                log.warning(f"[任务权限检查] {error_msg}")
                await self._send_error(user_id, error_msg)
                return
        
        # 4. 调用n8n工作流（带监控）
        execution_id = str(uuid.uuid4())
        execution = n8n_monitor.start_execution(execution_id, workflow_type, user_id, session_id)
        log.info(f"[工作流调用] 启动工作流执行 {execution_id}，用户: {user_id}，工作流: {workflow_type.value}")
        
        try:
            # 按照规范文档格式构造请求参数
            payload = {
                "message": message.content,           # 用户输入的对话文字
                "session_id": session_id,             # 唯一会话标识
                "user_id": user_id,                   # 当前登录用户的ID
                "business_name": str(BUSINESS_NAME),       # 当前登录用户的公司名称（从配置文件获取）
                "task_id": task_id,                   # 传递任务ID
                "metadata": message.metadata,
                "timestamp": execution.start_time.timestamp(),  # 转换为时间戳
                "execution_id": execution_id
            }
            log.info(f"[工作流调用] 准备调用n8n工作流，负载数据: {payload}")
            
            workflow_response = await self._call_n8n_workflow_with_retry(
                workflow_type, 
                payload,
                execution_id
            )
            
            log.info(f"[工作流响应] 收到用户 {user_id} 的工作流响应: {workflow_response}")
            
            # 5. 使用专门的响应处理器
            log.info(f"[响应处理] 开始处理工作流响应，工作流类型: {workflow_type.value}")
            processed_response = await N8NResponseProcessor.process_response(
                workflow_response, workflow_type, execution.start_time.timestamp(), execution_id
            )
            log.info(f"[响应处理] 工作流响应处理完成: {processed_response}")
            
            # 6. 格式化并发送给客户端
            log.info(f"[客户端响应] 开始格式化客户端响应")
            client_response = N8NResponseProcessor.format_for_client(processed_response)
            client_response.update({
                "session_id": session_id,
                "user_id": user_id,
                "execution_id": execution_id,
                "task_id": task_id  # 返回任务ID
            })
            log.info(f"[客户端响应] 客户端响应格式化完成: {client_response}")
            
            log.info(f"[客户端响应] 发送响应给用户 {user_id}: {client_response}")
            await self._send_to_user(user_id, client_response)
            
            # 记录成功执行
            response_size = len(json.dumps(workflow_response, ensure_ascii=False))
            n8n_monitor.record_execution(workflow_type.value, True, response_size)
            log.info(f"[执行记录] 工作流执行记录完成，响应大小: {response_size} 字节")
            
        except Exception as e:
            error_msg = f"工作流处理失败: {str(e)}"
            log.error(f"[工作流处理] {error_msg}", exc_info=True)
            n8n_monitor.record_execution(workflow_type.value, False, 0, str(e))
            await self._send_error(user_id, error_msg)
    
    async def _handle_workflow_trigger(self, user_id: str, message: ChatMessage):
        """处理工作流触发消息"""
        log.info(f"[工作流触发] 处理用户 {user_id} 的工作流触发消息，工作流类型: {message.workflow_type}")
        
        if not message.workflow_type:
            error_msg = "工作流触发消息缺少工作流类型"
            log.warning(f"[工作流触发] {error_msg}")
            await self._send_error(user_id, error_msg)
            return
        
        session_id = message.session_id or self._get_or_create_session(user_id)
        log.info(f"[工作流触发] 使用会话 {session_id} 处理工作流触发")
        
        try:
            # 按照规范文档格式构造请求参数
            execution_start_time = time.time()
            payload = {
                "message": message.content,           # 用户输入的对话文字
                "session_id": session_id,             # 唯一会话标识
                "user_id": user_id,                   # 当前登录用户的ID
                "business_name": str(BUSINESS_NAME),       # 当前登录用户的公司名称（从配置文件获取）
                "metadata": message.metadata,
                "timestamp": execution_start_time
            }
            log.info(f"[工作流触发] 准备调用n8n工作流，负载数据: {payload}")
            
            workflow_response = await self._call_n8n_workflow(
                message.workflow_type,
                payload
            )
            
            log.info(f"[工作流响应] 收到用户 {user_id} 的工作流响应: {workflow_response}")
            
            log.info(f"[响应处理] 开始处理工作流响应，工作流类型: {message.workflow_type}")
            processed_response = await N8NResponseProcessor.process_response(
                workflow_response, message.workflow_type, execution_start_time
            )
            log.info(f"[响应处理] 工作流响应处理完成: {processed_response}")
            
            log.info(f"[客户端响应] 开始格式化客户端响应")
            client_response = N8NResponseProcessor.format_for_client(processed_response)
            client_response.update({
                "session_id": session_id,
                "user_id": user_id
            })
            log.info(f"[客户端响应] 客户端响应格式化完成: {client_response}")
            
            log.info(f"[客户端响应] 发送响应给用户 {user_id}: {client_response}")
            await self._send_to_user(user_id, client_response)
            
        except Exception as e:
            error_msg = f"工作流触发失败: {str(e)}"
            log.error(f"[工作流触发] {error_msg}", exc_info=True)
            await self._send_error(user_id, error_msg)
    
    def _select_workflow_by_entry(self, message: ChatMessage) -> WorkflowType:
        """根据入口类型选择工作流"""
        # 1. 优先使用明确指定的工作流类型
        if message.workflow_type:
            log.info(f"[工作流选择] 使用明确指定的工作流: {message.workflow_type.value}")
            return message.workflow_type
        
        # 2. 根据入口类型选择工作流
        if message.entry_type:
            workflow_type = get_workflow_by_entry_type(message.entry_type)
            log.info(f"[工作流选择] 基于入口类型 {message.entry_type} 选择工作流: {workflow_type.value}")
            return workflow_type
        
        # 3. 基于关键词的智能选择（作为后备方案）
        workflow_type = self._select_workflow_by_keywords(message.content)
        log.info(f"[工作流选择] 基于关键词智能选择工作流: {workflow_type.value}")
        return workflow_type
    
    def _select_workflow_by_keywords(self, content: str) -> WorkflowType:
        """基于关键词智能选择工作流（后备方案）"""
        content_lower = content.lower()
        log.info(f"[关键词选择] 基于内容进行关键词匹配: {content_lower}")
        
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
            log.debug(f"[关键词选择] 工作流 {workflow_type.value} 匹配分数: {score}")
        
        # 选择得分最高的工作流
        if workflow_scores:
            best_workflow = max(workflow_scores, key=workflow_scores.get)
            if workflow_scores[best_workflow] > 0:
                log.info(f"[关键词选择] 选择匹配分数最高的工作流: {best_workflow.value}")
                return best_workflow
        
        # 默认使用主工作流
        log.info("[关键词选择] 未匹配到关键词，使用默认主工作流")
        return WorkflowType.MAIN
    
    async def _call_n8n_workflow_with_retry(
        self, 
        workflow_type: WorkflowType, 
        payload: Dict[str, Any],
        execution_id: str
    ) -> Dict[str, Any]:
        """调用n8n工作流webhook（带重试机制）"""
        log.info(f"[工作流调用] 开始调用n8n工作流 {workflow_type.value}，执行ID: {execution_id}")
        last_error = None
        
        while True:
            try:
                result = await self._call_n8n_workflow(workflow_type, payload)
                log.info(f"[工作流调用] n8n工作流 {workflow_type.value} 调用成功")
                return result
            except Exception as e:
                last_error = e
                error_message = str(e)
                log.warning(f"[工作流调用] n8n工作流 {workflow_type.value} 调用失败: {error_message}")
                
                # 检查是否应该重试
                if n8n_monitor.should_retry(execution_id, error_message):
                    log.info(f"[工作流调用] 工作流 {workflow_type.value} 将进行重试")
                    await n8n_monitor.retry_execution(execution_id)
                    continue
                else:
                    log.error(f"[工作流调用] 工作流 {workflow_type.value} 重试次数已达上限，终止执行")
                    raise last_error
    
    async def _call_n8n_workflow(self, workflow_type: WorkflowType, payload: Dict[str, Any]) -> Dict[str, Any]:
        """调用n8n工作流webhook"""
        config = self.workflow_configs[workflow_type]
        log.info(f"[n8n调用] 准备调用n8n工作流 {workflow_type.value}，URL: {config.webhook_url}")
        
        async with aiohttp.ClientSession() as session:
            try:
                log.info(f"[n8n调用] 正在向n8n发送POST请求")
                
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
                        log.info(f"[n8n调用] n8n工作流 {workflow_type.value} 执行成功，状态码: {response.status}")
                        return result
                    else:
                        error_text = await response.text()
                        error_msg = f"n8n工作流失败，状态码: {response.status}，错误信息: {error_text}"
                        log.error(f"[n8n调用] {error_msg}")
                        raise Exception(error_msg)
                        
            except asyncio.TimeoutError:
                error_msg = f"n8n工作流 {workflow_type.value} 超时，超时时间: {config.timeout}秒"
                log.error(f"[n8n调用] {error_msg}")
                raise Exception(error_msg)
            except Exception as e:
                log.error(f"[n8n调用] 调用n8n工作流 {workflow_type.value} 时发生错误: {e}", exc_info=True)
                raise
    

    
    def _get_or_create_session(self, user_id: str) -> str:
        """获取或创建用户会话"""
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]
            log.info(f"[会话管理] 获取现有会话 {session_id} 给用户 {user_id}")
            return session_id
        
        session_id = f"session_{user_id}_{int(time.time())}"
        self.user_sessions[user_id] = session_id
        log.info(f"[会话管理] 为用户 {user_id} 创建新会话 {session_id}")
        return session_id
    
    async def _send_to_user(self, user_id: str, message: Dict[str, Any]):
        """发送消息给指定用户"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                log.info(f"[消息发送] 向用户 {user_id} 发送消息: {message}")
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
                log.info(f"[消息发送] 消息发送成功")
            except Exception as e:
                error_msg = f"向用户 {user_id} 发送消息时发生错误: {e}"
                log.error(f"[消息发送] {error_msg}", exc_info=True)
                await self.disconnect(user_id)
        else:
            log.warning(f"[消息发送] 用户 {user_id} 的WebSocket连接不存在，无法发送消息: {message}")
    
    async def _send_error(self, user_id: str, error_message: str):
        """发送错误消息给用户"""
        error_data = {
            "type": MessageType.ERROR,
            "content": error_message,
            "timestamp": time.time()
        }
        log.error(f"[错误发送] 向用户 {user_id} 发送错误消息: {error_data}")
        await self._send_to_user(user_id, error_data)
    
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
        log.info(f"[消息广播] 向会话 {session_id} 广播消息给 {len(users)} 个用户: {users}")
        for user_id in users:
            await self._send_to_user(user_id, message)
    
    def _verify_task_access(self, user_id: str, task_id: str, session_id: str) -> bool:
        """
        验证用户是否有权限访问指定任务
        """
        try:
            log.info(f"[任务权限] 验证用户 {user_id} 对任务 {task_id} 的访问权限")
            # 从数据库获取任务信息
            from open_webui.models.hsai_tasks import HSAITasks
            
            task = HSAITasks.get_task_by_id(task_id)
            if not task:
                log.warning(f"[任务权限] 任务 {task_id} 不存在")
                return False
            
            # 检查用户是否是任务所有者
            if task.user_id == user_id:
                log.info(f"[任务权限] 用户 {user_id} 是任务 {task_id} 的所有者")
                return True
            
            # 检查用户是否是协作者
            if task.collaborators:
                for collaborator in task.collaborators:
                    if collaborator.get("user_id") == user_id:
                        log.info(f"[任务权限] 用户 {user_id} 是任务 {task_id} 的协作者")
                        return True
            
            # 检查会话是否被共享
            if task.shared_sessions and session_id in task.shared_sessions:
                log.info(f"[任务权限] 会话 {session_id} 已被共享到任务 {task_id}")
                return True
            
            log.warning(f"[任务权限] 用户 {user_id} 无权访问任务 {task_id}")
            return False
        except Exception as e:
            log.error(f"[任务权限] 验证任务访问权限时发生错误: {e}", exc_info=True)
            return False
    
    def add_task_collaborator(self, task_id: str, user_id: str, role: str = "collaborator") -> bool:
        """
        添加任务协作者
        """
        try:
            log.info(f"[协作者管理] 为任务 {task_id} 添加协作者 {user_id}")
            from open_webui.models.hsai_tasks import HSAITasks, HSAITaskUpdateForm
            
            task = HSAITasks.get_task_by_id(task_id)
            if not task:
                log.warning(f"[协作者管理] 任务 {task_id} 不存在")
                return False
            
            # 创建协作者信息
            collaborator = {
                "user_id": user_id,
                "role": role,
                "joined_at": int(time.time())
            }
            
            # 更新协作者列表
            collaborators = task.collaborators or []
            collaborators.append(collaborator)
            
            # 更新任务
            update_form = HSAITaskUpdateForm(collaborators=collaborators)
            updated_task = HSAITasks.update_task_by_id(task_id, update_form)
            
            if updated_task:
                log.info(f"[协作者管理] 成功为任务 {task_id} 添加协作者 {user_id}")
                return True
            else:
                log.warning(f"[协作者管理] 为任务 {task_id} 添加协作者 {user_id} 失败")
                return False
        except Exception as e:
            log.error(f"[协作者管理] 添加任务协作者时发生错误: {e}", exc_info=True)
            return False
    
    def share_task_session(self, task_id: str, session_id: str) -> bool:
        """
        共享任务到会话
        """
        try:
            log.info(f"[会话共享] 将任务 {task_id} 共享到会话 {session_id}")
            from open_webui.models.hsai_tasks import HSAITasks, HSAITaskUpdateForm
            
            task = HSAITasks.get_task_by_id(task_id)
            if not task:
                log.warning(f"[会话共享] 任务 {task_id} 不存在")
                return False
            
            # 更新共享会话列表
            shared_sessions = task.shared_sessions or []
            if session_id not in shared_sessions:
                shared_sessions.append(session_id)
            
            # 更新任务
            update_form = HSAITaskUpdateForm(shared_sessions=shared_sessions)
            updated_task = HSAITasks.update_task_by_id(task_id, update_form)
            
            if updated_task:
                log.info(f"[会话共享] 成功将任务 {task_id} 共享到会话 {session_id}")
                return True
            else:
                log.warning(f"[会话共享] 将任务 {task_id} 共享到会话 {session_id} 失败")
                return False
        except Exception as e:
            log.error(f"[会话共享] 共享任务会话时发生错误: {e}", exc_info=True)
            return False

# 全局chat_handler实例
chat_handler = HSAIChatHandler()