"""
N8N Webhook调用客户端
支持异步HTTP请求和错误处理
"""

import asyncio
import aiohttp
import logging
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from datetime import datetime, timedelta

from .n8n_workflow_manager import WorkflowConfig
from .performance_monitor import monitor_n8n_operation, async_perf_context
from .hsai_monitor import ComponentType
from .hsai_logger import hsai_logger

log = logging.getLogger(__name__)

class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class ExecutionRequest:
    """执行请求"""
    workflow_id: str
    session_id: str
    user_id: str
    message: str
    business_name: Optional[str] = None
    additional_data: Dict[str, Any] = None
    priority: int = 1
    timeout: int = 30
    
    def to_webhook_payload(self) -> Dict[str, Any]:
        """转换为webhook负载"""
        payload = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "message": self.message,
            "timestamp": int(time.time() * 1000),
            "request_id": str(uuid.uuid4())
        }
        
        if self.business_name:
            payload["business_name"] = self.business_name
            
        if self.additional_data:
            payload.update(self.additional_data)
            
        return {"body": payload}

@dataclass
class ExecutionResult:
    """执行结果"""
    execution_id: str
    workflow_id: str
    status: ExecutionStatus
    request_data: Dict[str, Any]
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    start_time: datetime = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
            
    def mark_completed(self, response_data: Dict[str, Any]):
        """标记为完成"""
        self.status = ExecutionStatus.COMPLETED
        self.response_data = response_data
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        
    def mark_failed(self, error_message: str):
        """标记为失败"""
        self.status = ExecutionStatus.FAILED
        self.error_message = error_message
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()

