-- PostgreSQL 初始化：hsai_projects

CREATE TABLE IF NOT EXISTS hsai_projects (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    business_name VARCHAR NOT NULL,
    company_info JSON,
    user_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'active',
    config JSON,
    company_id VARCHAR REFERENCES companies(id),
    organization_id VARCHAR,
    created_at BIGINT,
    updated_at BIGINT
);

CREATE INDEX IF NOT EXISTS ix_hsai_projects_user_id ON hsai_projects (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_projects_status ON hsai_projects (status);
CREATE INDEX IF NOT EXISTS ix_hsai_projects_user_status_updated ON hsai_projects (user_id, status, updated_at DESC);
