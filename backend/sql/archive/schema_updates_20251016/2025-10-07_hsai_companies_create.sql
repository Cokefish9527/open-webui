-- HSAI公司表结构
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    owner_user_id VARCHAR NOT NULL,
    company_info JSON,
    status VARCHAR DEFAULT 'active',
    config JSON,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_companies_owner_user_id ON companies (owner_user_id);
CREATE INDEX IF NOT EXISTS ix_companies_status ON companies (status);