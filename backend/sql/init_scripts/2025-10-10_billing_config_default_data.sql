-- 插入默认计费配置数据

-- 存储空间计费配置 (2/GB/月)
INSERT OR IGNORE INTO billing_config (id, config_type, config_key, config_value, description, is_active, created_at, updated_at)
VALUES (
    'storage_gb_per_month',
    'resource',
    'storage',
    '{"rate": "2", "unit": "GB/month"}',
    '存储空间计费：2积分/GB/月',
    '1',
    strftime('%s', 'now'),
    strftime('%s', 'now')
);

-- 第三方API调用计费配置 (0.1/次)
INSERT OR IGNORE INTO billing_config (id, config_type, config_key, config_value, description, is_active, created_at, updated_at)
VALUES (
    'api_call_per_request',
    'resource',
    'api_call',
    '{"rate": "0.1", "unit": "per_call"}',
    '第三方API调用计费：0.1积分/次',
    '1',
    strftime('%s', 'now'),
    strftime('%s', 'now')
);