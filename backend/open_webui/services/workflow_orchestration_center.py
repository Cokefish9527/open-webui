"""
工作流编排中心 (Workflow Orchestration Center - WOC)
根据HSAI技术架构设计文档实现的统一工作流管理和路由系统
"""

import re
import json
import logging
import asyncio
import uuid
import time
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp

from open_webui.utils.n8n_workflow_manager import WorkflowType, WorkflowConfig, workflow_manager
from open_webui.utils.n8n_client import n8n_client, ExecutionRequest, ExecutionResult

log = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """工作流状态枚举"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class RoutingRule:
    """路由规则"""
    pattern: str
    workflow_type: WorkflowType
    priority: int
    conditions: List[str] = None

class RouterManager:
    """路由管理器 - 智能路由请求到合适的n8n工作流"""
    
    def __init__(self):
        self.routing_rules = self._initialize_routing_rules()
        self.workflow_endpoints = {
            WorkflowType.MAIN: "https://webhook-n8n.hsai.cc/webhook/n8n_chat",
            WorkflowType.COMPANY_INFO: "https://webhook-n8n.hsai.cc/webhook/business_information_get",
            WorkflowType.VIRAL_LEARNING: "https://webhook-n8n.hsai.cc/webhook/viral-learning",
            WorkflowType.VIDEO_ANALYSIS: "https://webhook-n8n.hsai.cc/webhook/video_analysis"
        }

    def _initialize_routing_rules(self) -> List[RoutingRule]:
        """初始化路由规则"""
        return [
            # 企业信息收集规则
            RoutingRule(
                pattern=r"(企业|公司|组织).*(信息|资料|分析)",
                workflow_type=WorkflowType.COMPANY_INFO,
                priority=10,
                conditions=["has_file_upload"]
            ),
            RoutingRule(
                pattern=r"(上传|解析|分析).*(文件|文档|资料)",
                workflow_type=WorkflowType.COMPANY_INFO,
                priority=9
            ),

            # 视频相关规则
            RoutingRule(
                pattern=r"(视频|爬取|抓取).*(分析|关键词|内容)",
                workflow_type=WorkflowType.VIDEO_ANALYSIS,
                priority=8
            ),
            RoutingRule(
                pattern=r"(抖音|快手|小红书|B站).*(视频|内容)",
                workflow_type=WorkflowType.VIDEO_ANALYSIS,
                priority=8
            ),

            # 爆款学习规则
            RoutingRule(
                pattern=r"(爆款|热门|趋势).*(学习|分析|研究)",
                workflow_type=WorkflowType.VIRAL_LEARNING,
                priority=7
            ),

            # 默认主工作流
            RoutingRule(
                pattern=r".*",
                workflow_type=WorkflowType.MAIN,
                priority=1
            )
        ]

    def route_request(self, user_input: str, context: Dict[str, Any] = None) -> WorkflowType:
        """根据用户输入路由到合适的工作流"""
        context = context or {}
        
        log.info(f"开始路由分析，用户输入: {user_input[:50]}...")

        # 按优先级排序规则
        sorted_rules = sorted(self.routing_rules, key=lambda x: x.priority, reverse=True)

        for rule in sorted_rules:
            if self._match_rule(rule, user_input, context):
                log.info(f"匹配到路由规则: {rule.pattern} -> {rule.workflow_type.value}")
                return rule.workflow_type

        # 默认返回主工作流
        log.info("未匹配到特定规则，使用默认主工作流")
        return WorkflowType.MAIN

    def _match_rule(self, rule: RoutingRule, user_input: str, context: Dict[str, Any]) -> bool:
        """检查规则是否匹配"""
        # 检查模式匹配
        if not re.search(rule.pattern, user_input, re.IGNORECASE):
            return False

        # 检查条件
        if rule.conditions:
            for condition in rule.conditions:
                if not self._check_condition(condition, context):
                    return False

        return True

    def _check_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """检查条件"""
        if condition == "has_file_upload":
            return context.get("has_files", False)
        # 可以添加更多条件检查
        return True

    def get_workflow_endpoint(self, workflow_type: WorkflowType) -> str:
        """获取工作流端点"""
        return self.workflow_endpoints.get(workflow_type)

class StateManager:
    """状态管理器 - 统一管理所有工作流的执行状态"""
    
    def __init__(self):
        self.executions: Dict[str, Dict[str, Any]] = {}
        self.workflow_lifecycles: Dict[str, List[Dict[str, Any]]] = {}
        
    def track_execution(self, execution_id: str, workflow_id: str, user_id: str, 
                       session_id: str) -> Dict[str, Any]:
        """跟踪工作流执行进度"""
        execution_data = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "user_id": user_id,
            "session_id": session_id,
            "status": WorkflowStatus.PENDING,
            "progress": 0,
            "start_time": datetime.now(),
            "end_time": None,
            "error_message": None,
            "steps": [],
            "current_step": None
        }
        
        self.executions[execution_id] = execution_data
        log.info(f"开始跟踪执行: {execution_id}")
        return execution_data
        
    def update_execution_status(self, execution_id: str, status: WorkflowStatus, 
                              progress: int = None, current_step: str = None,
                              error_message: str = None) -> bool:
        """更新执行状态"""
        if execution_id not in self.executions:
            log.warning(f"执行ID不存在: {execution_id}")
            return False
            
        execution = self.executions[execution_id]
        execution["status"] = status
        execution["updated_at"] = datetime.now()
        
        if progress is not None:
            execution["progress"] = progress
        if current_step:
            execution["current_step"] = current_step
        if error_message:
            execution["error_message"] = error_message
        if status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
            execution["end_time"] = datetime.now()
            
        log.info(f"更新执行状态: {execution_id} -> {status.value}")
        return True
        
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """查询执行状态"""
        return self.executions.get(execution_id)
        
    def get_user_executions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有执行"""
        return [exec_data for exec_data in self.executions.values() 
                if exec_data["user_id"] == user_id]
                
    def cleanup_old_executions(self, max_age_hours: int = 24):
        """清理旧的执行记录"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        to_remove = []
        
        for execution_id, execution in self.executions.items():
            if execution["start_time"] < cutoff_time:
                to_remove.append(execution_id)
                
        for execution_id in to_remove:
            del self.executions[execution_id]
            
        if to_remove:
            log.info(f"清理了 {len(to_remove)} 个旧执行记录")

class CommunicationManager:
    """通信管理器 - 管理与n8n工作流的通信"""
    
    def __init__(self):
        self.retry_configs = {
            WorkflowType.MAIN: {"max_retries": 3, "timeout": 30},
            WorkflowType.COMPANY_INFO: {"max_retries": 3, "timeout": 60},
            WorkflowType.VIRAL_LEARNING: {"max_retries": 2, "timeout": 45},
            WorkflowType.VIDEO_ANALYSIS: {"max_retries": 3, "timeout": 90}
        }
        
    async def execute_workflow(self, workflow: WorkflowConfig, 
                             request: ExecutionRequest) -> ExecutionResult:
        """执行工作流HTTP请求"""
        log.info(f"开始执行工作流通信: {workflow.name}")
        
        try:
            # 使用现有的N8N客户端
            result = await n8n_client.execute_workflow(workflow, request)
            
            # 格式化响应数据
            if result.response_data:
                formatted_response = self._format_response_data(result.response_data)
                result.response_data = formatted_response
                
            log.info(f"工作流通信完成: {workflow.name}, 状态: {result.status}")
            return result
            
        except Exception as e:
            log.error(f"工作流通信失败: {workflow.name}, 错误: {e}")
            raise
            
    def _format_response_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """响应数据格式化"""
        try:
            # 确保响应数据包含必要字段
            formatted_data = {
                "success": raw_data.get("success", True),
                "messageType": raw_data.get("messageType", "assistant"),
                "displayText": raw_data.get("displayText", ""),
                "data": raw_data.get("data", {}),
                "timestamp": raw_data.get("create_ts") or str(int(datetime.now().timestamp() * 1000)),
                "session_id": raw_data.get("session_id", ""),
                "business_name": raw_data.get("business_name", "")
            }
            
            # 处理文件预览
            if "file_preview" in raw_data:
                formatted_data["file_preview"] = raw_data["file_preview"]
                
            return formatted_data
            
        except Exception as e:
            log.error(f"响应数据格式化失败: {e}")
            return raw_data

class WorkflowOrchestrationCenter:
    """工作流编排中心 - 核心协调器"""
    
    def __init__(self):
        self.router_manager = RouterManager()
        self.state_manager = StateManager()
        self.communication_manager = CommunicationManager()
        
    async def initialize(self):
        """初始化编排中心"""
        log.info("正在初始化工作流编排中心...")
        
        # 确保工作流管理器已初始化
        if not workflow_manager.workflows:
            await workflow_manager.initialize()
            
        # 确保N8N客户端已初始化
        await n8n_client.initialize()
        
        log.info("工作流编排中心初始化完成")
        
    async def process_request(self, user_input: str, user_id: str, session_id: str,
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理用户请求的核心方法"""
        execution_id = str(uuid.uuid4())
        
        try:
            log.info(f"WOC开始处理请求: {execution_id}")
            
            # 1. 路由管理 - 选择合适的工作流
            workflow_type = self.router_manager.route_request(user_input, context)
            workflow = workflow_manager.get_workflows_by_type(workflow_type)[0]
            
            log.info(f"选择的工作流: {workflow.name} ({workflow_type.value})")
            
            # 2. 状态管理 - 跟踪执行状态
            execution_data = self.state_manager.track_execution(
                execution_id, workflow.id, user_id, session_id
            )
            
            # 通过Socket.IO通知开始执行
            await self._notify_socket_event("workflow_started", {
                "execution_id": execution_id,
                "workflow_type": workflow_type.value,
                "workflow_name": workflow.name,
                "user_id": user_id,
                "session_id": session_id
            }, context)
            
            # 3. 准备执行请求
            request = ExecutionRequest(
                workflow_id=workflow.id,
                session_id=session_id,
                user_id=user_id,
                message=user_input,
                business_name=context.get("business_name"),
                additional_data=context,
                timeout=workflow.timeout
            )
            
            # 4. 更新状态为运行中
            self.state_manager.update_execution_status(
                execution_id, WorkflowStatus.RUNNING, progress=10
            )
            
            # 通过Socket.IO通知进度
            await self._notify_socket_event("workflow_progress", {
                "execution_id": execution_id,
                "progress": 10,
                "message": "工作流正在执行..."
            }, context)
            
            # 5. 通信管理 - 执行工作流
            result = await self.communication_manager.execute_workflow(workflow, request)
            
            # 6. 处理执行结果
            if result.status == ExecutionStatus.COMPLETED:
                self.state_manager.update_execution_status(
                    execution_id, WorkflowStatus.COMPLETED, progress=100
                )
                
                # 通过Socket.IO通知完成
                await self._notify_socket_event("workflow_completed", {
                    "execution_id": execution_id,
                    "result": result.response_data
                }, context)
                
                return {
                    "success": True,
                    "execution_id": execution_id,
                    "workflow_type": workflow_type.value,
                    "workflow_name": workflow.name,
                    "response_data": result.response_data,
                    "execution_time": result.duration or 0
                }
            else:
                self.state_manager.update_execution_status(
                    execution_id, WorkflowStatus.FAILED, 
                    error_message=result.error_message
                )
                
                # 通过Socket.IO通知失败
                await self._notify_socket_event("workflow_failed", {
                    "execution_id": execution_id,
                    "error": result.error_message
                }, context)
                
                return {
                    "success": False,
                    "execution_id": execution_id,
                    "workflow_type": workflow_type.value,
                    "error_message": result.error_message or "工作流执行失败"
                }
                
        except Exception as e:
            log.error(f"WOC处理请求失败: {execution_id}, 错误: {e}", exc_info=True)
            
            # 更新状态为失败
            self.state_manager.update_execution_status(
                execution_id, WorkflowStatus.FAILED, error_message=str(e)
            )
            
            # 通过Socket.IO通知错误
            await self._notify_socket_event("workflow_error", {
                "execution_id": execution_id,
                "error": str(e)
            }, context)
            
            return {
                "success": False,
                "execution_id": execution_id,
                "error_message": str(e)
            }
            
    async def _notify_socket_event(self, event_type: str, data: Dict[str, Any], 
                                 context: Dict[str, Any] = None):
        """通过Socket.IO发送事件通知"""
        try:
            # 获取Socket.IO实例
            from open_webui.socket.main import sio
            
            socket_id = context.get("socket_id") if context else None
            user_id = data.get("user_id")
            
            # 构建事件数据
            event_data = {
                "type": event_type,
                "timestamp": time.time(),
                **data
            }
            
            # 如果有socket_id，直接发送到特定连接
            if socket_id:
                await sio.emit(f"hsai_{event_type}", event_data, to=socket_id)
                log.info(f"通过Socket.IO发送事件到sid {socket_id}: {event_type}")
            # 否则发送给用户的所有连接
            elif user_id:
                from open_webui.socket.main import USER_POOL
                user_sids = USER_POOL.get(user_id, [])
                for sid in user_sids:
                    await sio.emit(f"hsai_{event_type}", event_data, to=sid)
                log.info(f"通过Socket.IO发送事件到用户 {user_id}: {event_type}")
                
        except Exception as e:
            log.error(f"发送Socket.IO事件失败: {e}", exc_info=True)
            
            if not workflow:
                raise Exception(f"找不到工作流: {workflow_type}")
                
            # 2. 状态管理 - 开始跟踪执行
            execution_data = self.state_manager.track_execution(
                execution_id, workflow.id, user_id, session_id
            )
            
            # 3. 构建执行请求
            request = ExecutionRequest(
                workflow_id=workflow.id,
                session_id=session_id,
                user_id=user_id,
                message=user_input,
                business_name=context.get("business_name"),
                additional_data=context.get("additional_data", {}),
                timeout=workflow.timeout
            )
            
            # 4. 更新状态为运行中
            self.state_manager.update_execution_status(
                execution_id, WorkflowStatus.RUNNING, 0, "开始执行"
            )
            
            # 5. 通信管理 - 执行工作流
            result = await self.communication_manager.execute_workflow(workflow, request)
            
            # 6. 更新最终状态
            if result.status.value == "completed":
                self.state_manager.update_execution_status(
                    execution_id, WorkflowStatus.COMPLETED, 100, "执行完成"
                )
            else:
                self.state_manager.update_execution_status(
                    execution_id, WorkflowStatus.FAILED, 0, "执行失败",
                    result.error_message
                )
                
            # 7. 返回格式化结果
            return {
                "success": result.status.value == "completed",
                "execution_id": execution_id,
                "workflow_type": workflow_type.value,
                "workflow_name": workflow.name,
                "response_data": result.response_data,
                "execution_time": result.duration,
                "error_message": result.error_message
            }
            
        except Exception as e:
            log.error(f"WOC处理请求失败: {e}")
            
            # 更新失败状态
            self.state_manager.update_execution_status(
                execution_id, WorkflowStatus.FAILED, 0, "处理失败", str(e)
            )
            
            return {
                "success": False,
                "execution_id": execution_id,
                "error_message": str(e)
            }
            
    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        return self.state_manager.get_execution_status(execution_id)
        
    async def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        # 尝试取消N8N客户端的执行
        cancelled = await n8n_client.cancel_execution(execution_id)
        
        if cancelled:
            self.state_manager.update_execution_status(
                execution_id, WorkflowStatus.CANCELLED, 0, "用户取消"
            )
            
        return cancelled
        
    def get_workflow_stats(self) -> Dict[str, Any]:
        """获取工作流统计信息"""
        executions = list(self.state_manager.executions.values())
        
        if not executions:
            return {"total_executions": 0}
            
        status_counts = {}
        workflow_counts = {}
        total_duration = 0
        completed_count = 0
        
        for execution in executions:
            # 状态统计
            status = execution["status"].value if hasattr(execution["status"], "value") else execution["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # 工作流类型统计
            workflow_id = execution["workflow_id"]
            workflow_counts[workflow_id] = workflow_counts.get(workflow_id, 0) + 1
            
            # 时间统计
            if execution.get("end_time") and execution.get("start_time"):
                duration = (execution["end_time"] - execution["start_time"]).total_seconds()
                total_duration += duration
                completed_count += 1
                
        avg_duration = total_duration / completed_count if completed_count > 0 else 0
        success_rate = status_counts.get("completed", 0) / len(executions) * 100 if executions else 0
        
        return {
            "total_executions": len(executions),
            "status_distribution": status_counts,
            "workflow_distribution": workflow_counts,
            "average_duration": round(avg_duration, 2),
            "success_rate": round(success_rate, 2),
            "active_executions": status_counts.get("running", 0)
        }

# 全局工作流编排中心实例
workflow_orchestration_center = WorkflowOrchestrationCenter()