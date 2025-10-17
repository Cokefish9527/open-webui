-- 为 redis_queue_messages 增加 correlation_id 字段与索引
-- 日期：2025-10-17

ALTER TABLE redis_queue_messages 
ADD COLUMN IF NOT EXISTS correlation_id VARCHAR;

CREATE INDEX IF NOT EXISTS ix_redis_queue_messages_correlation_id 
ON redis_queue_messages (correlation_id);

