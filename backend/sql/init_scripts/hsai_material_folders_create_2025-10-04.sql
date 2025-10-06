-- 表 hsai_material_folders 的结构
CREATE TABLE IF NOT EXISTS [hsai_material_folders] (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    parent_id VARCHAR,
    user_id VARCHAR NOT NULL,
    settings JSON,
    sort_order BIGINT,
    created_at BIGINT,
    updated_at BIGINT,
    FOREIGN KEY (parent_id) REFERENCES hsai_material_folders(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_material_folders_parent_id ON [hsai_material_folders] (parent_id);
CREATE INDEX IF NOT EXISTS ix_hsai_material_folders_user_id ON [hsai_material_folders] (user_id);