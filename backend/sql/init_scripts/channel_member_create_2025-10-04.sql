-- 表 channel_member 的结构
CREATE TABLE IF NOT EXISTS [channel_member] (
    id TEXT NOT NULL PRIMARY KEY,
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at BIGINT
);