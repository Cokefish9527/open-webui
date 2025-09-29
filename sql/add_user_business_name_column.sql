-- 添加用户表的business_name字段
ALTER TABLE "user" ADD COLUMN business_name TEXT NULL;

-- 添加注释
COMMENT ON COLUMN "user".business_name IS '用户所属公司名称';

-- 如果需要为现有用户设置默认值，可以使用以下语句：
-- UPDATE "user" SET business_name = 'HSAI' WHERE business_name IS NULL;