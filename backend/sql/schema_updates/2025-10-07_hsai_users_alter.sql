-- 扩展用户表结构，添加公司关联字段
ALTER TABLE user 
ADD COLUMN company_id VARCHAR(255) REFERENCES companies(id);