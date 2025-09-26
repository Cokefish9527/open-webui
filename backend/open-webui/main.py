    # 启动Redis信号处理器
    from open_webui.utils.redis_signal_handler import redis_signal_handler
    await redis_signal_handler.initialize()
    app.state.redis_signal_handler = redis_signal_handler
    app.state.redis_signal_monitoring_task = asyncio.create_task(
        redis_signal_handler.start_monitoring()
    )

    # 注册对话消息队列处理器
    from open_webui.utils.conversation_queue_handler import register_conversation_queue_handler
    register_conversation_queue_handler(redis_signal_handler)
