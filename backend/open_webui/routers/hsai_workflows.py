        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_response",  # 合并到核心事件中
                {
                    "type": "hsai_response",
                    "subtype": "workflow_started",  # 添加子类型用于区分原始事件
                    "execution_id": execution_id,
                    "workflow_id": request_data.workflow_id,
                    "user_id": user.id
                },
                to=user.id
            )