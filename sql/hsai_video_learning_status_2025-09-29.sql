-- HSAI视频学习状态表创建脚本
-- 表名: hsai_video_learning_status
-- 创建时间: 2025-09-29

CREATE TABLE IF NOT EXISTS hsai_video_learning_status (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,    -- 自增主键
    business_name TEXT NOT NULL,             -- 公司名称
    video_id TEXT NOT NULL,                  -- 学习的视频ID
    status TEXT NOT NULL,                    -- 学习状态: 学习中、已学习、已放弃
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP   -- 更新时间
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_hsai_video_learning_status_video_id 
ON hsai_video_learning_status(video_id);

CREATE INDEX IF NOT EXISTS idx_hsai_video_learning_status_business_video 
ON hsai_video_learning_status(business_name, video_id);

-- 插入一些示例数据（可选）
-- INSERT INTO hsai_video_learning_status (business_name, video_id, status) 
-- VALUES ('示例公司', 'video_001', '学习中');

-- INSERT INTO hsai_video_learning_status (business_name, video_id, status) 
-- VALUES ('示例公司', 'video_002', '已学习');

-- INSERT INTO hsai_video_learning_status (business_name, video_id, status) 
-- VALUES ('示例公司', 'video_003', '已放弃');