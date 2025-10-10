-- 表 group 的结构
CREATE TABLE IF NOT EXISTS [group] (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    name TEXT,
    description TEXT,
    data JSON,
    meta JSON,
    permissions JSON,
    user_ids JSON,
    created_at BIGINT,
    updated_at BIGINT
);