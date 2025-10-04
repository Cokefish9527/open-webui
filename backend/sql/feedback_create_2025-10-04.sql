-- 表 feedback 的结构
CREATE TABLE IF NOT EXISTS [feedback] (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    version BIGINT,
    type TEXT,
    data JSON,
    meta JSON,
    snapshot JSON,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);