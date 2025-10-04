-- 表 hsai_publish_tasks 的结构
CREATE TABLE IF NOT EXISTS [hsai_publish_tasks] (
    id VARCHAR NOT NULL PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT,
    user_id VARCHAR NOT NULL,
    hsai_task_id VARCHAR,
    content JSON NOT NULL,
    content_type VARCHAR NOT NULL,
    platforms JSON NOT NULL,
    publish_config JSON,
    status VARCHAR,
    progress BIGINT,
    scheduled_at BIGINT,
    published_at BIGINT,
    error_message TEXT,
    retry_count BIGINT,
    tags JSON,
    priority BIGINT,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_tasks_user_id ON [hsai_publish_tasks] (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_tasks_status ON [hsai_publish_tasks] (status);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_tasks_priority ON [hsai_publish_tasks] (priority);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_tasks_scheduled_at ON [hsai_publish_tasks] (scheduled_at);