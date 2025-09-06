"""
n8n工作流监控系统

监控n8n工作流的健康状态、执行情况和性能指标
"""

import asyncio
import logging
import time
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

from open_webui.config.n8n_workflows import N8NWorkflowType, get_all_workflow_configs

log = logging.getLogger(__name__)

class HealthStatus(str, Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"

@dataclass
class ExecutionInfo:
    """执行信息"""
    execution_id: str
    workflow_type: str
    user_id: str
    session_id: str
    start_time: datetime
    retry_count: int = 0

@dataclass
class WorkflowMetrics:
    """工作流指标"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_response_time: float = 0.0
    last_execution_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    last_error_message: Optional[str] = None
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))

@dataclass
class SystemHealth:
    """系统健康状态"""
    overall_status: HealthStatus
    workflow_statuses: Dict[str, HealthStatus]
    metrics: Dict[str, WorkflowMetrics]
    last_check_time: datetime
    uptime: float
    active_connections: int = 0

class N8NMonitor:
    """n8n监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, WorkflowMetrics] = defaultdict(WorkflowMetrics)
        self.start_time = datetime.now()
        self.last_health_check = None
        self.health_check_interval = 60  # 秒
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        self.active_executions: Dict[str, ExecutionInfo] = {}
        self.retry_limits: Dict[str, int] = {}
        
    async def start_monitoring(self):
        """启动监控"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        log.info("n8n monitoring started")
    
    async def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        log.info("n8n monitoring stopped")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_check(self):
        """执行健康检查"""
        try:
            workflow_configs = get_all_workflow_configs()
            
            for workflow_type, config in workflow_configs.items():
                await self._check_workflow_health(workflow_type, config)
                
            self.last_health_check = datetime.now()
            log.debug("Health check completed")
            
        except Exception as e:
            log.error(f"Health check failed: {e}")
    
    async def _check_workflow_health(self, workflow_type: str, config: Dict[str, Any]):
        """检查单个工作流健康状态"""
        try:
            # 这里可以实现具体的健康检查逻辑
            # 例如发送ping请求到webhook URL
            webhook_url = config.get("webhook_url")
            if webhook_url:
                # 简单的连接测试
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(webhook_url.replace("/webhook/", "/health/"), timeout=5) as response:
                            if response.status == 200:
                                log.debug(f"Workflow {workflow_type} is healthy")
                            else:
                                log.warning(f"Workflow {workflow_type} returned status {response.status}")
                    except Exception as e:
                        log.warning(f"Workflow {workflow_type} health check failed: {e}")
                        
        except Exception as e:
            log.error(f"Error checking workflow {workflow_type} health: {e}")
    
    def start_execution(self, execution_id: str, workflow_type: N8NWorkflowType, user_id: str, session_id: str) -> ExecutionInfo:
        """开始执行并记录执行信息"""
        execution_info = ExecutionInfo(
            execution_id=execution_id,
            workflow_type=workflow_type.value,
            user_id=user_id,
            session_id=session_id,
            start_time=datetime.now()
        )
        self.active_executions[execution_id] = execution_info
        log.debug(f"Started execution {execution_id} for workflow {workflow_type.value}")
        return execution_info
    
    def record_execution(
        self, 
        workflow_type: str, 
        success: bool, 
        response_time: float,
        error_message: Optional[str] = None
    ):
        """记录工作流执行"""
        metrics = self.metrics[workflow_type]
        metrics.total_executions += 1
        metrics.last_execution_time = datetime.now()
        
        if success:
            metrics.successful_executions += 1
            metrics.last_success_time = datetime.now()
        else:
            metrics.failed_executions += 1
            metrics.last_error_time = datetime.now()
            metrics.last_error_message = error_message
        
        # 记录响应时间
        metrics.response_times.append(response_time)
        
        # 计算平均响应时间
        if metrics.response_times:
            metrics.average_response_time = sum(metrics.response_times) / len(metrics.response_times)
        
        log.debug(f"Recorded execution for {workflow_type}: success={success}, time={response_time:.2f}s")
    
    def get_workflow_health(self, workflow_type: N8NWorkflowType) -> Dict[str, Any]:
        """获取工作流健康状态"""
        workflow_key = workflow_type.value
        metrics = self.metrics[workflow_key]
        
        # 计算健康状态
        status = self._calculate_health_status(metrics)
        
        return {
            "workflow_type": workflow_key,
            "status": status.value,
            "metrics": {
                "total_executions": metrics.total_executions,
                "successful_executions": metrics.successful_executions,
                "failed_executions": metrics.failed_executions,
                "success_rate": (
                    metrics.successful_executions / metrics.total_executions 
                    if metrics.total_executions > 0 else 0
                ),
                "average_response_time": metrics.average_response_time,
                "last_execution_time": metrics.last_execution_time.isoformat() if metrics.last_execution_time else None,
                "last_success_time": metrics.last_success_time.isoformat() if metrics.last_success_time else None,
                "last_error_time": metrics.last_error_time.isoformat() if metrics.last_error_time else None,
                "last_error_message": metrics.last_error_message
            }
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统整体健康状态"""
        workflow_statuses = {}
        overall_status = HealthStatus.HEALTHY
        
        # 检查所有工作流状态
        for workflow_type in N8NWorkflowType:
            metrics = self.metrics[workflow_type.value]
            status = self._calculate_health_status(metrics)
            workflow_statuses[workflow_type.value] = status.value
            
            # 更新整体状态
            if status == HealthStatus.ERROR:
                overall_status = HealthStatus.ERROR
            elif status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "overall_status": overall_status.value,
            "workflow_statuses": workflow_statuses,
            "uptime_seconds": uptime,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "monitoring_active": self.is_monitoring,
            "total_workflows": len(workflow_statuses)
        }
    
    def _calculate_health_status(self, metrics: WorkflowMetrics) -> HealthStatus:
        """计算健康状态"""
        if metrics.total_executions == 0:
            return HealthStatus.UNKNOWN
        
        success_rate = metrics.successful_executions / metrics.total_executions
        
        # 检查最近是否有错误
        if metrics.last_error_time:
            time_since_error = datetime.now() - metrics.last_error_time
            if time_since_error < timedelta(minutes=5):  # 5分钟内有错误
                return HealthStatus.ERROR
        
        # 基于成功率判断
        if success_rate >= 0.95:
            return HealthStatus.HEALTHY
        elif success_rate >= 0.8:
            return HealthStatus.WARNING
        else:
            return HealthStatus.ERROR
    
    def cleanup_old_data(self, max_age_hours: int = 24):
        """清理旧数据"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for workflow_type, metrics in self.metrics.items():
            # 清理旧的响应时间数据
            # 这里可以添加更复杂的清理逻辑
            log.info(f"Cleaned up old data for {workflow_type}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        total_executions = sum(m.total_executions for m in self.metrics.values())
        total_successful = sum(m.successful_executions for m in self.metrics.values())
        total_failed = sum(m.failed_executions for m in self.metrics.values())
        
        return {
            "total_executions": total_executions,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "overall_success_rate": total_successful / total_executions if total_executions > 0 else 0,
            "active_workflows": len([m for m in self.metrics.values() if m.total_executions > 0]),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
        }
    
    def should_retry(self, execution_id: str, error_message: str) -> bool:
        """检查是否应该重试执行"""
        execution_info = self.active_executions.get(execution_id)
        if not execution_info:
            return False
            
        # 获取重试限制（默认3次）
        retry_limit = self.retry_limits.get(execution_info.workflow_type, 3)
        
        # 检查重试次数是否超过限制
        if execution_info.retry_count >= retry_limit:
            return False
            
        # 某些错误可能不值得重试
        non_retryable_errors = [
            "404",  # Not found
            "401",  # Unauthorized
            "403",  # Forbidden
        ]
        
        for error in non_retryable_errors:
            if error in error_message:
                return False
                
        return True
    
    async def retry_execution(self, execution_id: str):
        """重试执行"""
        execution_info = self.active_executions.get(execution_id)
        if execution_info:
            execution_info.retry_count += 1
            log.info(f"Retrying execution {execution_id}, attempt {execution_info.retry_count}")
            # 等待一段时间再重试
            await asyncio.sleep(min(2 ** execution_info.retry_count, 30))  # 指数退避，最大30秒

# 全局监控器实例
n8n_monitor = N8NMonitor()