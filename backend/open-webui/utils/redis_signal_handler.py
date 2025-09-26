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
        log.debug(f"原始队列消息数据 [{signal_name}]: {message_data}")
        
        # 解析消息
        message = json.loads(message_data.decode('utf-8'))
        log.info(f"收到队列消息 [{signal_name}]: {message.get('message_id', 'unknown')}")
        log.debug(f"完整消息内容 [{signal_name}]: {message}")
        
        # 获取处理器
        handler = _signal_handlers.get(signal_name)
        if not handler:
            log.warning(f"未找到信号处理器: {signal_name}")
            return False
            
        # 调用处理器
        if asyncio.iscoroutinefunction(handler):
            # 如果处理器是异步函数，使用asyncio.run运行
            asyncio.run(handler(message, db_session))
        else:
            # 如果处理器是同步函数，直接调用
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