class N8NClient:
    """N8N客户端"""
    
    def __init__(self, base_url: str = "http://localhost:5678", 
                 default_timeout: int = 30, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        self.executions: Dict[str, ExecutionResult] = {}
        
        # 连接池配置
        self.connector = aiohttp.TCPConnector(
            limit=100,  # 总连接池大小
            limit_per_host=30,  # 每个主机的连接数
            ttl_dns_cache=300,  # DNS缓存时间
            use_dns_cache=True,
        )
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
        
    async def initialize(self):
        """初始化客户端"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.default_timeout)
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=timeout,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'OpenWebUI-N8N-Client/1.0'
                }
            )
        log.info("N8N Client initialized")
        
    async def close(self):
        """关闭客户端"""
        if self.session:
            await self.session.close()
            self.session = None
        if self.connector:
            await self.connector.close()
        log.info("N8N Client closed")
        
    @monitor_n8n_operation("execute_workflow")
    async def execute_workflow(self, workflow: WorkflowConfig, 
                             request: ExecutionRequest) -> ExecutionResult:
        """执行工作流"""
        execution_id = str(uuid.uuid4())
        
        # 创建执行结果对象
        result = ExecutionResult(
            execution_id=execution_id,
            workflow_id=workflow.id,
            status=ExecutionStatus.PENDING,
            request_data=asdict(request)
        )
        
        self.executions[execution_id] = result
        
        async with async_perf_context(
            ComponentType.N8N_CLIENT, 
            f"workflow_{workflow.type.value}",
            user_id=request.user_id,
            session_id=request.session_id,
            details={"workflow_id": workflow.id, "execution_id": execution_id}
        ):
            try:
                log.info(f"Executing workflow {workflow.name} (ID: {execution_id})")
                result.status = ExecutionStatus.RUNNING
                
                # 准备请求数据
                payload = request.to_webhook_payload()
                
                # 执行HTTP请求（带重试）
                response_data = await self._execute_with_retry(
                    workflow.webhook_url,
                    payload,
                    workflow.timeout or request.timeout,
                    workflow.retry_count or self.max_retries
                )
                
                # 标记完成
                result.mark_completed(response_data)
                log.info(f"Workflow execution completed: {execution_id}")
                
                # 记录成功的N8N请求
                hsai_logger.log_n8n_request(
                    workflow.id, execution_id, result.duration or 0,
                    True, request.user_id, request.session_id,
                    {"workflow_type": workflow.type.value}
                )
                
            except asyncio.TimeoutError:
                result.status = ExecutionStatus.TIMEOUT
                result.mark_failed("Execution timeout")
                log.error(f"Workflow execution timeout: {execution_id}")
                
                # 记录超时的N8N请求
                hsai_logger.log_n8n_request(
                    workflow.id, execution_id, result.duration or 0,
                    False, request.user_id, request.session_id,
                    {"error": "timeout", "workflow_type": workflow.type.value}
                )
                
            except Exception as e:
                result.mark_failed(str(e))
                log.error(f"Workflow execution failed: {execution_id}, error: {e}")
                
                # 记录失败的N8N请求
                hsai_logger.log_n8n_request(
                    workflow.id, execution_id, result.duration or 0,
                    False, request.user_id, request.session_id,
                    {"error": str(e), "workflow_type": workflow.type.value}
                )
                
        return result
        
    async def _execute_with_retry(self, url: str, payload: Dict[str, Any],
                                timeout: int, max_retries: int) -> Dict[str, Any]:
        """带重试的HTTP请求执行"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # 指数退避
                    wait_time = min(2 ** attempt, 10)
                    log.info(f"Retrying request in {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    
                async with self.session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    
                    # 检查HTTP状态码
                    if response.status >= 400:
                        error_text = await response.text()
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"HTTP {response.status}: {error_text}"
                        )
                    
                    # 解析响应
                    content_type = response.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        return await response.json()
                    else:
                        text_response = await response.text()
                        return {"raw_response": text_response}
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                log.warning(f"Request attempt {attempt + 1} failed: {e}")
                
                # 如果是最后一次尝试，抛出异常
                if attempt == max_retries:
                    break
                    
        # 所有重试都失败了
        raise last_exception
        
    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionResult]:
        """获取执行状态"""
        return self.executions.get(execution_id)
        
    async def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        result = self.executions.get(execution_id)
        if result and result.status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            result.status = ExecutionStatus.CANCELLED
            result.mark_failed("Execution cancelled by user")
            log.info(f"Execution cancelled: {execution_id}")
            return True
        return False
        
    async def batch_execute(self, requests: List[tuple]) -> List[ExecutionResult]:
        """批量执行工作流"""
        tasks = []
        for workflow, request in requests:
            task = asyncio.create_task(self.execute_workflow(workflow, request))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 创建失败的执行结果
                workflow, request = requests[i]
                failed_result = ExecutionResult(
                    execution_id=str(uuid.uuid4()),
                    workflow_id=workflow.id,
                    status=ExecutionStatus.FAILED,
                    request_data=asdict(request)
                )
                failed_result.mark_failed(str(result))
                processed_results.append(failed_result)
            else:
                processed_results.append(result)
                
        return processed_results
        
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        total = len(self.executions)
        if total == 0:
            return {"total": 0}
            
        status_counts = {}
        total_duration = 0
        completed_count = 0
        
        for result in self.executions.values():
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if result.duration:
                total_duration += result.duration
                completed_count += 1
                
        avg_duration = total_duration / completed_count if completed_count > 0 else 0
        
        return {
            "total_executions": total,
            "status_distribution": status_counts,
            "average_duration": round(avg_duration, 2),
            "success_rate": round(status_counts.get("completed", 0) / total * 100, 2) if total > 0 else 0
        }
        
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            start_time = time.time()
            
            # 尝试访问n8n健康检查端点
            health_url = f"{self.base_url}/healthz"
            async with self.session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_time = time.time() - start_time
                
                return {
                    "status": "healthy" if response.status == 200 else "unhealthy",
                    "response_time": round(response_time * 1000, 2),  # ms
                    "n8n_status": response.status,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# 全局N8N客户端实例
n8n_client = N8NClient()