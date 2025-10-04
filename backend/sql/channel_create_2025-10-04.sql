-- 表 channel 的结构
CREATE TABLE IF NOT EXISTS [channel] (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    name TEXT,
    description TEXT,
    data JSON,
    meta JSON,
    access_control JSON,
    created_at BIGINT,
    updated_at BIGINT,
    type TEXT
);