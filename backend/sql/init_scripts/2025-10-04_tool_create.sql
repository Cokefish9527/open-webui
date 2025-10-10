-- 表 tool 的结构
CREATE TABLE IF NOT EXISTS [tool] (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    specs TEXT NOT NULL,
    meta TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    valves TEXT,
    access_control JSON
);
CREATE UNIQUE INDEX IF NOT EXISTS tool_id ON [tool] (id);