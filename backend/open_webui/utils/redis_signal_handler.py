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
from redis import Redis
from sqlalchemy.orm import Session

from open_webui.env import SRC_LOG_LEVELS, REDIS_URL
from open_webui.internal.db import get_session

# 配置日志
log = logging.getLogger(__name__)
# 使用已存在的日志源，比如"CONFIG"，而不是"UTILS"
log.setLevel(SRC_LOG_LEVELS.get("CONFIG", logging.INFO))

# 全局Redis客户端
_redis_client: Optional[redis.Redis] = None

# 信号处理注册表
_signal_handlers: Dict[str, Callable] = {}
_signal_configs: Dict[str, Dict[str, Any]] = {}

# 处理线程
_processing_thread: Optional[threading.Thread] = None
_video_processing_thread: Optional[threading.Thread] = None
_video_crawl_notification_thread: Optional[threading.Thread] = None

# 处理标志
_processing = False
_listening = False
_listener_tasks: List[threading.Thread] = []


def get_redis_client() -> Redis:
    """获取Redis客户端实例"""
    global _redis_client
    if _redis_client is None:
        # 使用项目配置的Redis连接信息
        _redis_client = redis.from_url(REDIS_URL)
    return _redis_client


def register_signal_handler(
    signal_name: str, 
    handler: Callable, 
    config: Optional[Dict[str, Any]] = None
) -> None:
    """注册信号处理器"""
    _signal_handlers[signal_name] = handler
    _signal_configs[signal_name] = config or {}
    log.info(f"已注册信号处理器: {signal_name}")


def unregister_signal_handler(signal_name: str) -> bool:
    """
    取消注册信号处理器
    
    Args:
        signal_name: 信号名称
        
    Returns:
        bool: 是否成功取消注册
    """
    if signal_name in _signal_handlers:
        del _signal_handlers[signal_name]
        if signal_name in _signal_configs:
            del _signal_configs[signal_name]
        log.info(f"已取消注册信号处理器: {signal_name}")
        return True
    return False


def _process_queue_message(signal_name: str, message_data: bytes, db_session: Session) -> bool:
    """
    处理队列消息
    
    Args:
        signal_name: 信号名称
        message_data: 消息数据
        db_session: 数据库会话
        
    Returns:
        bool: 处理是否成功
    """
    try:
        # 记录原始消息数据
        log.info(f"原始队列消息数据 [{signal_name}]: {message_data}")
        
        # 解析消息
        message = json.loads(message_data.decode('utf-8'))
        log.info(f"收到队列消息 [{signal_name}]: {message.get('message_id', 'unknown')}")
        log.info(f"完整消息内容 [{signal_name}]: {message}")
        
        # 获取处理器
        handler = _signal_handlers.get(signal_name)
        if not handler:
            log.info(f"未找到信号处理器: {signal_name}")
            return False
            
        # 调用处理器
        handler(message, db_session)
            
        log.info(f"队列消息处理成功 [{signal_name}]: {message.get('message_id', 'unknown')}")
        return True
        
    except json.JSONDecodeError as e:
        log.error(f"消息JSON解析失败 [{signal_name}]: {e}")
        log.error(f"原始消息数据: {message_data}")
        return False
    except Exception as e:
        log.error(f"处理队列消息时发生错误 [{signal_name}]: {e}")
        log.error(f"原始消息数据: {message_data}")
        return False


def _listen_to_queue(signal_name: str, db_session: Session) -> None:
    """
    监听单个队列
    
    Args:
        signal_name: Redis队列key
        db_session: 数据库会话
    """
    redis_client = get_redis_client()
    config = _signal_configs.get(signal_name, {})
    timeout = config.get("timeout", 30)
    
    log.info(f"开始监听队列: {signal_name}")
    
    global _listening
    while _listening:
        try:
            # 从Redis队列中获取消息
            message = redis_client.brpop([signal_name], timeout=timeout)
            if message:
                # brpop返回的是一个元组(key, value)或None
                if isinstance(message, (list, tuple)) and len(message) == 2:
                    _, message_data = message
                    # 处理消息
                    _process_queue_message(signal_name, message_data, db_session)
            # 如果超时，继续下一次循环
        except Exception as e:
            log.error(f"监听队列 {signal_name} 时发生错误: {e}")
            # 短暂休眠后继续
            time.sleep(1)
    
    log.info(f"停止监听队列: {signal_name}")


