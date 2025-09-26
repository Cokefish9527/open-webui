async def handle_conversation_agent_message(message: Dict[str, Any], db_session: Session) -> None:
    """
    处理对话代理消息队列中的消息
    按照服务端消息结构规范文档重新封装消息并发送给前端
    
    Args:
        message: 从Redis队列中获取的消息数据
        db_session: 数据库会话
    """
    try:
        # 延迟导入Socket.IO相关模块
        from open_webui.socket.main import SESSION_POOL, sio
        
        log.info(f"开始处理对话代理消息")
        log.debug(f"原始消息内容: {message}")
        
        # 获取消息关键字段
        session_id = message.get("session_id")
        status = message.get("status", "FINISHED")
        reply_id = message.get("reply_id")
        operate_id = message.get("operate_id")
        
        log.info(f"消息关键字段: session_id={session_id}, status={status}, reply_id={reply_id}")
        
        if not session_id:
            log.warning("消息缺少session_id字段，无法关联到客户端会话")
            return
            
        # 查找对应的Socket.IO连接
        target_sid = _find_socket_by_session_id(session_id, SESSION_POOL)
        if not target_sid:
            log.warning(f"未找到session_id {session_id} 对应的Socket.IO连接")
            return
            
        log.info(f"找到Socket.IO连接: {target_sid}")
            
        # 按照服务端消息结构规范文档重新封装消息
        # 创建符合前端定义的消息体结构
        frontend_message = {
            "type": "hsai_response",
            "success": True,
            "execution_id": reply_id or "",
            "session_id": session_id,
            "user_id": message.get("user_id", ""),
            "execution_time": "0.00s",  # 默认值，可根据需要修改
            "timestamp": message.get("create_ts", 0),
            "messageType": message.get("content_type", 3),  # 默认为text类型
            "displayText": "",
            "data": {},
            "status": status  # 直接使用原始状态
        }
        
        log.debug(f"封装前的消息内容: {frontend_message}")
        
        # 处理内容字段
        content = message.get("content", {})
        if isinstance(content, dict):
            frontend_message["displayText"] = content.get("text", "")
            frontend_message["data"] = content.get("data", {})
        elif isinstance(content, str):
            frontend_message["displayText"] = content
        
        log.debug(f"封装后的消息内容: {frontend_message}")
        
        # 发送封装后的消息到前端
        if sio is not None:
            await sio.emit("hsai_response", frontend_message, to=target_sid)
            log.info(f"已发送封装后的消息到前端: session_id={session_id}, status={status}")
        else:
            log.error("Socket.IO服务器未初始化")
        
    except Exception as e:
        log.error(f"处理对话代理消息时发生错误: {e}", exc_info=True)
        raise


def _find_socket_by_session_id(session_id: str, SESSION_POOL) -> Optional[str]:
    """
    根据session_id查找对应的Socket.IO连接ID
    通过遍历SESSION_POOL查找匹配的session_id
    """
    try:
        log.debug(f"开始查找session_id {session_id} 对应的Socket.IO连接")
        log.debug(f"SESSION_POOL内容: {SESSION_POOL}")
        
        # 遍历SESSION_POOL查找匹配的session_id
        for sid, session_data in SESSION_POOL.items():
            log.debug(f"检查sid {sid}: {session_data}")
            # 检查session_data中是否包含session_id字段
            if isinstance(session_data, dict) and session_data.get("session_id") == session_id:
                log.info(f"找到匹配的Socket.IO连接: {sid}")
                return sid
                
        # 如果在SESSION_POOL中没找到，尝试通过用户关联查找
        # 这种情况适用于session_id是用户会话ID的情况
        log.debug("未在SESSION_POOL中直接找到匹配项，尝试通过用户关联查找")
        for sid, session_data in SESSION_POOL.items():
            if isinstance(session_data, dict) and session_data.get("id"):
                user_id = session_data.get("id")
                # 检查用户是否有关联的session_id
                # 这里假设session_id格式为"session_{user_id}_{timestamp}"
                if session_id.startswith(f"session_{user_id}_"):
                    log.info(f"通过用户关联找到匹配的Socket.IO连接: {sid}")
                    return sid
                    
        log.debug(f"未找到session_id {session_id} 对应的Socket.IO连接")
        return None
        
    except Exception as e:
        log.error(f"查找Socket.IO连接时发生错误: {e}", exc_info=True)
        return None
