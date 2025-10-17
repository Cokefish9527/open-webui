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

# 导入我们新创建的健壮JSON解析器
from open_webui.utils.robust_json_parser import robust_json_parse, reformat_for_frontend

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
                                # 尝试从原始消息中解析 correlation_id（request_id/reply_id 的统一追踪ID）
                                parsed_json = None
                                try:
                                    parsed_json = robust_json_parse(raw_message_data)
                                except Exception:
                                    parsed_json = None

                                correlation_id = None
                                if isinstance(parsed_json, dict):
                                    correlation_id = (
                                        parsed_json.get("correlation_id")
                                        or parsed_json.get("request_id")
                                        or parsed_json.get("reply_id")
                                        or parsed_json.get("id")
                                        or parsed_json.get("message_id")
                                    )

                                form_data = RedisQueueMessageForm(
                                    queue_name=queue_name,
                                    raw_data=raw_message_data,
                                    fetched_at=int(time.time()),
                                    correlation_id=correlation_id
                                )
                                
                                # 插入到数据库
                                message_record = RedisQueueMessages.insert_new_message(form_data)
                                if message_record:
                                    log.info(f"已记录队列消息到数据库: {message_record.id}")
                                else:
                                    log.error(f"记录队列消息到数据库失败: {queue_name}")
                            except Exception as db_error:
                                log.error(f"保存队列消息到数据库时出错: {db_error}", exc_info=True)
                            
                            # 使用健壮的JSON解析器处理可能包含未转义控制字符的消息
                            try:
                                decoded_data = message_data.decode('utf-8')
                                message = robust_json_parse(decoded_data)
                                if message is None:
                                    raise json.JSONDecodeError("Failed to parse with robust parser", decoded_data, 0)
                            except json.JSONDecodeError as e:
                                # 如果JSON解析失败，记录错误并跳过处理
                                log.error(f"JSON解析失败，无法修复: {e}")
                                log.debug(f"原始消息数据: {message_data[:500] if isinstance(message_data, (bytes, str)) else 'binary data'}")
                                continue  # 跳过这条消息，继续处理下一条
                            
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
    
    def _find_socket_by_session_id(self, session_id: str, SESSION_POOL) -> Optional[str]:
        """
        根据session_id查找对应的Socket.IO连接ID
        直接使用前端传递的session_id来维持会话
        """
        try:
            # 延迟导入Socket.IO相关模块
            from open_webui.socket.main import SESSION_ID_TO_SID
            
            log.debug(f"开始查找session_id {session_id} 对应的Socket.IO连接")
            
            # 首先尝试通过SESSION_ID_TO_SID映射查找
            if SESSION_ID_TO_SID:
                log.debug("尝试通过SESSION_ID_TO_SID映射查找")
                if isinstance(SESSION_ID_TO_SID, dict):
                    sid = SESSION_ID_TO_SID.get(session_id)
                    if sid:
                        log.info(f"通过SESSION_ID_TO_SID找到匹配的Socket.IO连接: {sid} 对应 session_id: {session_id}")
                        return sid
                    else:
                        log.debug(f"SESSION_ID_TO_SID中未找到session_id {session_id}")
                else:
                    # 对于RedisDict，需要特殊处理
                    try:
                        log.debug("SESSION_ID_TO_SID是RedisDict类型，尝试获取")
                        sid = SESSION_ID_TO_SID.get(session_id)
                        if hasattr(sid, '__await__'):
                            # 这是一个异步操作，但在同步函数中无法处理
                            # 回退到遍历SESSION_POOL的方式
                            log.debug("SESSION_ID_TO_SID返回异步对象，回退到遍历SESSION_POOL方式")
                            pass
                        elif sid:
                            log.info(f"通过SESSION_ID_TO_SID找到匹配的Socket.IO连接: {sid} 对应 session_id: {session_id}")
                            return sid
                        else:
                            log.debug(f"SESSION_ID_TO_SID中未找到session_id {session_id}")
                    except Exception as e:
                        log.error(f"通过SESSION_ID_TO_SID查找时发生异常: {e}")
                        # 如果无法通过SESSION_ID_TO_SID查找，回退到遍历SESSION_POOL的方式
                        pass
            
            # 如果通过SESSION_ID_TO_SID找不到，回退到遍历SESSION_POOL的方式
            log.debug("回退到遍历SESSION_POOL方式查找")
            # 直接遍历SESSION_POOL查找匹配的session_id
            if hasattr(SESSION_POOL, 'items'):
                found_count = 0
                for sid, session_data in SESSION_POOL.items():
                    found_count += 1
                    # 检查session_data中是否包含session_id字段，并且与传入的session_id匹配
                    if isinstance(session_data, dict) and session_data.get("session_id") == session_id:
                        log.info(f"找到匹配的Socket.IO连接: {sid} 对应 session_id: {session_id}")
                        return sid
                
                log.debug(f"遍历SESSION_POOL完成，共检查了{found_count}个会话，未找到匹配的session_id")
            else:
                log.debug("SESSION_POOL没有items方法，无法遍历")
            
            # 如果没有找到直接匹配的session_id，记录日志
            log.debug(f"未找到session_id {session_id} 对应的Socket.IO连接")
            return None
            
        except Exception as e:
            log.error(f"查找Socket.IO连接时发生错误: {e}", exc_info=True)
            return None
    
    def _find_socket_by_user_id(self, user_id: str, USER_POOL, SESSION_POOL) -> Optional[str]:
        """
        根据user_id查找对应的Socket.IO连接ID
        通过USER_POOL获取用户的所有连接，然后返回最新的一个
        
        Args:
            user_id: 用户ID
            USER_POOL: 用户连接池
            SESSION_POOL: 会话连接池
            
        Returns:
            Optional[str]: 找到的Socket.IO连接ID，未找到返回None
        """
        try:
            log.debug(f"开始查找user_id {user_id} 对应的Socket.IO连接")
            
            # 从USER_POOL获取用户的所有连接
            if isinstance(USER_POOL, dict):
                user_sids = USER_POOL.get(user_id, [])
            else:
                # 对于RedisDict，需要特殊处理
                user_sids = USER_POOL.get(user_id, [])
                # 如果是awaitable，需要await
                if user_sids is not None and hasattr(user_sids, '__await__'):
                    # 在同步函数中无法await，直接返回None
                    log.warning("RedisDict类型在同步函数中无法处理")
                    return None
                # 确保user_sids是列表类型
                if not isinstance(user_sids, list):
                    user_sids = []
                    
            log.debug(f"用户 {user_id} 的所有连接: {user_sids}")
            
            # 如果用户有连接，返回最新的一个（列表中的最后一个）
            if user_sids:
                # 验证sid是否仍然有效（在SESSION_POOL中存在）
                for sid in reversed(user_sids):  # 从最新的开始检查
                    if sid in SESSION_POOL:
                        log.info(f"通过user_id {user_id} 找到匹配的Socket.IO连接: {sid}")
                        return sid
                        
            log.debug(f"未找到user_id {user_id} 对应的Socket.IO连接")
            return None
            
        except Exception as e:
            log.error(f"通过user_id查找Socket.IO连接时发生错误: {e}", exc_info=True)
            return None
    
    def _handle_generic_message(self, message: Dict[str, Any]):
        """处理通用消息，重新封装后发送给前端"""
        try:
            # 延迟导入Socket.IO相关模块
            from open_webui.socket.main import SESSION_POOL, USER_POOL, sio
            
            log.info(f"处理通用消息: session_id={message.get('session_id')}, status={message.get('status')}")
            log.debug(f"完整消息内容: {message}")
            
            # 获取消息关键字段
            session_id = message.get("session_id")
            socket_id = message.get("socket_id")  # 优先使用socket_id
            status = message.get("status", "FINISHED")
            user_id = message.get("user_id", "")  # 提取user_id
            
            # 查找对应的Socket.IO连接，按照socket_id->session_id->user_id的顺序
            target_sid = None
            
            # 1. 优先尝试通过socket_id查找
            if socket_id:
                log.debug(f"尝试通过socket_id {socket_id} 查找Socket.IO连接")
                if socket_id in SESSION_POOL:
                    target_sid = socket_id
                    log.info(f"通过socket_id {socket_id} 找到匹配的Socket.IO连接")
                else:
                    log.warning(f"未找到socket_id {socket_id} 对应的Socket.IO连接")
            
            # 2. 如果通过socket_id找不到，尝试通过session_id查找
            if not target_sid and session_id:
                log.debug(f"尝试通过session_id {session_id} 查找Socket.IO连接")
                target_sid = self._find_socket_by_session_id(session_id, SESSION_POOL)
                
            # 3. 如果通过session_id找不到，尝试使用user_id查找
            if not target_sid and user_id:
                log.warning(f"未找到session_id {session_id} 对应的Socket.IO连接，尝试通过user_id {user_id} 查找")
                target_sid = self._find_socket_by_user_id(user_id, USER_POOL, SESSION_POOL)
                
            if not target_sid:
                log.warning(f"未找到socket_id {socket_id}、session_id {session_id} 或 user_id {user_id} 对应的Socket.IO连接")
                return
                
            # 重新封装消息以发送给前端
            frontend_message = reformat_for_frontend(message)
            
            # 发送封装后的消息到前端
            if sio is not None:
                # 在新的事件循环中发送消息
                async def send_message():
                    await sio.emit("hsai_response", frontend_message, to=target_sid)
                    log.info(f"已发送封装后的消息到前端: session_id={session_id}, status={status}")
                
                # 创建新的事件循环并运行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(send_message())
                finally:
                    loop.close()
            else:
                log.error("Socket.IO服务器未初始化")
                
        except Exception as e:
            log.error(f"处理通用消息时发生错误: {e}", exc_info=True)
    
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
                # 如果没有找到特定的处理器，尝试使用通用的消息重新封装和转发机制
                log.warning(f"未找到队列 {queue_name} 的处理器，尝试通用处理")
                self._handle_generic_message(message)
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
