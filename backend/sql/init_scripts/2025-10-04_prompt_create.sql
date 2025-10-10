-- 表 prompt 的结构
CREATE TABLE IF NOT EXISTS [prompt] (
    id INTEGER NOT NULL PRIMARY KEY,
    command VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    access_control JSON
);
CREATE UNIQUE INDEX IF NOT EXISTS prompt_command ON [prompt] (command);