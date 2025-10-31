# 计费管理API接口分析报告

## 1. 接口概览
- 总计费接口数: 10

## 2. 接口详情

### billing

| 路径 | 方法 | 操作ID | 摘要 |
|------|------|--------|------|
| /api/v1/billing/billing/user/credit | GET | get_user_company_credit_api_v1_billing_billing_user_credit_get | 获取用户所属公司的积分余额 |
| /api/v1/billing/billing/configs | GET | get_billing_configs_api_v1_billing_billing_configs_get | 获取计费配置列表 |
| /api/v1/billing/billing/configs | POST | create_billing_config_api_v1_billing_billing_configs_post | 创建计费配置 |
| /api/v1/billing/billing/configs/{config_id} | GET | get_billing_config_api_v1_billing_billing_configs__config_id__get | 获取计费配置详情 |
| /api/v1/billing/billing/configs/{config_id} | PUT | update_billing_config_api_v1_billing_billing_configs__config_id__put | 更新计费配置 |
| /api/v1/billing/billing/configs/{config_id} | DELETE | delete_billing_config_api_v1_billing_billing_configs__config_id__delete | 删除计费配置 |
| /api/v1/billing/billing/usage-logs | GET | get_api_usage_logs_api_v1_billing_billing_usage_logs_get | 获取API使用记录列表 |
| /api/v1/billing/billing/usage-logs | POST | create_api_usage_log_api_v1_billing_billing_usage_logs_post | 创建API使用记录 |
| /api/v1/billing/billing/usage-logs/session/{session_id} | GET | get_api_usage_logs_by_session_api_v1_billing_billing_usage_logs_session__session_id__get | 根据会话ID获取API使用记录 |
| /api/v1/billing/billing/usage-logs/session/{session_id}/total | GET | get_total_credits_consumed_by_session_api_v1_billing_billing_usage_logs_session__session_id__total_get | 根据会话ID获取总消耗积分 |

### 计费管理

| 路径 | 方法 | 操作ID | 摘要 |
|------|------|--------|------|
| /api/v1/billing/billing/user/credit | GET | get_user_company_credit_api_v1_billing_billing_user_credit_get | 获取用户所属公司的积分余额 |
| /api/v1/billing/billing/configs | GET | get_billing_configs_api_v1_billing_billing_configs_get | 获取计费配置列表 |
| /api/v1/billing/billing/configs | POST | create_billing_config_api_v1_billing_billing_configs_post | 创建计费配置 |
| /api/v1/billing/billing/configs/{config_id} | GET | get_billing_config_api_v1_billing_billing_configs__config_id__get | 获取计费配置详情 |
| /api/v1/billing/billing/configs/{config_id} | PUT | update_billing_config_api_v1_billing_billing_configs__config_id__put | 更新计费配置 |
| /api/v1/billing/billing/configs/{config_id} | DELETE | delete_billing_config_api_v1_billing_billing_configs__config_id__delete | 删除计费配置 |
| /api/v1/billing/billing/usage-logs | GET | get_api_usage_logs_api_v1_billing_billing_usage_logs_get | 获取API使用记录列表 |
| /api/v1/billing/billing/usage-logs | POST | create_api_usage_log_api_v1_billing_billing_usage_logs_post | 创建API使用记录 |
| /api/v1/billing/billing/usage-logs/session/{session_id} | GET | get_api_usage_logs_by_session_api_v1_billing_billing_usage_logs_session__session_id__get | 根据会话ID获取API使用记录 |
| /api/v1/billing/billing/usage-logs/session/{session_id}/total | GET | get_total_credits_consumed_by_session_api_v1_billing_billing_usage_logs_session__session_id__total_get | 根据会话ID获取总消耗积分 |

