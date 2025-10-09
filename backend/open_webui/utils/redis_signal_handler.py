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
                            
                            # 在处理消息之前，先将原始数据保存到数据库中
                            # 确保原始数据不丢失，支持失败重试和历史追溯
                            try:
                                from open_webui.models.redis_queue_messages import RedisQueueMessages, RedisQueueMessageForm
                                
                                # 创建消息记录表单
                                # 重要：使用原始消息数据，而不是解析后的数据
                                raw_message_data = message_data.decode('utf-8') if isinstance(message_data, bytes) else str(message_data)
                                form_data = RedisQueueMessageForm(
                                    queue_name=queue_name,
                                    raw_data=raw_message_data,
                                    fetched_at=int(time.time())
                                )
                                
                                # 插入到数据库
                                message_record = RedisQueueMessages.insert_new_message(form_data)
                                if message_record:
                                    log.info(f"已记录队列消息到数据库: {message_record.id}")
                                else:
                                    log.error(f"记录队列消息到数据库失败: {queue_name}")
                            except Exception as db_error:
                                log.error(f"保存队列消息到数据库时出错: {db_error}", exc_info=True)
                            
                            # 在解析JSON之前，先尝试修复可能存在的格式问题
                            try:
                                message = json.loads(message_data.decode('utf-8'))
                            except json.JSONDecodeError as e:
                                # 如果JSON解析失败，尝试修复格式问题
                                log.warning(f"JSON解析失败，尝试修复: {e}")
                                # 解码消息数据
                                decoded_data = message_data.decode('utf-8')
                                # 尝试修复常见的JSON格式问题
                                fixed_data = self._fix_json_format(decoded_data)
                                # 再次尝试解析
                                message = json.loads(fixed_data)
                            
                            # 在新的线程中处理消息，避免阻塞监听
                            handler_thread = threading.Thread(
                                target=self._process_message,
                                args=(queue_name, message),
                                daemon=True
                            )
                            handler_thread.start()
                        
                except Exception as e:
                    log.error(f"监听队列 {queue_name} 时发生错误: {e}", exc_info=True)
                    time.sleep(1)  # 短暂休眠后重试
                    
        except Exception as e:
            log.error(f"监听队列 {queue_name} 失败: {e}", exc_info=True)
    
    def _fix_json_format(self, json_str: str) -> str:
        """
        尝试修复JSON格式问题
        """
        try:
            # 先尝试直接解析
            try:
                json.loads(json_str)
                return json_str  # 如果已经可以解析，直接返回
            except:
                pass
            
            # 尝试使用ast.literal_eval解析Python字典格式（这是最可能的情况）
            import ast
            try:
                # 尝试解析为Python字典
                data = ast.literal_eval(json_str)
                # 转换为标准JSON格式
                return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            except Exception as ast_error:
                log.debug(f"ast.literal_eval解析失败: {ast_error}")
                pass
            
            # 如果ast.literal_eval也失败，尝试更复杂的修复方法
            try:
                import re
                
                # 创建修复后字符串的副本
                fixed_str = json_str
                
                # 修复1: 处理多行字符串问题
                # 查找displayText字段中的换行问题
                display_text_match = re.search(r"'displayText':\s*'([^']*)'", fixed_str)
                if display_text_match:
                    display_text = display_text_match.group(1)
                    # 转义特殊字符
                    escaped_text = display_text.replace('\\', '\\\\').replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
                    # 替换原始文本
                    fixed_str = fixed_str.replace(f"'displayText': '{display_text}'", f'"displayText": "{escaped_text}"')
                
                # 修复2: 将单引号替换为双引号（小心处理）
                # 先处理值部分的单引号
                fixed_str = re.sub(r":\s*'([^']*)'", r': "\1"', fixed_str)
                # 处理键部分的单引号
                fixed_str = re.sub(r"'([^']+)':", r'"\1":', fixed_str)
                
                # 尝试解析修复后的字符串
                json.loads(fixed_str)
                return fixed_str
            except Exception as fix_error:
                log.debug(f"手动修复尝试失败: {fix_error}")
                pass
            
            # 如果以上方法都失败，返回原始字符串（可能会再次失败，但至少记录了错误）
            log.warning(f"无法修复JSON格式，原始数据长度: {len(json_str)}")
            # 记录前500个字符用于调试（避免日志过长）
            log.debug(f"原始数据前500字符: {json_str[:500]}")
            return json_str
            
        except Exception as e:
            log.error(f"修复JSON格式时发生错误: {e}", exc_info=True)
            return json_str
    
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

def initialize_redis_handlers():
    """初始化所有Redis队列处理器"""
    try:
        # 注册对话消息队列处理器
        from open_webui.utils.conversation_queue_handler import register_conversation_queue_handler
        register_conversation_queue_handler(redis_signal_handler)
        
        # 注册视频学习通知队列处理器
        from open_webui.utils.video_learning_notifier import register_video_learning_queue_handler
        register_video_learning_queue_handler(redis_signal_handler)
        
        # 注册任务完成信号队列处理器
        from open_webui.utils.task_completion_handler import register_task_completion_queue_handler
        register_task_completion_queue_handler(redis_signal_handler)
        
        log.info("所有Redis队列处理器注册完成")
    except Exception as e:
        log.error(f"注册Redis队列处理器时发生错误: {e}", exc_info=True)
        raise
