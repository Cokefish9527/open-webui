    async def _notify_socket_event(self, event_type: str, data: Dict[str, Any], 
                                 context: Optional[Dict[str, Any]] = None):
        """通过Socket.IO发送事件通知"""
        try:
            # 获取Socket.IO实例
            from open_webui.socket.main import sio
            
            # 检查sio是否已初始化
            if sio is None:
                log.warning("Socket.IO未初始化，无法发送事件")
                return
                
            socket_id = context.get("socket_id") if context else None
            user_id = data.get("user_id")
            
            # 构建事件数据
            event_data = {
                "timestamp": time.time(),
                **data
            }
            
            # 根据事件类型确定发送的核心事件和子类型
            core_event = "hsai_response"  # 默认使用成功响应事件
            if event_type in ["workflow_started", "workflow_progress", "workflow_completed", "status"]:
                # 工作流相关事件和状态事件合并到hsai_response
                core_event = "hsai_response"
                event_data["type"] = "hsai_response"
                event_data["subtype"] = event_type  # 添加子类型用于区分原始事件
            elif event_type in ["workflow_failed", "error"]:
                # 工作流失败和错误事件合并到hsai_error
                core_event = "hsai_error"
                event_data["type"] = "hsai_error"
                event_data["subtype"] = event_type  # 添加子类型用于区分原始事件
            else:
                # 其他事件保持原有的命名方式
                core_event = f"hsai_{event_type}"
                event_data["type"] = core_event
            
            # 如果有socket_id，直接发送到特定连接
            if socket_id:
                await sio.emit(core_event, event_data, to=socket_id)
                log.info(f"通过Socket.IO发送事件到sid {socket_id}: {event_type} (合并到 {core_event})")
            # 否则发送给用户的所有连接
            elif user_id:
                from open_webui.socket.main import USER_POOL
                user_sids = USER_POOL.get(user_id, [])
                for sid in user_sids:
                    await sio.emit(core_event, event_data, to=sid)
                log.info(f"通过Socket.IO发送事件到用户 {user_id}: {event_type} (合并到 {core_event})")
                
        except Exception as e:
            log.error(f"发送Socket.IO事件失败: {e}", exc_info=True)