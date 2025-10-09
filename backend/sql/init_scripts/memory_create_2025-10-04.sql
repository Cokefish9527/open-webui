-- 表 memory 的结构
CREATE TABLE IF NOT EXISTS [memory] (
    id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS memory_id ON [memory] (id);