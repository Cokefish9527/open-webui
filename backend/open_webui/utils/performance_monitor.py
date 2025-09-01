"""
性能监控装饰器和工具
提供函数执行时间监控和性能分析功能
"""

import time
import asyncio
import functools
import logging
from typing import Callable, Any, Dict, Optional
from .hsai_monitor import hsai_monitor, ComponentType
from .hsai_logger import hsai_logger

log = logging.getLogger(__name__)

def monitor_performance(component: ComponentType, operation: str = None, 
                       log_details: bool = True):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        op_name = operation or func.__name__
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = False
                error_msg = None
                
                try:
                    result = await func(*args, **kwargs)
                    success = True
                    return result
                except Exception as e:
                    error_msg = str(e)
                    hsai_monitor.log_error(
                        component, 
                        hsai_monitor.ErrorLevel.ERROR,
                        f"Function {op_name} failed: {error_msg}",
                        details={"function": func.__name__, "args_count": len(args)}
                    )
                    raise
                finally:
                    duration = time.time() - start_time
                    
                    # 记录性能指标
                    hsai_monitor.log_performance(
                        component, op_name, duration, success,
                        details={"error": error_msg} if error_msg else None
                    )
                    
                    # 记录到日志
                    if log_details:
                        hsai_logger.log_operation(
                            component.value, op_name, duration, success,
                            details={"error": error_msg} if error_msg else None
                        )
                        
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = False
                error_msg = None
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    return result
                except Exception as e:
                    error_msg = str(e)
                    hsai_monitor.log_error(
                        component,
                        hsai_monitor.ErrorLevel.ERROR,
                        f"Function {op_name} failed: {error_msg}",
                        details={"function": func.__name__, "args_count": len(args)}
                    )
                    raise
                finally:
                    duration = time.time() - start_time
                    
                    # 记录性能指标
                    hsai_monitor.log_performance(
                        component, op_name, duration, success,
                        details={"error": error_msg} if error_msg else None
                    )
                    
                    # 记录到日志
                    if log_details:
                        hsai_logger.log_operation(
                            component.value, op_name, duration, success,
                            details={"error": error_msg} if error_msg else None
                        )
                        
            return sync_wrapper
            
    return decorator

def monitor_websocket_operation(operation: str):
    """WebSocket操作监控装饰器"""
    return monitor_performance(ComponentType.WEBSOCKET, operation)

def monitor_n8n_operation(operation: str):
    """N8N操作监控装饰器"""
    return monitor_performance(ComponentType.N8N_CLIENT, operation)

def monitor_workflow_operation(operation: str):
    """工作流操作监控装饰器"""
    return monitor_performance(ComponentType.WORKFLOW_MANAGER, operation)

class PerformanceContext:
    """性能监控上下文管理器"""
    
    def __init__(self, component: ComponentType, operation: str, 
                 user_id: str = None, session_id: str = None,
                 details: Dict[str, Any] = None):
        self.component = component
        self.operation = operation
        self.user_id = user_id
        self.session_id = session_id
        self.details = details or {}
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        
        if exc_type:
            self.details["error"] = str(exc_val)
            hsai_monitor.log_error(
                self.component,
                hsai_monitor.ErrorLevel.ERROR,
                f"Operation {self.operation} failed: {exc_val}",
                details=self.details,
                user_id=self.user_id,
                session_id=self.session_id
            )
            
        # 记录性能指标
        hsai_monitor.log_performance(
            self.component, self.operation, duration, success, self.details
        )
        
        # 记录到日志
        hsai_logger.log_operation(
            self.component.value, self.operation, duration, success,
            user_id=self.user_id, session_id=self.session_id,
            details=self.details
        )

class AsyncPerformanceContext:
    """异步性能监控上下文管理器"""
    
    def __init__(self, component: ComponentType, operation: str,
                 user_id: str = None, session_id: str = None,
                 details: Dict[str, Any] = None):
        self.component = component
        self.operation = operation
        self.user_id = user_id
        self.session_id = session_id
        self.details = details or {}
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = time.time()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        
        if exc_type:
            self.details["error"] = str(exc_val)
            hsai_monitor.log_error(
                self.component,
                hsai_monitor.ErrorLevel.ERROR,
                f"Operation {self.operation} failed: {exc_val}",
                details=self.details,
                user_id=self.user_id,
                session_id=self.session_id
            )
            
        # 记录性能指标
        hsai_monitor.log_performance(
            self.component, self.operation, duration, success, self.details
        )
        
        # 记录到日志
        hsai_logger.log_operation(
            self.component.value, self.operation, duration, success,
            user_id=self.user_id, session_id=self.session_id,
            details=self.details
        )

# 便捷函数
def perf_context(component: ComponentType, operation: str, **kwargs):
    """创建性能监控上下文"""
    return PerformanceContext(component, operation, **kwargs)

def async_perf_context(component: ComponentType, operation: str, **kwargs):
    """创建异步性能监控上下文"""
    return AsyncPerformanceContext(component, operation, **kwargs)