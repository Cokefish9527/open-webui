-- 扩展用户组表结构，添加组织关联字段
ALTER TABLE "group" ADD COLUMN organization_id VARCHAR(255) REFERENCES organizations(id);

