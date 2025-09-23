# Redis队列监听器使用说明

## 概述

Redis队列监听器是一个可扩展的队列处理系统，支持动态添加新的队列监听key和对应的处理器。该系统设计用于替代原有的基于线程的队列处理方式，提供更好的可维护性和扩展性。

## 架构设计

### 核心组件

1. **RedisQueueListener类** - 主要的监听器类
2. **队列处理器注册机制** - 动态注册和管理队列处理器
3. **配置管理** - 每个队列的独立配置
4. **异步处理** - 基于asyncio的异步处理机制

### 特性

- 支持动态添加/删除队列监听器
- 每个队列可独立配置超时、重试等参数
- 支持同步和异步处理器函数
- 自动数据库会话管理
- 错误处理和日志记录

## 使用方法

### 1. 基本使用

```python
from open_webui.utils.redis_queue_listener import redis_queue_listener

# 注册队列处理器
def my_handler(message, db_session):
    print(f"处理消息: {message}")

redis_queue_listener.register_handler("my_queue", my_handler)

# 启动监听
await redis_queue_listener.start_monitoring()
```

### 2. 带配置的队列处理器

```python
redis_queue_listener.register_handler(
    "my_queue", 
    my_handler,
    {
        "timeout": 60,          # 超时时间（秒）
        "max_retry": 3,         # 最大重试次数
        "dead_letter_queue": "my_dead_letter_queue"  # 死信队列
    }
)
```

### 3. 异步处理器

```python
async def async_handler(message, db_session):
    # 异步处理逻辑
    await some_async_operation()
    
redis_queue_listener.register_handler("async_queue", async_handler)
```

## 集成到主应用

在`main.py`中已经集成了Redis队列监听器：

```python
# 启动Redis队列监听器
from open_webui.utils.redis_queue_listener import redis_queue_listener
await redis_queue_listener.initialize()
app.state.redis_queue_listener = redis_queue_listener
app.state.redis_queue_monitoring_task = asyncio.create_task(
    redis_queue_listener.start_monitoring()
)

# 注册默认的队列处理器
from open_webui.utils.video_queue_handlers import handle_viral_video_crawl_notification
# 注册爆款视频抓取通知队列处理器
redis_queue_listener.register_handler(
    "viral_video_crawled_notification", 
    handle_viral_video_crawl_notification,
    {
        "timeout": 30,
        "max_retry": 3,
        "dead_letter_queue": "viral_video_dead_letter"
    }
)
```

## 添加新的队列监听器

### 1. 创建处理器函数

在`video_queue_handlers.py`或其他模块中创建处理器函数：

```python
async def handle_new_queue_message(message: Dict[str, Any], db_session: Session) -> None:
    """
    处理新队列消息
    
    Args:
        message: 队列消息数据
        db_session: 数据库会话
    """
    # 实现处理逻辑
    pass
```

### 2. 注册处理器

在主应用启动时注册：

```python
from open_webui.utils.my_handlers import handle_new_queue_message

redis_queue_listener.register_handler(
    "new_queue_key", 
    handle_new_queue_message,
    {
        "timeout": 30,
        "max_retry": 3
    }
)
```

## 配置选项

每个队列可以配置以下选项：

- `timeout`: brpop超时时间（秒），默认30
- `max_retry`: 最大重试次数，默认3
- `dead_letter_queue`: 死信队列key，可选

## 测试

可以使用`test_redis_queue_listener.py`脚本进行测试：

```bash
cd backend
python test_redis_queue_listener.py
```

## 扩展性

### 添加新的队列类型

1. 创建新的处理器函数
2. 在主应用中注册处理器
3. 如需要，更新配置

### 自定义配置

可以根据业务需求添加更多配置选项，如：
- 消息过滤规则
- 批量处理支持
- 优先级队列
- 消息确认机制

## 最佳实践

1. **错误处理**: 在处理器中妥善处理异常，避免影响其他消息处理
2. **资源管理**: 确保数据库会话等资源正确释放
3. **日志记录**: 详细记录处理过程，便于调试和监控
4. **性能优化**: 对于高频率队列，考虑批量处理或并发处理
5. **监控告警**: 实现处理状态监控和异常告警

## 与原有系统的兼容性

新的队列监听器设计为与原有系统并存，可以逐步迁移：
1. 保留原有的信号处理机制
2. 逐步将队列处理迁移到新的监听器
3. 最终可以完全替换原有的线程方式

## 示例：添加新的队列处理器

参考`example_queue_handler.py`文件：

```python
# 1. 创建处理器函数
async def handle_example_queue_message(message: Dict[str, Any], db_session: Session) -> None:
    # 实现处理逻辑
    pass

# 2. 注册处理器
def register_example_queue_handler(redis_queue_listener) -> None:
    redis_queue_listener.register_handler(
        "example_queue", 
        handle_example_queue_message,
        {
            "timeout": 30,
            "max_retry": 3
        }
    )
```

## 对话消息队列处理器

对话消息队列处理器用于处理来自n8n工作流的对话消息，队列名称为`ai-conversation-agent-message-queue`。

该处理器支持两种消息类型：
1. 流式传输消息（status为RUNNING）：通过`agent_message_chunk`事件逐块发送消息内容
2. 完整消息（status为FINISHED）：通过`agent_message`事件发送完整消息内容

处理器会根据消息中的session_id字段查找对应的Socket.IO连接，并将消息发送到客户端。