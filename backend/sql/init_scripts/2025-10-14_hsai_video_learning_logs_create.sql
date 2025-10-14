-- 表 hsai_video_learning_logs 的结构
CREATE TABLE IF NOT EXISTS [hsai_video_learning_logs] (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    business_name TEXT NOT NULL,
    video_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    change_reason TEXT,
    changed_by TEXT,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);