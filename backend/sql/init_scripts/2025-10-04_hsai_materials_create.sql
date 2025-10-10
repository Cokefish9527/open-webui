-- 表 hsai_materials 的结构
CREATE TABLE IF NOT EXISTS [hsai_materials] (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    material_type VARCHAR NOT NULL,
    folder_id VARCHAR,
    user_id VARCHAR NOT NULL,
    file_path VARCHAR,
    file_size BIGINT,
    file_hash VARCHAR,
    mime_type VARCHAR,
    material_metadata JSON,
    tags JSON,
    ai_analysis JSON,
    usage_count BIGINT,
    last_used_at BIGINT,
    status VARCHAR,
    access_control JSON,
    created_at BIGINT,
    updated_at BIGINT,
    scene_code VARCHAR,
    technique_code VARCHAR,
    properties_code VARCHAR,
    duration INTEGER,
    resolution VARCHAR,
    oss_bucket VARCHAR,
    oss_key VARCHAR,
    is_deleted BOOLEAN,
    original_directory VARCHAR,
    deleted_at BIGINT,
    deleted_by VARCHAR,
    FOREIGN KEY (folder_id) REFERENCES hsai_material_folders(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_materials_folder_id ON [hsai_materials] (folder_id);
CREATE INDEX IF NOT EXISTS ix_hsai_materials_status ON [hsai_materials] (status);
CREATE INDEX IF NOT EXISTS ix_hsai_materials_user_id ON [hsai_materials] (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_materials_type ON [hsai_materials] (material_type);