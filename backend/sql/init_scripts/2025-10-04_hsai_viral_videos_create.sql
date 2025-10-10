-- 表 hsai_viral_videos 的结构
CREATE TABLE IF NOT EXISTS [hsai_viral_videos] (
    id VARCHAR NOT NULL PRIMARY KEY,
    video_url VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT,
    thumbnail_url VARCHAR,
    duration INTEGER,
    platform VARCHAR NOT NULL,
    tags JSON,
    metadata JSON,
    status VARCHAR NOT NULL,
    is_learned BOOLEAN NOT NULL,
    material_id VARCHAR,
    task_id VARCHAR,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    processed_at BIGINT,
    learned_at BIGINT
);