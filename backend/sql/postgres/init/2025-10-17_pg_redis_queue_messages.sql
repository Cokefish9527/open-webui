-- PostgreSQL 初始化：redis_queue_messages（带 correlation_id）

CREATE TABLE IF NOT EXISTS redis_queue_messages (
    id VARCHAR PRIMARY KEY,
    queue_name VARCHAR NOT NULL,
    correlation_id VARCHAR,
    raw_data TEXT NOT NULL,
    fetched_at BIGINT NOT NULL,
    execution_result TEXT,
    error_message TEXT,
    last_executed_at BIGINT,
    status VARCHAR NOT NULL DEFAULT 'pending',
    retry_count BIGINT DEFAULT 0,
    created_at BIGINT,
    updated_at BIGINT
);

CREATE INDEX IF NOT EXISTS ix_rqm_correlation_id ON redis_queue_messages (correlation_id);
CREATE INDEX IF NOT EXISTS ix_rqm_queue_status ON redis_queue_messages (queue_name, status, fetched_at DESC);

