-- 扩展项目表结构，添加公司关联字段
ALTER TABLE hsai_projects 
ADD COLUMN company_id VARCHAR(255) REFERENCES companies(id);