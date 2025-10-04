-- 表 folder 的结构
CREATE TABLE IF NOT EXISTS [folder] (
    id TEXT NOT NULL PRIMARY KEY,
    parent_id TEXT,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    items JSON,
    meta JSON,
    is_expanded BOOLEAN NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);