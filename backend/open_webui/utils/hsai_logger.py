"""
HSAI日志配置模块
提供结构化日志记录和日志管理功能
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class HSAIFormatter(logging.Formatter):
    """HSAI自定义日志格式化器"""
    
    def __init__(self):
        super().__init__()
        
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 基础日志信息
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加额外字段
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        if hasattr(record, 'session_id'):
            log_data["session_id"] = record.session_id
        if hasattr(record, 'component'):
            log_data["component"] = record.component
        if hasattr(record, 'operation'):
            log_data["operation"] = record.operation
        if hasattr(record, 'duration'):
            log_data["duration"] = record.duration
        if hasattr(record, 'details'):
            log_data["details"] = record.details
            
        # 异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))

class HSAILogger:
    """HSAI日志管理器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 创建不同级别的日志文件
        self.log_files = {
            "all": self.log_dir / "hsai_all.log",
            "error": self.log_dir / "hsai_error.log",
            "performance": self.log_dir / "hsai_performance.log",
            "websocket": self.log_dir / "hsai_websocket.log",
            "n8n": self.log_dir / "hsai_n8n.log"
        }
        
        self.setup_loggers()
        
    def setup_loggers(self):
        """设置日志记录器"""
        # 主日志记录器
        main_logger = logging.getLogger("hsai")
        main_logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        main_logger.handlers.clear()
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        main_logger.addHandler(console_handler)
        
        # 文件处理器 - 所有日志
        all_handler = logging.handlers.RotatingFileHandler(
            self.log_files["all"],
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        all_handler.setLevel(logging.DEBUG)
        all_handler.setFormatter(HSAIFormatter())
        main_logger.addHandler(all_handler)
        
        # 错误日志处理器
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_files["error"],
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(HSAIFormatter())
        main_logger.addHandler(error_handler)
        
        # 设置子模块日志记录器
        self._setup_component_loggers()
        
    def _setup_component_loggers(self):
        """设置组件日志记录器"""
        components = [
            "hsai.websocket",
            "hsai.n8n_client", 
            "hsai.workflow_manager",
            "hsai.workflow_selector",
            "hsai.message_processor",
            "hsai.monitor"
        ]
        
        for component in components:
            logger = logging.getLogger(component)
            logger.setLevel(logging.DEBUG)
            
            # 性能日志处理器
            if "performance" not in component:
                perf_handler = logging.handlers.RotatingFileHandler(
                    self.log_files["performance"],
                    maxBytes=5*1024*1024,
                    backupCount=3,
                    encoding='utf-8'
                )
                perf_handler.setLevel(logging.INFO)
                perf_handler.setFormatter(HSAIFormatter())
                
                # 只记录包含duration的日志
                perf_handler.addFilter(lambda record: hasattr(record, 'duration'))
                logger.addHandler(perf_handler)
                
    def get_logger(self, name: str) -> logging.Logger:
        """获取日志记录器"""
        return logging.getLogger(f"hsai.{name}")
        
    def log_operation(self, logger_name: str, operation: str, duration: float, 
                     success: bool, user_id: str = None, session_id: str = None,
                     details: Dict[str, Any] = None):
        """记录操作日志"""
        logger = self.get_logger(logger_name)
        
        extra = {
            "operation": operation,
            "duration": duration,
            "success": success,
            "user_id": user_id,
            "session_id": session_id,
            "details": details or {}
        }
        
        level = logging.INFO if success else logging.ERROR
        message = f"Operation {operation} {'succeeded' if success else 'failed'} in {duration:.3f}s"
        
        logger.log(level, message, extra=extra)
        
    def log_websocket_event(self, event_type: str, user_id: str, session_id: str = None,
                           details: Dict[str, Any] = None):
        """记录WebSocket事件"""
        logger = self.get_logger("websocket")
        
        extra = {
            "event_type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "details": details or {}
        }
        
        logger.info(f"WebSocket event: {event_type}", extra=extra)
        
    def log_n8n_request(self, workflow_id: str, execution_id: str, duration: float,
                       success: bool, user_id: str = None, session_id: str = None,
                       details: Dict[str, Any] = None):
        """记录N8N请求日志"""
        logger = self.get_logger("n8n_client")
        
        extra = {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "duration": duration,
            "success": success,
            "user_id": user_id,
            "session_id": session_id,
            "details": details or {}
        }
        
        level = logging.INFO if success else logging.ERROR
        message = f"N8N workflow {workflow_id} {'completed' if success else 'failed'} in {duration:.3f}s"
        
        logger.log(level, message, extra=extra)
        
    def get_log_stats(self, hours: int = 24) -> Dict[str, Any]:
        """获取日志统计信息"""
        stats = {
            "log_files": {},
            "total_size": 0
        }
        
        for name, path in self.log_files.items():
            if path.exists():
                size = path.stat().st_size
                stats["log_files"][name] = {
                    "path": str(path),
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                }
                stats["total_size"] += size
                
        stats["total_size_mb"] = round(stats["total_size"] / (1024 * 1024), 2)
        
        return stats
        
    def cleanup_old_logs(self, days: int = 7):
        """清理旧日志文件"""
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        
        for log_file in self.log_dir.glob("*.log.*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    logging.info(f"Deleted old log file: {log_file}")
                except Exception as e:
                    logging.error(f"Failed to delete log file {log_file}: {e}")

# 全局日志管理器实例
hsai_logger = HSAILogger()