-- 表 auth 的结构
CREATE TABLE IF NOT EXISTS [auth] (
    id VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password TEXT NOT NULL,
    active INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS auth_id ON [auth] (id);