-- 表 chat 的结构
CREATE TABLE IF NOT EXISTS [chat] (
    id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    share_id VARCHAR(255),
    archived INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    chat JSON,
    pinned BOOLEAN,
    meta JSON NOT NULL DEFAULT ''{}'',
    folder_id TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS chat_share_id ON [chat] (share_id);
CREATE UNIQUE INDEX IF NOT EXISTS chat_id ON [chat] (id);