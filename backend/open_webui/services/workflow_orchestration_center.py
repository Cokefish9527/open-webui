"""
工作流编排中心
负责协调和管理所有n8n工作流的执行
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from open_webui.config.n8n_workflows import (
    N8NWorkflowType, 
    get_workflow_by_entry_type, 
    get_workflow_config
)
from open_webui.utils.n8n_workflow_manager import workflow_manager, WorkflowConfig, WorkflowType
from open_webui.utils.n8n_client import N8NClient, ExecutionRequest
from open_webui.utils.n8n_response_processor import N8NResponseProcessor

log = logging.getLogger(__name__)

class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class WorkflowExecution:
    """工作流执行记录"""
    execution_id: str
    workflow_id: str
    user_id: str
    session_id: str
    status: ExecutionStatus
    start_time: float
    end_time: Optional[float] = None
    progress: int = 0
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None

class RouterManager:
    """路由管理器 - 智能路由请求到合适的n8n工作流"""
    
    def route_request(self, user_input: str, context: Dict[str, Any]) -> N8NWorkflowType:
        """根据用户输入和上下文路由到合适的工作流"""
        entry_type = context.get("entry_type", "chat")
        
        # 首先检查消息中是否包含"战略"关键词，如果包含则路由到信息收集工作流
        if "战略" in user_input:
            return N8NWorkflowType.COMPANY_INFO
        
        # 根据entry_type路由
        if entry_type in ["company", "company_info"]:
            return N8NWorkflowType.COMPANY_INFO
        elif entry_type in ["video_crawl", "video_analysis"]:
            return N8NWorkflowType.VIDEO_CRAWL
        elif entry_type in ["viral_learning", "viral_video"]:
            return N8NWorkflowType.VIRAL_LEARNING
        elif entry_type == "chat":
            return N8NWorkflowType.MAIN
        else:
            # 默认使用主工作流
            return N8NWorkflowType.MAIN

class StateManager:
    """状态管理器 - 统一管理所有工作流的执行状态"""
    
    def __init__(self):
        self.executions: Dict[str, WorkflowExecution] = {}
        self.user_executions: Dict[str, List[str]] = {}  # user_id -> execution_ids
    
    def create_execution(self, workflow_id: str, user_id: str, session_id: str, context: Dict[str, Any]) -> str:
        """创建新的执行记录"""
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            user_id=user_id,
            session_id=session_id,
            status=ExecutionStatus.PENDING,
            start_time=time.time(),
            context=context
        )
        self.executions[execution_id] = execution
        
        # 记录用户的所有执行
        if user_id not in self.user_executions:
            self.user_executions[user_id] = []
        self.user_executions[user_id].append(execution_id)
        
        log.info(f"创建执行记录: {execution_id} for workflow {workflow_id}")
        return execution_id
    
    def update_execution_status(self, execution_id: str, status: ExecutionStatus, 
                              progress: Optional[int] = None, 
                              current_step: Optional[str] = None,
                              error_message: Optional[str] = None):
        """更新执行状态"""
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            execution.status = status
            if progress is not None:
                execution.progress = progress
            if current_step is not None:
                execution.current_step = current_step
            if error_message is not None:
                execution.error_message = error_message
            if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                execution.end_time = time.time()
            log.info(f"更新执行状态: {execution_id} -> {status}")
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """获取执行记录"""
        return self.executions.get(execution_id)
    
    def get_user_executions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有执行记录"""
        execution_ids = self.user_executions.get(user_id, [])
        return [asdict(self.executions[exec_id]) for exec_id in execution_ids if exec_id in self.executions]
    
    def cleanup_old_executions(self, max_age_hours: int = 24):
        """清理旧的执行记录"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        expired_executions = []
        
        for exec_id, execution in self.executions.items():
            if execution.end_time and (current_time - execution.end_time) > max_age_seconds:
                expired_executions.append(exec_id)
        
        for exec_id in expired_executions:
            if exec_id in self.executions:
                execution = self.executions[exec_id]
                # 从用户执行列表中移除
                if execution.user_id in self.user_executions:
                    if exec_id in self.user_executions[execution.user_id]:
                        self.user_executions[execution.user_id].remove(exec_id)
                # 删除执行记录
                del self.executions[exec_id]
        
        log.info(f"清理了 {len(expired_executions)} 个旧执行记录")

class CommunicationManager:
    """通信管理器 - 管理与n8n工作流的通信"""
    
    def __init__(self):
        self.n8n_client = N8NClient()
        self.response_processor = N8NResponseProcessor()
    
    async def execute_workflow(self, workflow_type: N8NWorkflowType, 
                             user_input: str, 
                             user_id: str, 
                             session_id: str,
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定的工作流"""
        try:
            # 获取工作流配置
            workflow_config = get_workflow_config(workflow_type)
            
            # 将N8NWorkflowType转换为WorkflowType
            workflow_type_mapping = {
                N8NWorkflowType.MAIN: WorkflowType.MAIN,
                N8NWorkflowType.COMPANY_INFO: WorkflowType.COMPANY_INFO,
                N8NWorkflowType.VIRAL_LEARNING: WorkflowType.VIRAL_LEARNING,
                N8NWorkflowType.VIDEO_CRAWL: WorkflowType.VIDEO_CRAWL
            }
            
            # 创建临时的WorkflowConfig对象
            workflow = WorkflowConfig(
                id=workflow_type.value,
                name=workflow_type.value,
                type=workflow_type_mapping[workflow_type],
                description="临时工作流配置",
                webhook_url=workflow_config["webhook_url"],
                webhook_method="POST",
                timeout=workflow_config.get("timeout", 30),
                retry_count=3,
                keywords=[],
                priority=1,
                enabled=True
            )
            
            # 构建请求数据，包含socket_id用于后续消息发送
            request = ExecutionRequest(
                workflow_id=workflow_type.value,
                session_id=session_id,
                user_id=user_id,
                message=user_input,
                additional_data=context
            )
            
            # 发送请求到n8n
            log.info(f"执行工作流: {workflow_type.value} at {workflow.webhook_url}")
            # 使用正确的客户端方法
            execution_result = await self.n8n_client.execute_workflow(workflow, request)
            
            # 处理响应
            processed_response = await self.response_processor.process_response(
                execution_result.response_data or {},
                workflow_type.value, 
                time.time(),
                execution_result.execution_id
            )
            
            # 转换为字典格式
            return {
                "success": processed_response.status == "success",
                "message": processed_response.message,
                "data": processed_response.data,
                "execution_id": processed_response.execution_id
            }
            
        except Exception as e:
            log.error(f"执行工作流失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

class WorkflowOrchestrationCenter:
    """工作流编排中心 - 核心协调器"""
    
    def __init__(self):
        self.router_manager = RouterManager()
        self.state_manager = StateManager()
        self.communication_manager = CommunicationManager()
        self._initialized = False
    
    async def initialize(self):
        """初始化工作流编排中心"""
        if not self._initialized:
            log.info("初始化工作流编排中心...")
            # 初始化工作流管理器
            await workflow_manager.load_workflows()
            # 初始化N8N客户端
            await self.communication_manager.n8n_client.initialize()
            self._initialized = True
            log.info("工作流编排中心初始化完成")
    
    async def process_request(self, user_input: str, user_id: str, session_id: str, context: Dict[str, Any]) -> str:
        """处理用户请求"""
        execution_id = ""  # 初始化execution_id
        try:
            # 1. 路由选择
            workflow_type = self.router_manager.route_request(user_input, context)
            log.info(f"路由选择结果: {workflow_type.value}")
            
            # 2. 创建执行记录
            execution_id = self.state_manager.create_execution(
                workflow_id=workflow_type.value,
                user_id=user_id,
                session_id=session_id,
                context=context
            )
            
            # 3. 更新状态为运行中
            self.state_manager.update_execution_status(
                execution_id=execution_id,
                status=ExecutionStatus.RUNNING,
                progress=10,
                current_step="开始执行工作流"
            )

            # 4. 通知Socket.IO事件 - 工作流开始
            await self._notify_socket_event(
                event_type="workflow_started",
                data={
                    "execution_id": execution_id,
                    "workflow_type": workflow_type.value,
                    "workflow_name": workflow_type.value,
                    "user_id": user_id,
                    "session_id": session_id
                },
                status="FINISHED",
                context=context
            )
            
            # 4. 记录工作流开始日志（取消发送Socket.IO事件）
            log.info(f"工作流开始执行: execution_id={execution_id}, workflow_type={workflow_type.value}, user_id={user_id}")
            
            # 5. 执行工作流
            result = await self.communication_manager.execute_workflow(
                workflow_type=workflow_type,
                user_input=user_input,
                user_id=user_id,
                session_id=session_id,
                context=context
            )
            
            # 6. 更新执行结果
            if result.get("success", False):
                # 成功完成
                self.state_manager.update_execution_status(
                    execution_id=execution_id,
                    status=ExecutionStatus.COMPLETED,
                    progress=100,
                    current_step="工作流执行完成"
                )
                # 更新结果
                execution = self.state_manager.get_execution(execution_id)
                if execution:
                    execution.result = result
            else:
                # 执行失败
                self.state_manager.update_execution_status(
                    execution_id=execution_id,
                    status=ExecutionStatus.FAILED,
                    progress=100,
                    current_step="工作流执行失败",
                    error_message=result.get("error", "未知错误")
                )
                # 更新结果
                execution = self.state_manager.get_execution(execution_id)
                if execution:
                    execution.result = result
            
            # 7. 记录工作流完成或失败日志（取消发送Socket.IO事件）
            if result.get("success", False):
                log.info(f"工作流执行完成: execution_id={execution_id}, workflow_type={workflow_type.value}, user_id={user_id}")
            else:
                log.error(f"工作流执行失败: execution_id={execution_id}, workflow_type={workflow_type.value}, user_id={user_id}, error={result.get('error', '未知错误')}")
            
            # 8. 只在失败时发送Socket.IO事件
            if not result.get("success", False):
                await self._notify_socket_event(
                    event_type="workflow_failed",
                    data={
                        "execution_id": execution_id,
                        "workflow_type": workflow_type.value,
                        "error": result.get("error", "未知错误"),
                        "user_id": user_id,
                        "session_id": session_id
                    },
                    status="FAILED",
                    context=context
                )
            
            return execution_id
            
        except Exception as e:
            log.error(f"处理请求时发生错误: {e}", exc_info=True)
            # 如果execution_id已创建，更新为失败状态
            if execution_id:
                self.state_manager.update_execution_status(
                    execution_id=execution_id,
                    status=ExecutionStatus.FAILED,
                    progress=100,
                    current_step="处理请求时发生错误",
                    error_message=str(e)
                )
                # 通知Socket.IO事件 - 工作流失败
                await self._notify_socket_event(
                    event_type="workflow_failed",
                    data={
                        "execution_id": execution_id,
                        "error": str(e),
                        "user_id": user_id,
                        "session_id": session_id
                    },
                    status="FAILED",
                    context=context
                )
            return ""
    
    async def _notify_socket_event(self, event_type: str, data: Dict[str, Any], status: str = "FINISHED",
                                 context: Optional[Dict[str, Any]] = None):
        """通过Socket.IO发送事件通知"""
        try:
            # 获取Socket.IO实例
            from open_webui.socket.main import sio
            
            # 检查sio是否已初始化
            if sio is None:
                log.warning("Socket.IO未初始化，无法发送事件")
                return
                
            socket_id = context.get("socket_id") if context else None
            user_id = data.get("user_id")
            
            # 构建事件数据
            event_data = {
                "timestamp": int(time.time() * 1000),  # 使用13位时间戳
                **data
            }
            
            # 根据事件类型确定发送的核心事件和子类型
            core_event = "hsai_response"  # 默认使用成功响应事件
            if event_type in ["workflow_started", "workflow_progress", "workflow_completed", "status"]:
                # 工作流相关事件和状态事件合并到hsai_response
                core_event = "hsai_response"
                event_data["type"] = "hsai_response"
                event_data["subtype"] = event_type  # 添加子类型用于区分原始事件
            elif event_type in ["workflow_failed", "error"]:
                # 工作流失败和错误事件合并到hsai_error
                core_event = "hsai_error"
                event_data["type"] = "hsai_error"
                event_data["subtype"] = event_type  # 添加子类型用于区分原始事件
            else:
                # 其他事件保持原有的命名方式
                core_event = f"hsai_{event_type}"
                event_data["type"] = core_event
            
            # 如果有socket_id，直接发送到特定连接
            if socket_id:
                await sio.emit(core_event, event_data, to=socket_id)
                log.info(f"通过Socket.IO发送事件到sid {socket_id}: {event_type} (合并到 {core_event})")
            # 否则发送给用户的所有连接
            elif user_id:
                from open_webui.socket.main import USER_POOL
                user_sids = USER_POOL.get(user_id, [])
                # 确保user_sids是可迭代的
                if user_sids:
                    if not isinstance(user_sids, list):
                        user_sids = list(user_sids) if hasattr(user_sids, '__iter__') else []
                    for sid in user_sids:
                        await sio.emit(core_event, event_data, to=sid)
                log.info(f"通过Socket.IO发送事件到用户 {user_id}: {event_type} (合并到 {core_event})")
                
        except Exception as e:
            log.error(f"发送Socket.IO事件失败: {e}", exc_info=True)
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """获取工作流统计信息"""
        total_executions = len(self.state_manager.executions)
        completed_executions = len([
            e for e in self.state_manager.executions.values() 
            if e.status == ExecutionStatus.COMPLETED
        ])
        failed_executions = len([
            e for e in self.state_manager.executions.values() 
            if e.status == ExecutionStatus.FAILED
        ])
        
        success_rate = 0.0
        if total_executions > 0:
            success_rate = completed_executions / total_executions
        
        # 计算平均执行时间
        completed_times = [
            (e.end_time - e.start_time) 
            for e in self.state_manager.executions.values() 
            if e.status == ExecutionStatus.COMPLETED and e.end_time
        ]
        average_duration = 0.0
        if completed_times:
            average_duration = sum(completed_times) / len(completed_times)
        
        # 工作流分布统计
        workflow_distribution = {}
        for execution in self.state_manager.executions.values():
            workflow_type = execution.workflow_id
            workflow_distribution[workflow_type] = workflow_distribution.get(workflow_type, 0) + 1
        
        return {
            "total_executions": total_executions,
            "active_executions": len([
                e for e in self.state_manager.executions.values() 
                if e.status == ExecutionStatus.RUNNING
            ]),
            "completed_executions": completed_executions,
            "failed_executions": failed_executions,
            "success_rate": success_rate,
            "average_duration": average_duration,
            "workflow_distribution": workflow_distribution
        }
    
    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        execution = self.state_manager.get_execution(execution_id)
        if execution:
            return asdict(execution)
        return None
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        execution = self.state_manager.get_execution(execution_id)
        if execution and execution.status == ExecutionStatus.RUNNING:
            self.state_manager.update_execution_status(
                execution_id=execution_id,
                status=ExecutionStatus.CANCELLED,
                progress=100,
                current_step="用户取消执行"
            )
            log.info(f"已取消执行: {execution_id}")
            return True
        return False

# 全局工作流编排中心实例
workflow_orchestration_center = WorkflowOrchestrationCenter()