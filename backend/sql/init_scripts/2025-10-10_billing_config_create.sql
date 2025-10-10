-- 计费配置表结构
CREATE TABLE IF NOT EXISTS [billing_config] (
    id VARCHAR NOT NULL PRIMARY KEY,
    config_type VARCHAR NOT NULL,
    config_key VARCHAR NOT NULL,
    config_value JSON NOT NULL,
    description TEXT,
    is_active VARCHAR DEFAULT '1',
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_billing_config_type ON [billing_config] (config_type);
CREATE INDEX IF NOT EXISTS ix_billing_config_key ON [billing_config] (config_key);
CREATE INDEX IF NOT EXISTS ix_billing_config_active ON [billing_config] (is_active);