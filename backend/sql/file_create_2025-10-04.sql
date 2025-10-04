-- 表 file 的结构
CREATE TABLE IF NOT EXISTS [file] (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    meta JSON,
    created_at INTEGER NOT NULL,
    hash TEXT,
    data JSON,
    updated_at BIGINT,
    path TEXT,
    access_control JSON
);
CREATE UNIQUE INDEX IF NOT EXISTS file_id ON [file] (id);