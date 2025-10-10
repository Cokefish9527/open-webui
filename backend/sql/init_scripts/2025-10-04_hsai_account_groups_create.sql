-- 表 hsai_account_groups 的结构
CREATE TABLE IF NOT EXISTS [hsai_account_groups] (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    color VARCHAR,
    user_id VARCHAR NOT NULL,
    config JSON,
    sort_order BIGINT,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_account_groups_user_id ON [hsai_account_groups] (user_id);