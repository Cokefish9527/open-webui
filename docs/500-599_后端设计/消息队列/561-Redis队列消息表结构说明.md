# Redis队列消息表设计说明

## 概述

本设计用于同步管理Redis监听队列消息，通过在服务端从队列中获取数据时记录到数据库表中，方便查询历史的Redis队列数据变化，并支持对执行失败的队列数据进行重新执行。

## 表结构

### redis_queue_messages 表

| 字段名 | 类型 | 允许空 | 描述 |
|--------|------|--------|------|
| id | TEXT | 否 | 消息唯一标识符（主键） |
| queue_name | TEXT | 否 | Redis队列名称 |
| raw_data | TEXT | 否 | 获取到的原始数据 |
| fetched_at | BIGINT | 否 | 获取时间（时间戳） |
| execution_result | TEXT | 是 | 执行结果 |
| error_message | TEXT | 是 | 异常信息 |
| last_executed_at | BIGINT | 是 | 最后一次执行时间（时间戳） |
| status | TEXT | 否 | 消息处理状态（默认：pending） |
| retry_count | BIGINT | 是 | 重试次数（默认：0） |
| created_at | BIGINT | 否 | 创建时间（时间戳） |
| updated_at | BIGINT | 否 | 更新时间（时间戳） |

### 状态枚举

- `pending`: 待处理
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 处理失败

## 索引

1. `idx_redis_queue_messages_queue_name`: queue_name字段索引，用于按队列查询
2. `idx_redis_queue_messages_status`: status字段索引，用于按状态查询
3. `idx_redis_queue_messages_created_at`: created_at字段索引，用于按时间查询

## 使用流程

### 1. 消息记录

当监听到Redis队列有数据更新，服务端从队列中每次获取到数据时，在处理之前向表中写入一条数据：

```python
# 创建消息记录
form_data = RedisQueueMessageForm(
    queue_name="ai-conversation-agent-message-queue",
    raw_data=json_data,
    fetched_at=int(time.time())
)

# 插入到数据库
message = RedisQueueMessages.insert_new_message(form_data)
```

### 2. 执行处理

处理消息内容...

### 3. 更新结果

执行完成后更新执行情况：

```python
# 更新处理结果
update_data = RedisQueueMessageUpdateForm(
    last_executed_at=int(time.time()),
    status="completed",
    execution_result="Task completed successfully"
)
RedisQueueMessages.update_message_by_id(message_id, update_data)
```

### 4. 失败处理

如果执行失败，记录错误信息：

```python
# 记录失败信息
update_data = RedisQueueMessageUpdateForm(
    last_executed_at=int(time.time()),
    status="failed",
    error_message="Processing failed due to network error"
)
RedisQueueMessages.update_message_by_id(message_id, update_data)
```

### 5. 重新执行

对于执行失败的队列数据，可以重新执行：

```python
# 获取失败的消息
failed_messages = RedisQueueMessages.get_failed_messages("queue_name")

# 重新处理
for message in failed_messages:
    # 重新处理逻辑
    reprocess_message(message)
```

## API接口

### 插入新消息

```python
RedisQueueMessages.insert_new_message(form_data: RedisQueueMessageForm) -> Optional[RedisQueueMessageModel]
```

### 根据ID获取消息

```python
RedisQueueMessages.get_message_by_id(message_id: str) -> Optional[RedisQueueMessageModel]
```

### 根据队列名称获取消息

```python
RedisQueueMessages.get_messages_by_queue_name(
    queue_name: str, 
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[RedisQueueMessageModel]
```

### 获取失败的消息

```python
RedisQueueMessages.get_failed_messages(
    queue_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[RedisQueueMessageModel]
```

### 更新消息

```python
RedisQueueMessages.update_message_by_id(
    message_id: str, 
    form_data: RedisQueueMessageUpdateForm
) -> Optional[RedisQueueMessageModel]
```

### 增加重试次数

```python
RedisQueueMessages.increment_retry_count(message_id: str) -> bool
```

## 初始化表结构

可以通过以下方式初始化表结构：

1. 使用SQL脚本: `backend/sql/schema_updates/001_create_redis_queue_messages_table.sql`
2. 使用Python脚本: `backend/init_redis_queue_table.py`

## 使用示例

参考文件: `backend/redis_queue_handler_example.py`

该示例展示了完整的使用流程，包括消息记录、结果更新、失败处理和重新执行等功能。