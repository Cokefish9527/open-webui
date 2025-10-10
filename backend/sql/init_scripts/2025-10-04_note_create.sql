-- 表 note 的结构
CREATE TABLE IF NOT EXISTS [note] (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    data JSON,
    meta JSON,
    access_control JSON,
    created_at BIGINT,
    updated_at BIGINT
);