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

from open_webui.env import SRC_LOG_LEVELS

# 配置日志
log = logging.getLogger(__name__)
# 使用已存在的日志源，比如"CONFIG"，而不是"UTILS"
log.setLevel(SRC_LOG_LEVELS.get("CONFIG", logging.INFO))

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
        # 使用默认的Redis连接信息
        redis_url = "redis://localhost:6379/0"
        _redis_client = redis.from_url(redis_url)
    return _redis_client


def register_signal_handler(signal_name: str, handler: Callable) -> None:
    """注册信号处理器"""
    _signal_handlers[signal_name] = handler
    log.info(f"已注册信号处理器: {signal_name}")


def _process_signals() -> None:
    """处理Redis队列中的信号"""
    global _processing
    redis_client = get_redis_client()
    
    while _processing:
        try:
            # 从Redis队列中获取信号
            message = redis_client.brpop(["signals"], timeout=1)
            if message:
                # brpop返回的是一个元组(key, value)或None
                if isinstance(message, (list, tuple)) and len(message) == 2:
                    _, signal_data = message
                    signal = json.loads(signal_data.decode("utf-8"))
                    
                    # 处理信号
                    signal_name = signal.get("signal")
                    payload = signal.get("payload", {})
                    
                    if signal_name in _signal_handlers:
                        try:
                            _signal_handlers[signal_name](payload)
                            log.info(f"已处理信号: {signal_name}")
                        except Exception as e:
                            log.error(f"处理信号 {signal_name} 时出错: {e}")
                    else:
                        log.warning(f"未找到信号处理器: {signal_name}")
                    
        except Exception as e:
            log.error(f"处理信号时出错: {e}")
            time.sleep(1)  # 出错时短暂休眠


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
    _processing_thread = threading.Thread(target=_process_signals, daemon=True)
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
    
    redis_client.lpush("signals", json.dumps(signal, ensure_ascii=False))
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
        
    async def start_monitoring(self):
        """开始监控信号"""
        if self._processing:
            log.warning("信号监控已在运行中")
            return
            
        self._processing = True
        log.info("Redis信号监控已启动")
        
        # 这里可以添加实际的监控逻辑
        # 由于原有的信号处理逻辑是基于线程的，我们可以保持原有逻辑
        # 或者重构为异步方式
        
    async def stop_monitoring(self):
        """停止监控信号"""
        self._processing = False
        log.info("Redis信号监控已停止")
        
    def start_signal_processing(self, db_session):
        """启动信号处理"""
        self.db_session = db_session
        start_signal_processing(db_session)
        
    def stop_signal_processing(self):
        """停止信号处理"""
        stop_signal_processing()

# 创建全局Redis信号处理器实例
redis_signal_handler = RedisSignalHandler()
