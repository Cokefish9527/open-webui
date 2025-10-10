-- 表 function 的结构
CREATE TABLE IF NOT EXISTS [function] (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    meta TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    valves TEXT,
    is_active INTEGER NOT NULL,
    is_global INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS function_id ON [function] (id);