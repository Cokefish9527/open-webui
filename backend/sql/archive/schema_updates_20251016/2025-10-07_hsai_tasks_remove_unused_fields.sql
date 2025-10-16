-- SQL脚本：移除HSAI任务表中的冗余字段
-- 日期：2025-10-07

-- 从hsai_tasks表中移除以下冗余字段：
-- 1. collaborators - 协作者列表
-- 2. shared_sessions - 共享会话列表
-- 3. inputs - 输入参数
-- 4. outputs - 输出结果
-- 5. error_message - 错误信息
-- 6. retry_count - 重试次数
-- 7. tags - 标签列表

-- 注意：此脚本假设这些字段在当前数据库中存在
-- 如果字段不存在，相应的ALTER TABLE语句将会失败，但不会影响现有数据

BEGIN TRANSACTION;

-- 添加task_category字段（如果不存在）
ALTER TABLE hsai_tasks 
ADD COLUMN IF NOT EXISTS task_category VARCHAR;

-- 移除collaborators字段
ALTER TABLE hsai_tasks 
DROP COLUMN IF EXISTS collaborators;

-- 移除shared_sessions字段
ALTER TABLE hsai_tasks 
DROP COLUMN IF EXISTS shared_sessions;

-- 移除inputs字段
ALTER TABLE hsai_tasks 
DROP COLUMN IF EXISTS inputs;

-- 移除outputs字段
ALTER TABLE hsai_tasks 
DROP COLUMN IF EXISTS outputs;

-- 移除error_message字段
ALTER TABLE hsai_tasks 
DROP COLUMN IF EXISTS error_message;

-- 移除retry_count字段
ALTER TABLE hsai_tasks 
DROP COLUMN IF EXISTS retry_count;

-- 移除tags字段
ALTER TABLE hsai_tasks 
DROP COLUMN IF EXISTS tags;

COMMIT;

-- 验证表结构
-- 可以通过以下查询验证字段是否已成功移除：
-- PRAGMA table_info(hsai_tasks);