-- 为 hsai_projects 增加 organization_id 字段（PostgreSQL）

ALTER TABLE hsai_projects
ADD COLUMN IF NOT EXISTS organization_id VARCHAR;

