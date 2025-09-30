-- HSAI视频学习日志表创建脚本
-- 表名: hsai_video_learning_logs
-- 创建时间: 2025-09-30

CREATE TABLE IF NOT EXISTS hsai_video_learning_logs (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,    -- 自增主键
    business_name TEXT NOT NULL,             -- 公司名称
    video_id TEXT NOT NULL,                  -- 学习的视频ID
    from_status TEXT,                        -- 原始状态
    to_status TEXT NOT NULL,                 -- 目标状态
    change_reason TEXT,                      -- 状态变更原因
    changed_by TEXT,                         -- 变更操作人
    created_at INTEGER,                      -- 创建时间戳
    updated_at INTEGER                       -- 更新时间戳
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_hsai_video_learning_logs_video_id 
ON hsai_video_learning_logs(video_id);

CREATE INDEX IF NOT EXISTS idx_hsai_video_learning_logs_business_video 
ON hsai_video_learning_logs(business_name, video_id);

CREATE INDEX IF NOT EXISTS idx_hsai_video_learning_logs_created_at 
ON hsai_video_learning_logs(created_at);