-- 表 hsai_publish_records 的结构
CREATE TABLE IF NOT EXISTS [hsai_publish_records] (
    id VARCHAR NOT NULL PRIMARY KEY,
    publish_task_id VARCHAR NOT NULL,
    platform_account_id VARCHAR NOT NULL,
    platform_post_id VARCHAR,
    platform_url VARCHAR,
    status VARCHAR NOT NULL,
    error_message TEXT,
    publish_data JSON,
    response_data JSON,
    views BIGINT,
    likes BIGINT,
    comments BIGINT,
    shares BIGINT,
    published_at BIGINT,
    last_stats_update_at BIGINT,
    created_at BIGINT,
    updated_at BIGINT,
    FOREIGN KEY (platform_account_id) REFERENCES hsai_platform_accounts(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (publish_task_id) REFERENCES hsai_publish_tasks(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_records_status ON [hsai_publish_records] (status);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_records_account_id ON [hsai_publish_records] (platform_account_id);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_records_task_id ON [hsai_publish_records] (publish_task_id);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_records_published_at ON [hsai_publish_records] (published_at);