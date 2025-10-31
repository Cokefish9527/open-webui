# 计费管理API接口清单

## 计费管理

| 路径 | 方法 | 操作ID | 摘要 | 描述 |
|------|------|--------|------|------|
| /api/v1/billing/billing/user/credit | GET | get_user_company_credit_api_v1_billing_billing_user_credit_get | 获取用户所属公司的积分余额 | 返回当前登录用户所属公司（若有）的积分余额信息。 |
| /api/v1/billing/billing/configs | GET | get_billing_configs_api_v1_billing_billing_configs_get | 获取计费配置列表 | 获取计费配置列表（分页）。

Args:
    config_type (Optional[str]): 配置类型过滤
    is_active (Optional[bool]): 是否启用过滤
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    user: 已认证的管理员用户对象
    
Returns:
    PaginatedBillingConfigResponse: 分页的计费配置列表 |
| /api/v1/billing/billing/configs | POST | create_billing_config_api_v1_billing_billing_configs_post | 创建计费配置 | 创建新的计费配置。

Args:
    form_data (BillingConfigForm): 计费配置创建表单
    user: 已认证的管理员用户对象
    
Returns:
    BillingConfigResponse: 创建的计费配置信息 |
| /api/v1/billing/billing/configs/{config_id} | GET | get_billing_config_api_v1_billing_billing_configs__config_id__get | 获取计费配置详情 | 获取单个计费配置详情 |
| /api/v1/billing/billing/configs/{config_id} | PUT | update_billing_config_api_v1_billing_billing_configs__config_id__put | 更新计费配置 | 更新计费配置 |
| /api/v1/billing/billing/configs/{config_id} | DELETE | delete_billing_config_api_v1_billing_billing_configs__config_id__delete | 删除计费配置 | 删除计费配置 |
| /api/v1/billing/billing/usage-logs | GET | get_api_usage_logs_api_v1_billing_billing_usage_logs_get | 获取API使用记录列表 | 获取API使用记录列表（分页）。

Args:
    user_id (Optional[str]): 用户ID过滤
    ps (int): 分页大小，范围1-100
    pi (int): 分页索引，从1开始
    user: 已认证的用户对象
    
Returns:
    PaginatedAPIUsageLogResponse: 分页的API使用记录列表 |
| /api/v1/billing/billing/usage-logs | POST | create_api_usage_log_api_v1_billing_billing_usage_logs_post | 创建API使用记录 | 创建新的API使用记录。

Args:
    form_data (APIUsageLogForm): API使用记录创建表单
    user: 已认证的管理员用户对象
    
Returns:
    APIUsageLogResponse: 创建的API使用记录信息 |
| /api/v1/billing/billing/usage-logs/session/{session_id} | GET | get_api_usage_logs_by_session_api_v1_billing_billing_usage_logs_session__session_id__get | 根据会话ID获取API使用记录 | 根据会话ID获取API使用记录 |
| /api/v1/billing/billing/usage-logs/session/{session_id}/total | GET | get_total_credits_consumed_by_session_api_v1_billing_billing_usage_logs_session__session_id__total_get | 根据会话ID获取总消耗积分 | 根据会话ID获取总消耗积分 |