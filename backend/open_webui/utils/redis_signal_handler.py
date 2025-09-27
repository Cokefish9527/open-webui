"""
Redis信号处理器，用于监听Redis队列中的信号并触发相应的操作
"""

import asyncio
import json
import logging
import threading
import time
from typing import Dict, Any, Callable, Optional, List, Tuple, Union
import redis

from open_webui.env import SRC_LOG_LEVELS, REDIS_URL

# 配置日志
log = logging.getLogger(__name__)
# 修复：使用已存在的日志级别键，而不是"UTILS"
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

# 全局Redis客户端
_redis_client: Optional[redis.Redis] = None

# 信号处理注册表
_signal_handlers: Dict[str, Callable] = {}

# 处理线程
_processing_thread: Optional[threading.Thread] = None
_video_processing_thread: Optional[threading.Thread] = None
_video_crawl_notification_thread: Optional[threading.Thread] = None

# 处理标志
_processing = False

def get_redis_client() -> redis.Redis:
    """获取Redis客户端实例"""
    global _redis_client
    if _redis_client is None:
        # 使用项目配置的Redis连接信息
        _redis_client = redis.from_url(REDIS_URL)
    return _redis_client

class RedisSignalHandler:
    """Redis信号处理器类"""
    
    def __init__(self):
        self._processing = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._handlers: Dict[str, Dict[str, Any]] = {}
        self._redis_client = None
        self._queue_threads: Dict[str, threading.Thread] = {}
        
    async def initialize(self):
        """初始化Redis信号处理器"""
        try:
            log.info("初始化Redis信号处理器...")
            self._redis_client = get_redis_client()
            self._processing = True
            log.info("Redis信号处理器初始化完成")
        except Exception as e:
            log.error(f"初始化Redis信号处理器失败: {e}")
            raise
    
    async def start_monitoring(self):
        """启动信号监控"""
        log.info("启动Redis信号监控...")
        # 为每个注册的队列启动监听线程
        for queue_name in self._handlers:
            if queue_name not in self._queue_threads or not self._queue_threads[queue_name].is_alive():
                thread = threading.Thread(
                    target=self._listen_to_queue, 
                    args=(queue_name,), 
                    daemon=True
                )
                self._queue_threads[queue_name] = thread
                thread.start()
                log.info(f"已启动队列 {queue_name} 的监听线程")
    
    def _listen_to_queue(self, queue_name: str):
        """监听指定队列的消息"""
        try:
            log.info(f"开始监听队列: {queue_name}")
            redis_client = get_redis_client()
            
            while self._processing:
                try:
                    # 从队列中阻塞式获取消息
                    # 使用BLPOP命令，超时时间为30秒
                    result = redis_client.blpop([queue_name], timeout=30)
                    
                    if result:
                        # 解析消息
                        # blpop返回的是一个元组 (queue_name, message_data)
                        if isinstance(result, (list, tuple)) and len(result) >= 2:
                            message_data = result[1]  # 第二个元素是消息内容
                            message = json.loads(message_data.decode('utf-8'))
                            
                            # 在新的线程中处理消息，避免阻塞监听
                            handler_thread = threading.Thread(
                                target=self._process_message,
                                args=(queue_name, message),
                                daemon=True
                            )
                            handler_thread.start()
                        
                except Exception as e:
                    log.error(f"监听队列 {queue_name} 时发生错误: {e}")
                    time.sleep(1)  # 短暂休眠后重试
                    
        except Exception as e:
            log.error(f"监听队列 {queue_name} 失败: {e}")
    
    def _process_message(self, queue_name: str, message: Dict[str, Any]):
        """处理队列消息"""
        try:
            if queue_name in self._handlers:
                handler_info = self._handlers[queue_name]
                handler = handler_info["handler"]
                config = handler_info["config"]
                
                # 创建一个新的事件循环来处理异步函数
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # 调用处理函数
                    if asyncio.iscoroutinefunction(handler):
                        loop.run_until_complete(handler(message, config))
                    else:
                        handler(message, config)
                finally:
                    loop.close()
                    
                log.info(f"已处理队列 {queue_name} 的消息")
            else:
                log.warning(f"未找到队列 {queue_name} 的处理器")
        except Exception as e:
            log.error(f"处理队列 {queue_name} 的消息时发生错误: {e}")
    
    async def stop_monitoring(self):
        """停止信号监控"""
        log.info("停止Redis信号监控...")
        self._processing = False
        
        # 等待所有监听线程结束
        for thread in self._queue_threads.values():
            if thread.is_alive():
                thread.join(timeout=5)
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
    
    def register_handler(self, signal_type: str, handler: Callable, config: Optional[Dict[str, Any]] = None):
        """注册信号处理器"""
        self._handlers[signal_type] = {
            "handler": handler,
            "config": config or {}
        }
        log.info(f"注册信号处理器: {signal_type}")
    
    async def _handle_signal(self, signal_type: str, data: Dict[str, Any]):
        """处理信号"""
        if signal_type in self._handlers:
            try:
                handler_info = self._handlers[signal_type]
                handler = handler_info["handler"]
                config = handler_info["config"]
                # 传递配置信息给处理函数
                await handler(data, config)
            except Exception as e:
                log.error(f"处理信号 {signal_type} 时发生错误: {e}")
        else:
            log.warning(f"未找到信号 {signal_type} 的处理器")

# 全局Redis信号处理器实例
redis_signal_handler = RedisSignalHandler()