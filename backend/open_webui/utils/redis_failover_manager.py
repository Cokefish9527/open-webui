"""
Redis连接熔断降级管理器

支持主Redis服务连接失败时自动切换到备用Redis服务
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from redis import asyncio as aioredis
from functools import wraps

log = logging.getLogger(__name__)

class RedisConnectionManager:
    """Redis连接管理器，支持熔断降级"""
    
    def __init__(self, primary_url: str, fallback_url: str = "redis://192.168.20.31:6379"):
        self.primary_url = primary_url
        self.fallback_url = fallback_url
        self.current_url = primary_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.is_fallback_mode = False
        self.last_connection_time = 0
        self.connection_timeout = 5  # 连接超时时间（秒）
        
    async def initialize(self):
        """初始化Redis连接"""
        await self._connect()
        
    async def _connect(self):
        """建立Redis连接"""
        # 尝试主连接
        if await self._try_connect(self.primary_url):
            self.current_url = self.primary_url
            self.is_fallback_mode = False
            log.info(f"Redis连接初始化成功，使用主连接: {self.primary_url}")
            return
            
        # 主连接失败，尝试备用连接
        log.warning(f"主Redis连接失败: {self.primary_url}，尝试备用连接: {self.fallback_url}")
        if await self._try_connect(self.fallback_url):
            self.current_url = self.fallback_url
            self.is_fallback_mode = True
            log.info(f"Redis连接初始化成功，使用备用连接: {self.fallback_url}")
            return
            
        # 所有连接都失败
        log.error(f"所有Redis连接都失败了，主连接: {self.primary_url}，备用连接: {self.fallback_url}")
        self.redis_client = None
        
    async def _try_connect(self, url: str) -> bool:
        """尝试连接到指定的Redis URL"""
        temp_client = None
        try:
            # 创建新的Redis客户端
            temp_client = aioredis.from_url(
                url, 
                socket_connect_timeout=self.connection_timeout,
                socket_timeout=self.connection_timeout,
                retry_on_timeout=True
            )
            
            # 测试连接
            await temp_client.ping()
            
            # 如果之前有连接，先关闭
            if self.redis_client:
                await self.redis_client.close()
                
            # 更新客户端
            self.redis_client = temp_client
            self.last_connection_time = asyncio.get_event_loop().time()
            return True
            
        except Exception as e:
            log.error(f"连接Redis失败 {url}: {e}")
            # 关闭临时客户端（如果创建了）
            if temp_client is not None:
                try:
                    await temp_client.close()
                except:
                    pass
            return False
            
    async def reconnect_if_needed(self):
        """检查并重新连接（如果需要）"""
        # 如果没有连接，尝试重新连接
        if self.redis_client is None:
            await self._connect()
            return
            
        # 检查连接是否仍然有效
        try:
            await self.redis_client.ping()
        except Exception as e:
            log.warning(f"Redis连接失效: {e}")
            # 尝试重新连接
            await self._connect()
            
    async def get_client(self) -> Optional[aioredis.Redis]:
        """获取Redis客户端"""
        await self.reconnect_if_needed()
        return self.redis_client
        
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.redis_client is not None
        
    def get_current_mode(self) -> str:
        """获取当前连接模式"""
        if self.is_fallback_mode:
            return "fallback"
        elif self.redis_client is not None:
            return "primary"
        else:
            return "disconnected"
            
    async def switch_to_fallback(self):
        """手动切换到备用连接"""
        if await self._try_connect(self.fallback_url):
            self.current_url = self.fallback_url
            self.is_fallback_mode = True
            log.info("手动切换到备用Redis连接")
            
    async def switch_to_primary(self):
        """手动切换到主连接"""
        if await self._try_connect(self.primary_url):
            self.current_url = self.primary_url
            self.is_fallback_mode = False
            log.info("手动切换到主Redis连接")

# 创建全局Redis连接管理器实例
redis_connection_manager: Optional[RedisConnectionManager] = None

def get_redis_connection_manager(primary_url: str, fallback_url: str = "redis://192.168.20.31:6379") -> RedisConnectionManager:
    """获取Redis连接管理器实例"""
    global redis_connection_manager
    if redis_connection_manager is None:
        redis_connection_manager = RedisConnectionManager(primary_url, fallback_url)
    return redis_connection_manager

def redis_failover_decorator(func):
    """Redis熔断降级装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 获取Redis连接管理器
        from open_webui.env import WEBSOCKET_REDIS_URL
        manager = get_redis_connection_manager(WEBSOCKET_REDIS_URL)
        
        # 确保连接有效
        await manager.reconnect_if_needed()
        
        # 执行原函数
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            log.error(f"Redis操作失败: {e}")
            # 如果是连接相关错误，尝试切换到备用连接后重试
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                log.info("尝试切换到备用Redis连接后重试")
                await manager.switch_to_fallback()
                # 重新获取客户端并重试
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as retry_e:
                    log.error(f"重试失败: {retry_e}")
                    raise retry_e
            else:
                raise e
                
    return wrapper