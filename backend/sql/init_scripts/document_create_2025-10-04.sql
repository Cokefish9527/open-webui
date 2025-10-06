-- 表 document 的结构
CREATE TABLE IF NOT EXISTS [document] (
    id INTEGER NOT NULL PRIMARY KEY,
    collection_name VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    content TEXT,
    user_id VARCHAR(255) NOT NULL,
    timestamp INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS document_name ON [document] (name);
CREATE UNIQUE INDEX IF NOT EXISTS document_collection_name ON [document] (collection_name);