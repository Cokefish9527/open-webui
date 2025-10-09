-- 表 chatidtag 的结构
CREATE TABLE IF NOT EXISTS [chatidtag] (
    id VARCHAR(255) NOT NULL,
    tag_name VARCHAR(255) NOT NULL,
    chat_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    timestamp INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS chatidtag_id ON [chatidtag] (id);