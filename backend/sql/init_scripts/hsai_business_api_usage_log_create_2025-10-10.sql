-- HSAI API使用记录表结构
CREATE TABLE IF NOT EXISTS [hsai_business_api_usage_log] (
    id BIGINT NOT NULL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    service_provider VARCHAR(100) NOT NULL,
    model_name VARCHAR(100),
    credits_consumed NUMERIC(12, 6) NOT NULL DEFAULT 0,
    consumed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_user_id ON [hsai_business_api_usage_log] (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_session_id ON [hsai_business_api_usage_log] (session_id);
CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_service_provider ON [hsai_business_api_usage_log] (service_provider);
CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_consumed_at ON [hsai_business_api_usage_log] (consumed_at);