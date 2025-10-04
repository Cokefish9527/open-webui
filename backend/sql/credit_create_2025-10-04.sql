-- 表 credit 的结构
CREATE TABLE IF NOT EXISTS [credit] (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    credit NUMERIC(24, 12),
    updated_at BIGINT,
    created_at BIGINT
);