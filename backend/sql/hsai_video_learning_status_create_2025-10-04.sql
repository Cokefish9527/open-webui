-- 表 hsai_video_learning_status 的结构
CREATE TABLE IF NOT EXISTS [hsai_video_learning_status] (
    id INTEGER NOT NULL PRIMARY KEY,
    business_name TEXT NOT NULL,
    video_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT DEFAULT 'CURRENT_TIMESTAMP',
    updated_at TEXT DEFAULT 'CURRENT_TIMESTAMP'
);