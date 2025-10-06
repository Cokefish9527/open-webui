-- 表 hsai_material_tags 的结构
CREATE TABLE IF NOT EXISTS [hsai_material_tags] (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    color VARCHAR,
    category VARCHAR,
    user_id VARCHAR NOT NULL,
    usage_count BIGINT,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_material_tags_user_id ON [hsai_material_tags] (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_material_tags_name ON [hsai_material_tags] (name);