-- 表 credit_log 的结构
CREATE TABLE IF NOT EXISTS [credit_log] (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    credit NUMERIC(24, 12),
    detail JSON,
    created_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_credit_log_created_at ON [credit_log] (created_at);
CREATE INDEX IF NOT EXISTS ix_credit_log_user_id ON [credit_log] (user_id);