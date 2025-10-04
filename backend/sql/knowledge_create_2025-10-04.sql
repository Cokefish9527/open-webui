-- 表 knowledge 的结构
CREATE TABLE IF NOT EXISTS [knowledge] (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    data JSON,
    meta JSON,
    created_at BIGINT NOT NULL,
    updated_at BIGINT,
    access_control JSON
);