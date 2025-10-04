-- 表 model 的结构
CREATE TABLE IF NOT EXISTS [model] (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    base_model_id TEXT,
    name TEXT NOT NULL,
    meta TEXT NOT NULL,
    params TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    access_control JSON,
    is_active BOOLEAN NOT NULL DEFAULT '1',
    price JSON
);
CREATE UNIQUE INDEX IF NOT EXISTS model_id ON [model] (id);