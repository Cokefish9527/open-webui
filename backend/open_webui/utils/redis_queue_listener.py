"""
可扩展的Redis队列监听器
支持动态添加新的队列监听key和对应的处理器
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Callable, Optional, List, Set
import redis
from redis import Redis
from sqlalchemy.orm import Session

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import get_session

# 配置日志
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("CONFIG", logging.INFO))

# 队列监听器注册表
_queue_handlers: Dict[str, Callable] = {}
_queue_configs: Dict[str, Dict[str, Any]] = {}

# 监听状态
_listening = False
_listener_tasks: List[asyncio.Task] = []


def register_queue_handler(
    queue_key: str, 
    handler: Callable, 
    config: Optional[Dict[str, Any]] = None
) -> None:
    """
    注册队列处理器
    
    Args:
        queue_key: Redis队列key
        handler: 处理器函数，接收消息数据作为参数
        config: 队列配置，可包含以下选项：
            - timeout: brpop超时时间（秒），默认30
            - max_retry: 最大重试次数，默认3
            - dead_letter_queue: 死信队列key，可选
    """
    _queue_handlers[queue_key] = handler
    _queue_configs[queue_key] = config or {}
    log.info(f"已注册队列处理器: {queue_key}")


def unregister_queue_handler(queue_key: str) -> bool:
    """
    取消注册队列处理器
    
    Args:
        queue_key: Redis队列key
        
    Returns:
        bool: 是否成功取消注册
    """
    if queue_key in _queue_handlers:
        del _queue_handlers[queue_key]
        if queue_key in _queue_configs:
            del _queue_configs[queue_key]
        log.info(f"已取消注册队列处理器: {queue_key}")
        return True
    return False


def get_redis_client() -> Redis:
    """获取Redis客户端实例"""
    # 使用默认的Redis连接信息
    redis_url = "redis://localhost:6379/0"
    return redis.from_url(redis_url)


async def _process_queue_message(queue_key: str, message_data: bytes, db_session: Session) -> bool:
    """
    处理队列消息
    
    Args:
        queue_key: 队列key
        message_data: 消息数据
        db_session: 数据库会话
        
    Returns:
        bool: 处理是否成功
    """
    try:
        # 解析消息
        message = json.loads(message_data.decode('utf-8'))
        log.info(f"收到队列消息 [{queue_key}]: {message.get('message_id', 'unknown')}")
        
        # 获取处理器
        handler = _queue_handlers.get(queue_key)
        if not handler:
            log.warning(f"未找到队列处理器: {queue_key}")
            return False
            
        # 调用处理器
        if asyncio.iscoroutinefunction(handler):
            await handler(message, db_session)
        else:
            handler(message, db_session)
            
        log.info(f"队列消息处理成功 [{queue_key}]: {message.get('message_id', 'unknown')}")
        return True
        
    except json.JSONDecodeError as e:
        log.error(f"消息JSON解析失败 [{queue_key}]: {e}")
        return False
    except Exception as e:
        log.error(f"处理队列消息时发生错误 [{queue_key}]: {e}")
        return False


async def _listen_to_queue(queue_key: str, db_session: Session) -> None:
    """
    监听单个队列
    
    Args:
        queue_key: Redis队列key
        db_session: 数据库会话
    """
    redis_client = get_redis_client()
    config = _queue_configs.get(queue_key, {})
    timeout = config.get("timeout", 30)
    
    log.info(f"开始监听队列: {queue_key}")
    
    while _listening:
        try:
            # 从Redis队列中获取消息
            message = redis_client.brpop([queue_key], timeout=timeout)
            if message:
                # brpop返回的是一个元组(key, value)或None
                if isinstance(message, (list, tuple)) and len(message) == 2:
                    _, message_data = message
                    # 处理消息
                    await _process_queue_message(queue_key, message_data, db_session)
            # 如果超时，继续下一次循环
        except Exception as e:
            log.error(f"监听队列 {queue_key} 时发生错误: {e}")
            # 短暂休眠后继续
            await asyncio.sleep(1)
    
    log.info(f"停止监听队列: {queue_key}")


async def start_listening(db_session: Optional[Session] = None) -> None:
    """
    启动队列监听
    
    Args:
        db_session: 数据库会话，如果为None则自动创建
    """
    global _listening, _listener_tasks
    
    if _listening:
        log.warning("队列监听已在运行中")
        return
        
    _listening = True
    
    # 如果没有提供db_session，则创建一个新的
    if db_session is None:
        session_gen = get_session()
        db_session = next(session_gen)
        # 确保会话在监听结束后关闭
        def cleanup():
            try:
                next(session_gen, None)  # 关闭会话
            except StopIteration:
                pass
    else:
        cleanup = lambda: None  # 不需要清理外部提供的会话
    
    try:
        # 为每个注册的队列创建监听任务
        for queue_key in _queue_handlers.keys():
            task = asyncio.create_task(_listen_to_queue(queue_key, db_session))
            _listener_tasks.append(task)
            log.info(f"已启动队列监听任务: {queue_key}")
            
        log.info(f"队列监听已启动，共 {len(_queue_handlers)} 个队列")
        
        # 等待所有任务完成（除非被取消）
        if _listener_tasks:
            await asyncio.gather(*_listener_tasks, return_exceptions=True)
            
    finally:
        cleanup()
        log.info("队列监听已停止")


async def stop_listening() -> None:
    """停止队列监听"""
    global _listening, _listener_tasks
    
    _listening = False
    
    # 取消所有监听任务
    for task in _listener_tasks:
        if not task.done():
            task.cancel()
    
    # 等待任务完成
    if _listener_tasks:
        await asyncio.gather(*_listener_tasks, return_exceptions=True)
    
    _listener_tasks.clear()
    log.info("队列监听已停止")


class RedisQueueListener:
    """Redis队列监听器类"""
    
    def __init__(self):
        self._listening = False
        self._listener_task = None
        self.db_session = None
        
    async def initialize(self):
        """初始化队列监听器"""
        log.info("Redis队列监听器初始化完成")
        
    async def start_monitoring(self, db_session: Optional[Session] = None):
        """开始监控队列"""
        if self._listening:
            log.warning("队列监控已在运行中")
            return
            
        self._listening = True
        log.info("Redis队列监控已启动")
        
        # 启动监听任务
        self._listener_task = asyncio.create_task(start_listening(db_session))
        
    async def stop_monitoring(self):
        """停止监控队列"""
        self._listening = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        log.info("Redis队列监控已停止")
        
    def register_handler(
        self, 
        queue_key: str, 
        handler: Callable, 
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """注册队列处理器"""
        register_queue_handler(queue_key, handler, config)
        
    def unregister_handler(self, queue_key: str) -> bool:
        """取消注册队列处理器"""
        return unregister_queue_handler(queue_key)

# 创建全局Redis队列监听器实例
redis_queue_listener = RedisQueueListener()