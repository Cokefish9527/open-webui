-- 表 hsai_analytics 的结构
CREATE TABLE IF NOT EXISTS [hsai_analytics] (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    dimension_type VARCHAR NOT NULL,
    dimension_value VARCHAR NOT NULL,
    date VARCHAR NOT NULL,
    period_type VARCHAR NOT NULL,
    metrics JSON NOT NULL,
    previous_metrics JSON,
    growth_rate JSON,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_analytics_user_id ON [hsai_analytics] (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_analytics_period ON [hsai_analytics] (period_type);
CREATE INDEX IF NOT EXISTS ix_hsai_analytics_date ON [hsai_analytics] (date);
CREATE INDEX IF NOT EXISTS ix_hsai_analytics_dimension ON [hsai_analytics] (dimension_type, dimension_value);