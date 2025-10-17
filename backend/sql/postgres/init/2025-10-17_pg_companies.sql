-- PostgreSQL 初始化：companies
-- 约定：与 ORM 模型一致，时间戳使用 BIGINT（秒），JSON 使用 JSON 类型

CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    owner_user_id VARCHAR NOT NULL,
    company_info JSON,
    status VARCHAR NOT NULL DEFAULT 'active',
    config JSON,
    created_at BIGINT,
    updated_at BIGINT
);

CREATE INDEX IF NOT EXISTS ix_companies_owner_user_id ON companies (owner_user_id);
CREATE INDEX IF NOT EXISTS ix_companies_status ON companies (status);