def _process_signals(db_session: Session) -> None:
    """处理Redis队列中的信号"""
    global _processing, _listening
    _listening = True
    
    # 为每个注册的信号创建监听线程
    for signal_name in _signal_handlers.keys():
        thread = threading.Thread(
            target=_listen_to_queue, 
            args=(signal_name, db_session),
            daemon=True
        )
        _listener_tasks.append(thread)
        thread.start()
        log.info(f"已启动队列监听线程: {signal_name}")
        
    log.info(f"队列监听已启动，共 {len(_signal_handlers)} 个队列")
    
    # 保持线程运行
    while _processing:
        time.sleep(1)
    
    # 停止监听
    _listening = False
    for thread in _listener_tasks:
        thread.join(timeout=5)
    _listener_tasks.clear()
    log.info("信号处理已停止")


def _process_viral_videos(db_session) -> None:
    """处理爆款视频队列"""
    try:
        from open_webui.utils.viral_video_processor import start_viral_video_processor
        start_viral_video_processor(db_session)
    except Exception as e:
        log.error(f"处理爆款视频队列时出错: {e}")


def _process_viral_video_crawl_notifications(db_session) -> None:
    """处理爆款视频抓取通知队列"""
    try:
        # 创建视频处理器实例
        from open_webui.utils.viral_video_processor import ViralVideoProcessor
        processor = ViralVideoProcessor(db_session)
        processor.start_processing()
    except Exception as e:
        log.error(f"处理爆款视频抓取通知队列时出错: {e}")


def start_signal_processing(db_session) -> None:
    """启动信号处理"""
    global _processing, _processing_thread, _video_processing_thread, _video_crawl_notification_thread
    
    if _processing:
        log.warning("信号处理已在运行中")
        return
        
    _processing = True
    
    # 启动信号处理线程
    _processing_thread = threading.Thread(
        target=_process_signals, 
        args=(db_session,),
        daemon=True
    )
    _processing_thread.start()
    
    # 启动视频处理线程
    _video_processing_thread = threading.Thread(
        target=_process_viral_videos, 
        args=(db_session,),
        daemon=True
    )
    _video_processing_thread.start()
    
    # 启动视频抓取通知处理线程
    _video_crawl_notification_thread = threading.Thread(
        target=_process_viral_video_crawl_notifications,
        args=(db_session,),
        daemon=True
    )
    _video_crawl_notification_thread.start()
    
    log.info("信号处理已启动")


def stop_signal_processing() -> None:
    """停止信号处理"""
    global _processing, _processing_thread, _video_processing_thread, _video_crawl_notification_thread
    
    _processing = False
    
    if _processing_thread:
        _processing_thread.join(timeout=5)
        _processing_thread = None
        
    if _video_processing_thread:
        _video_processing_thread.join(timeout=5)
        _video_processing_thread = None
        
    if _video_crawl_notification_thread:
        _video_crawl_notification_thread.join(timeout=5)
        _video_crawl_notification_thread = None
        
    log.info("信号处理已停止")


def send_signal(signal_name: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """发送信号到Redis队列"""
    redis_client = get_redis_client()
    
    signal = {
        "signal": signal_name,
        "payload": payload or {},
        "timestamp": int(time.time())
    }
    
    redis_client.lpush("ai-conversation-agent-message-queue", json.dumps(signal, ensure_ascii=False))
    log.info(f"已发送信号: {signal_name}")


class RedisSignalHandler:
    """Redis信号处理器类"""
    
    def __init__(self):
        self._processing = False
        self._monitoring_task = None
        self.db_session = None
        
    async def initialize(self):
        """初始化信号处理器"""
        log.info("Redis信号处理器初始化完成")
        
    async def start_monitoring(self, db_session: Optional[Session] = None):
        """开始监控信号"""
        if self._processing:
            log.warning("信号监控已在运行中")
            return
            
        self._processing = True
        log.info("Redis信号监控已启动")
        
        # 启动信号处理
        self.db_session = db_session
        start_signal_processing(db_session)
        
    async def stop_monitoring(self):
        """停止监控信号"""
        self._processing = False
        stop_signal_processing()
        log.info("Redis信号监控已停止")
        
    def register_handler(
        self, 
        signal_name: str, 
        handler: Callable, 
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """注册信号处理器"""
        register_signal_handler(signal_name, handler, config)
        
    def unregister_handler(self, signal_name: str) -> bool:
        """取消注册信号处理器"""
        return unregister_signal_handler(signal_name)

# 创建全局Redis信号处理器实例
redis_signal_handler = RedisSignalHandler()