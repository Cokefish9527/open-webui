-- Redis队列消息表
CREATE TABLE IF NOT EXISTS redis_queue_messages (
    id TEXT PRIMARY KEY,
    queue_name TEXT NOT NULL,
    raw_data TEXT NOT NULL,
    fetched_at BIGINT NOT NULL,
    execution_result TEXT,
    error_message TEXT,
    last_executed_at BIGINT,
    status TEXT NOT NULL DEFAULT 'pending',
    retry_count BIGINT DEFAULT 0,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_redis_queue_messages_queue_name ON redis_queue_messages(queue_name);
CREATE INDEX IF NOT EXISTS idx_redis_queue_messages_status ON redis_queue_messages(status);
CREATE INDEX IF NOT EXISTS idx_redis_queue_messages_created_at ON redis_queue_messages(created_at);