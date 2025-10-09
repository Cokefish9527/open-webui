-- 表 user 的结构
CREATE TABLE IF NOT EXISTS [user] (
    id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    profile_image_url TEXT NOT NULL,
    api_key VARCHAR(255),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    last_active_at INTEGER NOT NULL,
    settings TEXT,
    info TEXT,
    oauth_sub TEXT,
    info_collection_completed INTEGER DEFAULT '0',
    business_name TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS user_oauth_sub ON [user] (oauth_sub);
CREATE UNIQUE INDEX IF NOT EXISTS user_id ON [user] (id);
CREATE UNIQUE INDEX IF NOT EXISTS user_api_key ON [user] (api_key);