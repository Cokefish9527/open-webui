-- 创建Owen_ai数据库
CREATE DATABASE Owen_ai;

-- 连接到Owen_ai数据库
\c Owen_ai;

-- 执行完整数据库初始化脚本
\i 2025-10-04_full_database_init.sql;