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
from open_webui.utils.viral_video_processor import ViralVideoProcessor, start_viral_video_processor

# 配置日志
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["UTILS"])

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