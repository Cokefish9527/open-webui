-- 表 message_reaction 的结构
CREATE TABLE IF NOT EXISTS [message_reaction] (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at BIGINT
);