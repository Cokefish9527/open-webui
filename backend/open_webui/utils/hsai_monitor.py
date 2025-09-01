"""
HSAI系统监控和错误处理模块
提供完整的错误处理、日志监控和性能统计功能
"""

import logging
import asyncio
import time
import traceback
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import threading
from contextlib import asynccontextmanager

log = logging.getLogger(__name__)

class ErrorLevel(str, Enum):
    """错误级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ComponentType(str, Enum):
    """组件类型枚举"""
    WORKFLOW_MANAGER = "workflow_manager"
    WORKFLOW_SELECTOR = "workflow_selector"
    N8N_CLIENT = "n8n_client"
    MESSAGE_PROCESSOR = "message_processor"
    WEBSOCKET = "websocket"
    SYSTEM = "system"

@dataclass
class ErrorRecord:
    """错误记录"""
    timestamp: datetime
    component: ComponentType
    level: ErrorLevel
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "component": self.component.value,
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
            "stack_trace": self.stack_trace,
            "user_id": self.user_id,
            "session_id": self.session_id
        }

@dataclass
class PerformanceMetric:
    """性能指标"""
    timestamp: datetime
    component: ComponentType
    operation: str
    duration: float
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "component": self.component.value,
            "operation": self.operation,
            "duration": self.duration,
            "success": self.success,
            "details": self.details
        }

class HSAIMonitor:
    """HSAI系统监控器"""
    
    def __init__(self, max_error_records: int = 1000, max_performance_records: int = 5000):
        self.max_error_records = max_error_records
        self.max_performance_records = max_performance_records
        
        # 错误记录存储
        self.error_records: deque = deque(maxlen=max_error_records)
        self.performance_records: deque = deque(maxlen=max_performance_records)
        
        # 统计数据
        self.error_counts = defaultdict(lambda: defaultdict(int))
        self.performance_stats = defaultdict(lambda: {
            "total_calls": 0,
            "success_calls": 0,
            "total_duration": 0.0,
            "min_duration": float('inf'),
            "max_duration": 0.0
        })
        
        # 监控线程
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # 告警配置
        self.alert_thresholds = {
            "error_rate": 0.1,  # 10%错误率
            "response_time": 5.0,  # 5秒响应时间
            "memory_usage": 85.0,  # 85%内存使用率
        }
        
        # 告警回调
        self.alert_callbacks: List[Callable] = []
        
    def start_monitoring(self):
        """启动监控"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            log.info("HSAI Monitor started")
            
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        log.info("HSAI Monitor stopped")
        
    def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                self._check_alerts()
                time.sleep(30)  # 每30秒检查一次
            except Exception as e:
                log.error(f"Error in monitoring loop: {e}")
                
    def _check_alerts(self):
        """检查告警条件"""
        try:
            # 检查错误率
            self._check_error_rates()
            
        except Exception as e:
            log.error(f"Error checking alerts: {e}")
            
    def _check_error_rates(self):
        """检查错误率"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # 统计最近一小时的错误
        recent_performance = [r for r in self.performance_records if r.timestamp >= one_hour_ago]
        
        if recent_performance:
            error_count = len([r for r in recent_performance if not r.success])
            total_count = len(recent_performance)
            error_rate = error_count / total_count
            
            if error_rate > self.alert_thresholds["error_rate"]:
                self._trigger_alert("high_error_rate", {
                    "error_rate": error_rate,
                    "error_count": error_count,
                    "total_count": total_count,
                    "threshold": self.alert_thresholds["error_rate"]
                })
                
    def _trigger_alert(self, alert_type: str, data: Dict[str, Any]):
        """触发告警"""
        alert_data = {
            "type": alert_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        log.warning(f"Alert triggered: {alert_type}, data: {data}")
        
        # 调用告警回调
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                log.error(f"Error in alert callback: {e}")
                
    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
        
    def log_error(self, component: ComponentType, level: ErrorLevel, message: str,
                  details: Dict[str, Any] = None, user_id: str = None, 
                  session_id: str = None, include_stack: bool = True):
        """记录错误"""
        stack_trace = None
        if include_stack:
            stack_trace = traceback.format_exc()
            
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            component=component,
            level=level,
            message=message,
            details=details or {},
            stack_trace=stack_trace,
            user_id=user_id,
            session_id=session_id
        )
        
        self.error_records.append(error_record)
        self.error_counts[component.value][level.value] += 1
        
        # 记录到日志
        log_level = getattr(logging, level.value.upper())
        log.log(log_level, f"[{component.value}] {message}", extra={
            "user_id": user_id,
            "session_id": session_id,
            "details": details
        })
        
    def log_performance(self, component: ComponentType, operation: str, 
                       duration: float, success: bool, details: Dict[str, Any] = None):
        """记录性能指标"""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            component=component,
            operation=operation,
            duration=duration,
            success=success,
            details=details or {}
        )
        
        self.performance_records.append(metric)
        
        # 更新统计
        key = f"{component.value}_{operation}"
        stats = self.performance_stats[key]
        stats["total_calls"] += 1
        if success:
            stats["success_calls"] += 1
        stats["total_duration"] += duration
        stats["min_duration"] = min(stats["min_duration"], duration)
        stats["max_duration"] = max(stats["max_duration"], duration)
        
    @asynccontextmanager
    async def monitor_operation(self, component: ComponentType, operation: str, 
                               details: Dict[str, Any] = None):
        """监控操作上下文管理器"""
        start_time = time.time()
        success = False
        
        try:
            yield
            success = True
        except Exception as e:
            self.log_error(component, ErrorLevel.ERROR, f"Operation failed: {operation}", 
                          details={"error": str(e), **(details or {})})
            raise
        finally:
            duration = time.time() - start_time
            self.log_performance(component, operation, duration, success, details)
            
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [r for r in self.error_records if r.timestamp >= cutoff_time]
        
        summary = {
            "total_errors": len(recent_errors),
            "by_component": defaultdict(int),
            "by_level": defaultdict(int),
            "recent_errors": []
        }
        
        for error in recent_errors:
            summary["by_component"][error.component.value] += 1
            summary["by_level"][error.level.value] += 1
            
        # 最近的10个错误
        summary["recent_errors"] = [
            error.to_dict() for error in list(recent_errors)[-10:]
        ]
        
        return summary
        
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [r for r in self.performance_records if r.timestamp >= cutoff_time]
        
        summary = {
            "total_operations": len(recent_metrics),
            "success_rate": 0.0,
            "avg_duration": 0.0,
            "by_component": defaultdict(lambda: {
                "count": 0,
                "success_count": 0,
                "total_duration": 0.0
            })
        }
        
        if recent_metrics:
            success_count = sum(1 for m in recent_metrics if m.success)
            total_duration = sum(m.duration for m in recent_metrics)
            
            summary["success_rate"] = success_count / len(recent_metrics)
            summary["avg_duration"] = total_duration / len(recent_metrics)
            
            for metric in recent_metrics:
                comp_stats = summary["by_component"][metric.component.value]
                comp_stats["count"] += 1
                if metric.success:
                    comp_stats["success_count"] += 1
                comp_stats["total_duration"] += metric.duration
                
        return summary
        
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        error_summary = self.get_error_summary(1)  # 最近1小时
        perf_summary = self.get_performance_summary(1)
        
        # 计算健康分数
        health_score = 100.0
        
        # 错误率影响
        if error_summary["total_errors"] > 0:
            error_rate = error_summary["total_errors"] / max(perf_summary["total_operations"], 1)
            health_score -= min(error_rate * 100, 50)
            
        # 成功率影响
        if perf_summary["success_rate"] < 0.95:
            health_score -= (0.95 - perf_summary["success_rate"]) * 100
            
        # 响应时间影响
        if perf_summary["avg_duration"] > 2.0:
            health_score -= min((perf_summary["avg_duration"] - 2.0) * 10, 30)
            
        health_score = max(health_score, 0)
        
        status = "healthy"
        if health_score < 50:
            status = "critical"
        elif health_score < 70:
            status = "warning"
        elif health_score < 90:
            status = "degraded"
            
        return {
            "status": status,
            "health_score": round(health_score, 2),
            "error_summary": error_summary,
            "performance_summary": perf_summary,
            "timestamp": datetime.now().isoformat()
        }

# 全局监控器实例
hsai_monitor = HSAIMonitor()