-- 表 message 的结构
CREATE TABLE IF NOT EXISTS [message] (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    channel_id TEXT,
    content TEXT,
    data JSON,
    meta JSON,
    created_at BIGINT,
    updated_at BIGINT,
    parent_id TEXT
);