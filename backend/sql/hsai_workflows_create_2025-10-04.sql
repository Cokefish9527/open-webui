-- 表 hsai_workflows 的结构
CREATE TABLE IF NOT EXISTS [hsai_workflows] (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    user_id VARCHAR NOT NULL,
    definition JSON NOT NULL,
    variables JSON,
    status VARCHAR,
    version VARCHAR,
    execution_count BIGINT,
    last_executed_at BIGINT,
    category VARCHAR,
    tags JSON,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_workflows_category ON [hsai_workflows] (category);
CREATE INDEX IF NOT EXISTS ix_hsai_workflows_status ON [hsai_workflows] (status);
CREATE INDEX IF NOT EXISTS ix_hsai_workflows_user_id ON [hsai_workflows] (user_id);