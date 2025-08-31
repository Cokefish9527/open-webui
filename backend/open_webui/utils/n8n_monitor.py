"""
n8n工作流监控和错误处理

提供工作流执行监控、错误处理、重试机制和性能统计
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from open_webui.config.n8n_workflows import N8NWorkflowType

log = logging.getLogger(__name__)

@dataclass
class WorkflowExecution:
    """工作流执行记录"""
    execution_id: str
    workflow_type: N8NWorkflowType
    user_id: str
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    retry_count: int = 0
    response_size: int = 0

@dataclass
class WorkflowStats:
    """工作流统计信息"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_execution_time: float = 0.0
    total_execution_time: float = 0.0
    last_execution_time: Optional[float] = None
    error_rate: float = 0.0
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=10))

class N8NMonitor:
    """n8n工作流监控器"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.executions: deque = deque(maxlen=max_history)
        self.stats: Dict[N8NWorkflowType, WorkflowStats] = defaultdict(WorkflowStats)
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.error_patterns: Dict[str, int] = defaultdict(int)
        
        # 监控配置
        self.max_retry_count = 3
        self.retry_delays = [1, 2, 5]  # 重试延迟（秒）
        self.timeout_threshold = 300  # 超时阈值（秒）
        self.error_rate_threshold = 0.5  # 错误率阈值
        
    def start_execution(
        self, 
        execution_id: str, 
        workflow_type: N8NWorkflowType,
        user_id: str,
        session_id: str
    ) -> WorkflowExecution:
        """开始工作流执行监控"""
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_type=workflow_type,
            user_id=user_id,
            session_id=session_id,
            start_time=time.time()
        )
        
        self.active_executions[execution_id] = execution
        log.debug(f"Started monitoring execution {execution_id} for workflow {workflow_type.value}")
        
        return execution
    
    def complete_execution(
        self, 
        execution_id: str, 
        success: bool = True,
        error_message: Optional[str] = None,
        response_size: int = 0
    ):
        """完成工作流执行监控"""
        if execution_id not in self.active_executions:
            log.warning(f"Execution {execution_id} not found in active executions")
            return
        
        execution = self.active_executions[execution_id]
        execution.end_time = time.time()
        execution.success = success
        execution.error_message = error_message
        execution.response_size = response_size
        
        # 更新统计信息
        self._update_stats(execution)
        
        # 移动到历史记录
        self.executions.append(execution)
        del self.active_executions[execution_id]
        
        # 记录错误模式
        if not success and error_message:
            self.error_patterns[error_message] += 1
        
        log.debug(f"Completed monitoring execution {execution_id}: success={success}")
    
    def _update_stats(self, execution: WorkflowExecution):
        """更新工作流统计信息"""
        stats = self.stats[execution.workflow_type]
        
        stats.total_executions += 1
        stats.last_execution_time = execution.end_time
        
        if execution.success:
            stats.successful_executions += 1
        else:
            stats.failed_executions += 1
            if execution.error_message:
                stats.recent_errors.append({
                    "timestamp": execution.end_time,
                    "error": execution.error_message,
                    "execution_id": execution.execution_id
                })
        
        # 计算执行时间
        if execution.end_time:
            execution_time = execution.end_time - execution.start_time
            stats.total_execution_time += execution_time
            stats.average_execution_time = stats.total_execution_time / stats.total_executions
        
        # 计算错误率
        if stats.total_executions > 0:
            stats.error_rate = stats.failed_executions / stats.total_executions
    
    def should_retry(self, execution_id: str, error_message: str) -> bool:
        """判断是否应该重试"""
        if execution_id not in self.active_executions:
            return False
        
        execution = self.active_executions[execution_id]
        
        # 检查重试次数
        if execution.retry_count >= self.max_retry_count:
            return False
        
        # 检查错误类型（某些错误不应重试）
        non_retryable_errors = [
            "authentication failed",
            "invalid webhook url",
            "permission denied",
            "bad request"
        ]
        
        error_lower = error_message.lower()
        for non_retryable in non_retryable_errors:
            if non_retryable in error_lower:
                return False
        
        return True
    
    async def retry_execution(self, execution_id: str) -> int:
        """执行重试，返回延迟时间"""
        if execution_id not in self.active_executions:
            return 0
        
        execution = self.active_executions[execution_id]
        execution.retry_count += 1
        
        # 获取重试延迟
        delay_index = min(execution.retry_count - 1, len(self.retry_delays) - 1)
        delay = self.retry_delays[delay_index]
        
        log.info(f"Retrying execution {execution_id} (attempt {execution.retry_count}) after {delay}s")
        
        await asyncio.sleep(delay)
        return delay
    
    def check_timeouts(self) -> List[str]:
        """检查超时的执行"""
        current_time = time.time()
        timeout_executions = []
        
        for execution_id, execution in self.active_executions.items():
            if current_time - execution.start_time > self.timeout_threshold:
                timeout_executions.append(execution_id)
                log.warning(f"Execution {execution_id} timed out after {self.timeout_threshold}s")
        
        return timeout_executions
    
    def get_workflow_health(self, workflow_type: N8NWorkflowType) -> Dict[str, Any]:
        """获取工作流健康状态"""
        stats = self.stats[workflow_type]
        
        # 计算最近的错误率（最近10次执行）
        recent_executions = [
            ex for ex in list(self.executions)[-10:] 
            if ex.workflow_type == workflow_type
        ]
        recent_error_rate = 0.0
        if recent_executions:
            recent_failures = sum(1 for ex in recent_executions if not ex.success)
            recent_error_rate = recent_failures / len(recent_executions)
        
        # 判断健康状态
        health_status = "healthy"
        if stats.error_rate > self.error_rate_threshold:
            health_status = "unhealthy"
        elif recent_error_rate > 0.3:
            health_status = "degraded"
        
        return {
            "workflow_type": workflow_type.value,
            "health_status": health_status,
            "total_executions": stats.total_executions,
            "success_rate": 1 - stats.error_rate if stats.total_executions > 0 else 0,
            "average_execution_time": stats.average_execution_time,
            "recent_error_rate": recent_error_rate,
            "active_executions": len([
                ex for ex in self.active_executions.values() 
                if ex.workflow_type == workflow_type
            ]),
            "last_execution": stats.last_execution_time,
            "recent_errors": list(stats.recent_errors)
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取整体系统健康状态"""
        total_executions = sum(stats.total_executions for stats in self.stats.values())
        total_failures = sum(stats.failed_executions for stats in self.stats.values())
        
        overall_error_rate = total_failures / total_executions if total_executions > 0 else 0
        
        workflow_health = {
            workflow_type.value: self.get_workflow_health(workflow_type)
            for workflow_type in N8NWorkflowType
        }
        
        return {
            "overall_health": "healthy" if overall_error_rate < 0.1 else "degraded" if overall_error_rate < 0.3 else "unhealthy",
            "total_executions": total_executions,
            "overall_success_rate": 1 - overall_error_rate,
            "active_executions": len(self.active_executions),
            "workflow_health": workflow_health,
            "top_errors": dict(sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    def cleanup_old_data(self, max_age_hours: int = 24):
        """清理旧数据"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        # 清理执行历史
        while self.executions and self.executions[0].start_time < cutoff_time:
            self.executions.popleft()
        
        # 清理错误模式（保留计数但重置过旧的）
        if len(self.error_patterns) > 100:
            # 保留最常见的50个错误模式
            top_errors = dict(sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)[:50])
            self.error_patterns = defaultdict(int, top_errors)

# 全局监控实例
n8n_monitor = N8NMonitor()