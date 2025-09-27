-- 添加用户信息收集完成标志位字段
-- 该脚本用于向现有的user表添加info_collection_completed字段

-- 对于支持直接添加字段的数据库（如PostgreSQL、MySQL等）
-- ALTER TABLE "user" ADD COLUMN info_collection_completed BOOLEAN DEFAULT FALSE;

-- 对于SQLite数据库，需要使用以下步骤：
-- 1. 添加字段（SQLite不支持直接添加带默认值的布尔字段）
ALTER TABLE "user" ADD COLUMN info_collection_completed INTEGER DEFAULT 0;

-- 2. 更新现有记录的默认值（如果需要）
UPDATE "user" SET info_collection_completed = 0 WHERE info_collection_completed IS NULL;

-- 3. 添加检查约束（可选，如果数据库支持）
-- ALTER TABLE "user" ADD CONSTRAINT chk_info_collection_completed CHECK (info_collection_completed IN (0, 1));