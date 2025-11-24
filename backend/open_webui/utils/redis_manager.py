import time
import logging
from typing import Optional, Any
import redis
from redis.sentinel import Sentinel
from urllib.parse import urlparse

from open_webui.env import SRC_LOG_LEVELS

# 告警服务
try:
    from open_webui.utils.alert_sender import send_error_alert
    ALERT_SERVICE_AVAILABLE = True
except ImportError:
    ALERT_SERVICE_AVAILABLE = False

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

class RedisConnectionManager:
    """Redis连接管理器，提供稳定的连接和重试机制"""
    
    def __init__(self, redis_url: str, redis_sentinels: list = None, 
                 max_retries: int = 5, retry_delay: int = 5):
        self.redis_url = redis_url
        self.redis_sentinels = redis_sentinels
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._connection: Optional[Any] = None
        self._last_connection_time: float = 0
        self._connection_failures: int = 0
        self._max_connection_failures: int = 10
        
    def parse_redis_service_url(self, redis_url: str) -> dict:
        """解析Redis服务URL"""
        parsed_url = urlparse(redis_url)
        if parsed_url.scheme != "redis":
            raise ValueError("Invalid Redis URL scheme. Must be 'redis'.")
        
        return {
            "username": parsed_url.username or None,
            "password": parsed_url.password or None,
            "service": parsed_url.hostname or "mymaster",
            "port": parsed_url.port or 6379,
            "db": int(parsed_url.path.lstrip("/") or 0),
        }
        
    def _create_connection(self) -> Any:
        """创建Redis连接"""
        if self.redis_sentinels:
            redis_config = self.parse_redis_service_url(self.redis_url)
            sentinel = Sentinel(
                self.redis_sentinels,
                port=redis_config["port"],
                db=redis_config["db"],
                username=redis_config["username"],
                password=redis_config["password"],
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            return sentinel.master_for(redis_config["service"])
        elif self.redis_url:
            return redis.from_url(
                self.redis_url, 
                decode_responses=True, 
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
        else:
            return None
            
    def get_connection(self) -> Optional[Any]:
        """获取Redis连接，带重试机制"""
        # 如果已经有连接且最近连接时间在10秒内，直接返回
        if self._connection and (time.time() - self._last_connection_time) < 10:
            try:
                # 测试连接是否仍然有效
                self._connection.ping()
                # 重置连接失败计数
                self._connection_failures = 0
                return self._connection
            except Exception as e:
                log.warning(f"Redis连接失效，重新建立连接: {e}")
                self._connection = None
        
        # 如果连接失败次数过多，暂时不尝试连接
        if self._connection_failures >= self._max_connection_failures:
            log.warning(f"Redis连接失败次数过多({self._connection_failures})，暂时不尝试连接")
            return None
        
        # 尝试建立连接
        for attempt in range(self.max_retries):
            try:
                if not self._connection:
                    self._connection = self._create_connection()
                
                if self._connection:
                    self._connection.ping()
                    self._last_connection_time = time.time()
                    # 重置连接失败计数
                    self._connection_failures = 0
                    log.info("Redis连接建立成功")
                    return self._connection
                    
            except Exception as e:
                log.error(f"Redis连接尝试 {attempt + 1}/{self.max_retries} 失败: {e}")
                self._connection = None
                self._connection_failures += 1
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    # 发送连接失败告警
                    if ALERT_SERVICE_AVAILABLE:
                        try:
                            import asyncio
                            asyncio.create_task(send_error_alert(
                                error_message="Redis连接失败",
                                error_details=f"无法建立Redis连接，已尝试{self.max_retries}次: {str(e)}\n连接失败次数: {self._connection_failures}/{self._max_connection_failures}",
                                source="redis_manager",
                                category="connection_error"
                            ))
                        except Exception as alert_exc:
                            log.error(f"发送Redis连接错误告警失败: {alert_exc}")
                    
        log.error("无法建立Redis连接")
        return None
        
    def execute_with_retry(self, func, *args, **kwargs) -> Any:
        """执行Redis操作，带重试机制"""
        # 如果连接失败次数过多，直接返回
        if self._connection_failures >= self._max_connection_failures:
            log.warning(f"Redis连接失败次数过多({self._connection_failures})，跳过操作执行")
            return None
            
        for attempt in range(self.max_retries):
            try:
                conn = self.get_connection()
                if conn:
                    return func(conn, *args, **kwargs)
                else:
                    raise Exception("无法获取Redis连接")
            except Exception as e:
                log.error(f"Redis操作尝试 {attempt + 1}/{self.max_retries} 失败: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    # 发送操作失败告警
                    if ALERT_SERVICE_AVAILABLE:
                        try:
                            import asyncio
                            asyncio.create_task(send_error_alert(
                                error_message="Redis操作失败",
                                error_details=f"Redis操作失败，已尝试{self.max_retries}次: {str(e)}\n连接失败次数: {self._connection_failures}/{self._max_connection_failures}",
                                source="redis_manager",
                                category="operation_error"
                            ))
                        except Exception as alert_exc:
                            log.error(f"发送Redis操作错误告警失败: {alert_exc}")
                    raise e
                    
        return None
        
    def close(self):
        """关闭连接"""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
            
    def reset_connection_failures(self):
        """重置连接失败计数"""
        self._connection_failures = 0
        log.info("Redis连接失败计数已重置")

# 全局Redis连接管理器实例
redis_manager: Optional[RedisConnectionManager] = None

def init_redis_manager(redis_url: str, redis_sentinels: list = None) -> RedisConnectionManager:
    """初始化全局Redis连接管理器"""
    global redis_manager
    if redis_manager is None:
        redis_manager = RedisConnectionManager(redis_url, redis_sentinels)
    return redis_manager

def get_redis_manager() -> Optional[RedisConnectionManager]:
    """获取全局Redis连接管理器"""
    global redis_manager
    return redis_manager