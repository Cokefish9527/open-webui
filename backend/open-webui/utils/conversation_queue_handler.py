async def handle_conversation_agent_message(message: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> None:
    """
    处理对话代理消息队列中的消息
    按照服务端消息结构规范文档重新封装消息并发送给前端
    
    Args:
        message: 从Redis队列中获取的消息数据
        config: 配置信息（可选）
    """
    try:
        # 延迟导入Socket.IO相关模块
        from open_webui.socket.main import SESSION_POOL, USER_POOL, sio
        # 导入用户模型
        from open_webui.models.users import Users
        
        log.info(f"处理对话代理消息: session_id={message.get('session_id')}, status={message.get('status')}")
        log.debug(f"完整消息内容: {message}")
        
        # 获取消息关键字段
        session_id = message.get("session_id")
        status = message.get("status", "FINISHED")
        reply_id = message.get("reply_id")
        operate_id = message.get("operate_id")
        user_id = message.get("user_id", "")  # 提取user_id
        content_type = message.get("content_type", "")
        
        # 检查是否是信息收集完成的消息 (blue_image类型且状态为FINISHED)
        if content_type == "blue_image" and status == "FINISHED" and user_id:
            log.info(f"检测到信息收集完成消息，更新用户 {user_id} 的信息收集状态")
            # 更新用户信息收集完成状态
            Users.update_user_info_collection_status(user_id, True)
        
        if not session_id:
            log.warning("消息缺少session_id字段，无法关联到客户端会话")
            return
            
        # 查找对应的Socket.IO连接
        target_sid = _find_socket_by_session_id(session_id, SESSION_POOL)
        
        # 如果通过session_id找不到，尝试使用user_id查找
        if not target_sid and user_id:
            log.warning(f"未找到session_id {session_id} 对应的Socket.IO连接，尝试通过user_id {user_id} 查找")
            target_sid = _find_socket_by_user_id(user_id, USER_POOL, SESSION_POOL)
            
        if not target_sid:
            # 添加更多调试信息
            log.warning(f"未找到session_id {session_id} 或 user_id {user_id} 对应的Socket.IO连接")
            # 记录当前SESSION_POOL中的所有session_id
            try:
                if hasattr(SESSION_POOL, 'items'):
                    existing_session_ids = []
                    for sid, session_data in SESSION_POOL.items():
                        if isinstance(session_data, dict) and session_data.get("session_id"):
                            existing_session_ids.append(f"{session_data.get('session_id')}->{sid}")
                    log.debug(f"当前SESSION_POOL中的session_id映射: {existing_session_ids}")
                else:
                    log.debug("SESSION_POOL不是dict类型，无法遍历")
            except Exception as e:
                log.error(f"记录SESSION_POOL信息时发生错误: {e}")
            return
            
        # 按照服务端消息结构规范文档重新封装消息
        # 创建符合前端定义的消息体结构
        frontend_message = {
            "type": "hsai_response",
            "success": True,
            "execution_id": reply_id or "",
            "session_id": session_id,
            "user_id": user_id,
            "execution_time": "0.00s",  # 默认值，可根据需要修改
            "timestamp": message.get("create_ts", 0),
            "messageType": message.get("content_type", 3),  # 默认为text类型
            "displayText": "",
            "data": {},
            "status": status  # 直接使用原始状态
        }
        
        # 处理内容字段
        content = message.get("content", {})
        if isinstance(content, dict):
            frontend_message["displayText"] = content.get("text", "")
            frontend_message["data"] = content.get("data", {})
        elif isinstance(content, str):
            frontend_message["displayText"] = content
        
        # 发送封装后的消息到前端
        if sio is not None:
            await sio.emit("hsai_response", frontend_message, to=target_sid)
            log.info(f"已发送封装后的消息到前端: session_id={session_id}, status={status}")
        else:
            log.error("Socket.IO服务器未初始化")
        
    except Exception as e:
        log.error(f"处理对话代理消息时发生错误: {e}", exc_info=True)
        raise