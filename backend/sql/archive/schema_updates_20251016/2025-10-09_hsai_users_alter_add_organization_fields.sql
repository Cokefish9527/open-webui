-- 扩展用户表结构，添加组织关联和权限字段
ALTER TABLE user ADD COLUMN organization_id VARCHAR(255) REFERENCES organizations(id);
ALTER TABLE user ADD COLUMN is_super_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE user ADD COLUMN is_org_admin BOOLEAN DEFAULT FALSE;