-- 为 hsai_projects 增加联合索引 (user_id, organization_id)

CREATE INDEX IF NOT EXISTS ix_hsai_projects_user_org
ON hsai_projects (user_id, organization_id);

