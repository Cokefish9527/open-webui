-- HSAI项目表结构
CREATE TABLE IF NOT EXISTS [hsai_projects] (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    business_name VARCHAR NOT NULL,
    company_info JSON,
    user_id VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'active',
    config JSON,
    company_id VARCHAR(255) REFERENCES companies(id),
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_projects_user_id ON [hsai_projects] (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_projects_status ON [hsai_projects] (status);