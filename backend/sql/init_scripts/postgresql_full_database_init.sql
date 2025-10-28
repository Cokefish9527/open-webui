-- 完整数据库初始化脚本 (PostgreSQL版本)
-- 创建时间: 2025-10-04
-- 包含 41 个表和 0 个视图

-- 表 migratehistory 的结构
CREATE TABLE IF NOT EXISTS migratehistory (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    migrated_at TIMESTAMP NOT NULL
);

-- 表 chatidtag 的结构
CREATE TABLE IF NOT EXISTS chatidtag (
    id VARCHAR(255) NOT NULL,
    tag_name VARCHAR(255) NOT NULL,
    chat_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    timestamp BIGINT NOT NULL,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS chatidtag_id ON chatidtag (id);

-- 表 auth 的结构
CREATE TABLE IF NOT EXISTS auth (
    id VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password TEXT NOT NULL,
    active INTEGER NOT NULL,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS auth_id ON auth (id);

-- 表 chat 的结构
CREATE TABLE IF NOT EXISTS chat (
    id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    share_id VARCHAR(255),
    archived INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    chat JSONB,
    pinned BOOLEAN,
    meta JSONB NOT NULL DEFAULT '{}',
    folder_id TEXT,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS chat_share_id ON chat (share_id);
CREATE UNIQUE INDEX IF NOT EXISTS chat_id ON chat (id);

-- 表 document 的结构
CREATE TABLE IF NOT EXISTS document (
    id SERIAL PRIMARY KEY,
    collection_name VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    content TEXT,
    user_id VARCHAR(255) NOT NULL,
    timestamp BIGINT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS document_name ON document (name);
CREATE UNIQUE INDEX IF NOT EXISTS document_collection_name ON document (collection_name);

-- 表 prompt 的结构
CREATE TABLE IF NOT EXISTS prompt (
    id SERIAL PRIMARY KEY,
    command VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    access_control JSONB
);
CREATE UNIQUE INDEX IF NOT EXISTS prompt_command ON prompt (command);

-- 表 user 的结构
CREATE TABLE IF NOT EXISTS "user" (
    id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    profile_image_url TEXT NOT NULL,
    api_key VARCHAR(255),
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    last_active_at BIGINT NOT NULL,
    settings JSONB,
    info JSONB,
    oauth_sub TEXT,
    info_collection_completed INTEGER DEFAULT 0,
    business_name TEXT,
    company_id VARCHAR(255) REFERENCES companies(id),
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS user_oauth_sub ON "user" (oauth_sub);
CREATE UNIQUE INDEX IF NOT EXISTS user_id ON "user" (id);
CREATE UNIQUE INDEX IF NOT EXISTS user_api_key ON "user" (api_key);
CREATE INDEX IF NOT EXISTS ix_user_company_id ON "user" (company_id);

-- 表 memory 的结构
CREATE TABLE IF NOT EXISTS memory (
    id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    updated_at BIGINT NOT NULL,
    created_at BIGINT NOT NULL,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS memory_id ON memory (id);

-- 表 model 的结构
CREATE TABLE IF NOT EXISTS model (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    base_model_id TEXT,
    name TEXT NOT NULL,
    meta JSONB NOT NULL,
    params JSONB NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    access_control JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    price JSONB,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS model_id ON model (id);

-- 表 tool 的结构
CREATE TABLE IF NOT EXISTS tool (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    specs TEXT NOT NULL,
    meta JSONB NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    valves TEXT,
    access_control JSONB,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS tool_id ON tool (id);

-- 表 function 的结构
CREATE TABLE IF NOT EXISTS function (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    meta JSONB NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    valves TEXT,
    is_active INTEGER NOT NULL,
    is_global INTEGER NOT NULL,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS function_id ON function (id);

-- 表 alembic_version 的结构
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);

-- 表 config 的结构
CREATE TABLE IF NOT EXISTS config (
    id SERIAL PRIMARY KEY,
    data JSONB NOT NULL,
    version INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 表 knowledge 的结构
CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    data JSONB,
    meta JSONB,
    created_at BIGINT NOT NULL,
    updated_at BIGINT,
    access_control JSONB
);

-- 表 tag 的结构
CREATE TABLE IF NOT EXISTS tag (
    id VARCHAR(255) NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    meta JSONB
);

-- 表 file 的结构
CREATE TABLE IF NOT EXISTS file (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    meta JSONB,
    created_at BIGINT NOT NULL,
    hash TEXT,
    data JSONB,
    updated_at BIGINT,
    path TEXT,
    access_control JSONB,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS file_id ON file (id);

-- 表 feedback 的结构
CREATE TABLE IF NOT EXISTS feedback (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    version BIGINT,
    type TEXT,
    data JSONB,
    meta JSONB,
    snapshot JSONB,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);

-- 表 folder 的结构
CREATE TABLE IF NOT EXISTS folder (
    id TEXT NOT NULL PRIMARY KEY,
    parent_id TEXT,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    items JSONB,
    meta JSONB,
    is_expanded BOOLEAN NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);

-- 表 group 的结构
CREATE TABLE IF NOT EXISTS "group" (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    name TEXT,
    description TEXT,
    data JSONB,
    meta JSONB,
    permissions JSONB,
    user_ids JSONB,
    created_at BIGINT,
    updated_at BIGINT
);

-- 表 channel 的结构
CREATE TABLE IF NOT EXISTS channel (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    name TEXT,
    description TEXT,
    data JSONB,
    meta JSONB,
    access_control JSONB,
    created_at BIGINT,
    updated_at BIGINT,
    type TEXT
);

-- 表 message 的结构
CREATE TABLE IF NOT EXISTS message (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    channel_id TEXT,
    content TEXT,
    data JSONB,
    meta JSONB,
    created_at BIGINT,
    updated_at BIGINT,
    parent_id TEXT
);

-- 表 message_reaction 的结构
CREATE TABLE IF NOT EXISTS message_reaction (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at BIGINT
);

-- 表 channel_member 的结构
CREATE TABLE IF NOT EXISTS channel_member (
    id TEXT NOT NULL PRIMARY KEY,
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at BIGINT
);

-- 表 credit 的结构
CREATE TABLE IF NOT EXISTS credit (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    credit NUMERIC(24, 12),
    updated_at BIGINT,
    created_at BIGINT
);

-- 表 credit_log 的结构
CREATE TABLE IF NOT EXISTS credit_log (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    credit NUMERIC(24, 12),
    detail JSONB,
    created_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_credit_log_created_at ON credit_log (created_at);
CREATE INDEX IF NOT EXISTS ix_credit_log_user_id ON credit_log (user_id);

-- 表 trade_ticket 的结构
CREATE TABLE IF NOT EXISTS trade_ticket (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    amount NUMERIC(24, 12),
    detail JSONB,
    created_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_trade_ticket_created_at ON trade_ticket (created_at);
CREATE INDEX IF NOT EXISTS ix_trade_ticket_user_id ON trade_ticket (user_id);

-- 表 note 的结构
CREATE TABLE IF NOT EXISTS note (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    data JSONB,
    meta JSONB,
    access_control JSONB,
    created_at BIGINT,
    updated_at BIGINT
);

-- 表 hsai_material_folders 的结构
CREATE TABLE IF NOT EXISTS hsai_material_folders (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    parent_id VARCHAR,
    user_id VARCHAR NOT NULL,
    settings JSONB,
    sort_order BIGINT,
    created_at BIGINT,
    updated_at BIGINT,
    FOREIGN KEY (parent_id) REFERENCES hsai_material_folders(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_material_folders_parent_id ON hsai_material_folders (parent_id);
CREATE INDEX IF NOT EXISTS ix_hsai_material_folders_user_id ON hsai_material_folders (user_id);

-- 表 hsai_materials 的结构
CREATE TABLE IF NOT EXISTS hsai_materials (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    material_type VARCHAR NOT NULL,
    folder_id VARCHAR,
    user_id VARCHAR NOT NULL,
    file_path VARCHAR,
    file_size BIGINT,
    file_hash VARCHAR,
    mime_type VARCHAR,
    material_metadata JSONB,
    tags JSONB,
    ai_analysis JSONB,
    usage_count BIGINT,
    last_used_at BIGINT,
    status VARCHAR,
    access_control JSONB,
    created_at BIGINT,
    updated_at BIGINT,
    scene_code VARCHAR,
    technique_code VARCHAR,
    properties_code VARCHAR,
    duration INTEGER,
    resolution VARCHAR,
    oss_bucket VARCHAR,
    oss_key VARCHAR,
    is_deleted BOOLEAN,
    original_directory VARCHAR,
    deleted_at BIGINT,
    deleted_by VARCHAR,
    FOREIGN KEY (folder_id) REFERENCES hsai_material_folders(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_materials_folder_id ON hsai_materials (folder_id);
CREATE INDEX IF NOT EXISTS ix_hsai_materials_status ON hsai_materials (status);
CREATE INDEX IF NOT EXISTS ix_hsai_materials_user_id ON hsai_materials (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_materials_type ON hsai_materials (material_type);

-- 表 hsai_material_tags 的结构
CREATE TABLE IF NOT EXISTS hsai_material_tags (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    color VARCHAR,
    category VARCHAR,
    user_id VARCHAR NOT NULL,
    usage_count BIGINT,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_material_tags_user_id ON hsai_material_tags (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_material_tags_name ON hsai_material_tags (name);

-- 表 hsai_workflows 的结构
CREATE TABLE IF NOT EXISTS hsai_workflows (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    user_id VARCHAR NOT NULL,
    definition JSONB NOT NULL,
    variables JSONB,
    status VARCHAR,
    version VARCHAR,
    execution_count BIGINT,
    last_executed_at BIGINT,
    category VARCHAR,
    tags JSONB,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_workflows_category ON hsai_workflows (category);
CREATE INDEX IF NOT EXISTS ix_hsai_workflows_status ON hsai_workflows (status);
CREATE INDEX IF NOT EXISTS ix_hsai_workflows_user_id ON hsai_workflows (user_id);

-- 表 hsai_cards 的结构
CREATE TABLE IF NOT EXISTS hsai_cards (
    id VARCHAR NOT NULL PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT,
    card_type VARCHAR NOT NULL,
    status VARCHAR,
    user_id VARCHAR NOT NULL,
    chat_id VARCHAR,
    task_id VARCHAR,
    content JSONB,
    config JSONB,
    actions JSONB,
    position JSONB,
    style JSONB,
    is_pinned BOOLEAN,
    is_collapsed BOOLEAN,
    sort_order BIGINT,
    created_at BIGINT,
    updated_at BIGINT,
    FOREIGN KEY (task_id) REFERENCES hsai_tasks(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_cards_type ON hsai_cards (card_type);
CREATE INDEX IF NOT EXISTS ix_hsai_cards_user_id ON hsai_cards (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_cards_chat_id ON hsai_cards (chat_id);
CREATE INDEX IF NOT EXISTS ix_hsai_cards_status ON hsai_cards (status);

-- 表 hsai_workflow_executions 的结构
CREATE TABLE IF NOT EXISTS hsai_workflow_executions (
    id VARCHAR NOT NULL PRIMARY KEY,
    workflow_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    trigger_task_id VARCHAR,
    status VARCHAR,
    progress BIGINT,
    inputs JSONB,
    outputs JSONB,
    execution_log JSONB,
    started_at BIGINT,
    completed_at BIGINT,
    error_message TEXT,
    created_at BIGINT,
    updated_at BIGINT,
    FOREIGN KEY (trigger_task_id) REFERENCES hsai_tasks(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (workflow_id) REFERENCES hsai_workflows(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_workflow_executions_user_id ON hsai_workflow_executions (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_workflow_executions_status ON hsai_workflow_executions (status);
CREATE INDEX IF NOT EXISTS ix_hsai_workflow_executions_workflow_id ON hsai_workflow_executions (workflow_id);

-- 表 hsai_account_groups 的结构
CREATE TABLE IF NOT EXISTS hsai_account_groups (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    color VARCHAR,
    user_id VARCHAR NOT NULL,
    config JSONB,
    sort_order BIGINT,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_account_groups_user_id ON hsai_account_groups (user_id);

-- 表 hsai_platform_accounts 的结构
CREATE TABLE IF NOT EXISTS hsai_platform_accounts (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    platform_type VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    platform_account_id VARCHAR NOT NULL,
    username VARCHAR NOT NULL,
    display_name VARCHAR,
    avatar_url VARCHAR,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at BIGINT,
    config JSONB,
    permissions JSONB,
    status VARCHAR,
    last_sync_at BIGINT,
    follower_count BIGINT,
    following_count BIGINT,
    posts_count BIGINT,
    tags JSONB,
    group_id VARCHAR,
    created_at BIGINT,
    updated_at BIGINT,
    FOREIGN KEY (group_id) REFERENCES hsai_account_groups(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_platform_accounts_platform_type ON hsai_platform_accounts (platform_type);
CREATE INDEX IF NOT EXISTS ix_hsai_platform_accounts_status ON hsai_platform_accounts (status);
CREATE INDEX IF NOT EXISTS ix_hsai_platform_accounts_group_id ON hsai_platform_accounts (group_id);
CREATE INDEX IF NOT EXISTS ix_hsai_platform_accounts_user_id ON hsai_platform_accounts (user_id);

-- 表 hsai_publish_tasks 的结构
CREATE TABLE IF NOT EXISTS hsai_publish_tasks (
    id VARCHAR NOT NULL PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT,
    user_id VARCHAR NOT NULL,
    hsai_task_id VARCHAR,
    content JSONB NOT NULL,
    content_type VARCHAR NOT NULL,
    platforms JSONB NOT NULL,
    publish_config JSONB,
    status VARCHAR,
    progress BIGINT,
    scheduled_at BIGINT,
    published_at BIGINT,
    error_message TEXT,
    retry_count BIGINT,
    tags JSONB,
    priority BIGINT,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_tasks_user_id ON hsai_publish_tasks (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_tasks_status ON hsai_publish_tasks (status);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_tasks_priority ON hsai_publish_tasks (priority);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_tasks_scheduled_at ON hsai_publish_tasks (scheduled_at);

-- 表 hsai_publish_records 的结构
CREATE TABLE IF NOT EXISTS hsai_publish_records (
    id VARCHAR NOT NULL PRIMARY KEY,
    publish_task_id VARCHAR NOT NULL,
    platform_account_id VARCHAR NOT NULL,
    platform_post_id VARCHAR,
    platform_url VARCHAR,
    status VARCHAR NOT NULL,
    error_message TEXT,
    publish_data JSONB,
    response_data JSONB,
    views BIGINT,
    likes BIGINT,
    comments BIGINT,
    shares BIGINT,
    published_at BIGINT,
    last_stats_update_at BIGINT,
    created_at BIGINT,
    updated_at BIGINT,
    FOREIGN KEY (platform_account_id) REFERENCES hsai_platform_accounts(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (publish_task_id) REFERENCES hsai_publish_tasks(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_records_status ON hsai_publish_records (status);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_records_account_id ON hsai_publish_records (platform_account_id);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_records_task_id ON hsai_publish_records (publish_task_id);
CREATE INDEX IF NOT EXISTS ix_hsai_publish_records_published_at ON hsai_publish_records (published_at);

-- 表 hsai_analytics 的结构
CREATE TABLE IF NOT EXISTS hsai_analytics (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    dimension_type VARCHAR NOT NULL,
    dimension_value VARCHAR NOT NULL,
    date VARCHAR NOT NULL,
    period_type VARCHAR NOT NULL,
    metrics JSONB NOT NULL,
    previous_metrics JSONB,
    growth_rate JSONB,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_analytics_user_id ON hsai_analytics (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_analytics_period ON hsai_analytics (period_type);
CREATE INDEX IF NOT EXISTS ix_hsai_analytics_date ON hsai_analytics (date);
CREATE INDEX IF NOT EXISTS ix_hsai_analytics_dimension ON hsai_analytics (dimension_type, dimension_value);

-- 表 hsai_viral_videos 的结构
CREATE TABLE IF NOT EXISTS hsai_viral_videos (
    id VARCHAR NOT NULL PRIMARY KEY,
    video_url VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT,
    thumbnail_url VARCHAR,
    duration INTEGER,
    platform VARCHAR NOT NULL,
    tags JSONB,
    metadata JSONB,
    status VARCHAR NOT NULL,
    is_learned BOOLEAN NOT NULL,
    material_id VARCHAR,
    task_id VARCHAR,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    processed_at BIGINT,
    learned_at BIGINT
);

-- 表 hsai_tasks 的结构
CREATE TABLE IF NOT EXISTS hsai_tasks (
    id VARCHAR NOT NULL PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT,
    task_type VARCHAR NOT NULL,
    task_category VARCHAR,
    status VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    chat_id VARCHAR,
    config JSONB,
    inputs JSONB,
    outputs JSONB,
    workflow_id VARCHAR,
    parent_task_id VARCHAR,
    progress BIGINT NOT NULL,
    started_at BIGINT,
    completed_at BIGINT,
    error_message TEXT,
    retry_count BIGINT NOT NULL,
    priority BIGINT,
    tags JSONB,
    created_at BIGINT,
    updated_at BIGINT,
    assignee_id VARCHAR,
    collaborators JSONB,
    shared_sessions JSONB,
    project_id VARCHAR REFERENCES hsai_projects(id),
    prompt_config JSONB,
    FOREIGN KEY (workflow_id) REFERENCES hsai_workflows(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (parent_task_id) REFERENCES hsai_tasks(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (project_id) REFERENCES hsai_projects(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_assignee_id ON hsai_tasks (assignee_id);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_type ON hsai_tasks (task_type);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_status ON hsai_tasks (status);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_user_id ON hsai_tasks (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_chat_id ON hsai_tasks (chat_id);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_priority ON hsai_tasks (priority);

-- 表 hsai_video_learning_status 的结构
CREATE TABLE IF NOT EXISTS hsai_video_learning_status (
    id SERIAL PRIMARY KEY,
    business_name TEXT NOT NULL,
    video_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 表 hsai_video_learning_logs 的结构
CREATE TABLE IF NOT EXISTS hsai_video_learning_logs (
    id SERIAL PRIMARY KEY,
    business_name TEXT NOT NULL,
    video_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    change_reason TEXT,
    changed_by TEXT,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);

-- 表 hsai_projects 的结构
CREATE TABLE IF NOT EXISTS hsai_projects (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    business_name VARCHAR NOT NULL,
    company_info JSONB,
    user_id VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'active',
    config JSONB,
    company_id VARCHAR REFERENCES companies(id),
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_hsai_projects_user_id ON hsai_projects (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_projects_status ON hsai_projects (status);
CREATE INDEX IF NOT EXISTS ix_hsai_projects_company_id ON hsai_projects (company_id);

-- 表 companies 的结构
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    owner_user_id VARCHAR NOT NULL,
    company_info JSONB,
    status VARCHAR DEFAULT 'active',
    config JSONB,
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_companies_owner_user_id ON companies (owner_user_id);
CREATE INDEX IF NOT EXISTS ix_companies_status ON companies (status);

-- 表 hsai_business_api_usage_log 的结构
CREATE TABLE IF NOT EXISTS hsai_business_api_usage_log (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    service_provider VARCHAR(100) NOT NULL,
    model_name VARCHAR(100),
    credits_consumed NUMERIC(12, 6) NOT NULL DEFAULT 0,
    consumed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_user_id ON hsai_business_api_usage_log (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_session_id ON hsai_business_api_usage_log (session_id);
CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_service_provider ON hsai_business_api_usage_log (service_provider);
CREATE INDEX IF NOT EXISTS ix_hsai_business_api_usage_log_consumed_at ON hsai_business_api_usage_log (consumed_at);

-- 表 billing_config 的结构
CREATE TABLE IF NOT EXISTS billing_config (
    id VARCHAR NOT NULL PRIMARY KEY,
    config_type VARCHAR NOT NULL,
    config_key VARCHAR NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    is_active VARCHAR DEFAULT '1',
    created_at BIGINT,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_billing_config_type ON billing_config (config_type);
CREATE INDEX IF NOT EXISTS ix_billing_config_key ON billing_config (config_key);
CREATE INDEX IF NOT EXISTS ix_billing_config_active ON billing_config (is_active);

-- 表 social_accounts 的结构 (2025-10-24)
CREATE TABLE IF NOT EXISTS social_accounts (
    id VARCHAR NOT NULL PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    platform VARCHAR NOT NULL,
    handle VARCHAR NOT NULL,
    display_name VARCHAR,
    encrypted_credentials_ref VARCHAR NOT NULL,
    playwright_profile_path VARCHAR NOT NULL,
    vpn_profile_id VARCHAR NOT NULL,
    device_fingerprint_hash VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'inactive',
    health_status VARCHAR DEFAULT 'unknown',
    last_rotation_at BIGINT,
    created_by VARCHAR NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_social_accounts_tenant_platform_handle
    ON social_accounts (tenant_id, platform, handle);
CREATE INDEX IF NOT EXISTS ix_social_accounts_status
    ON social_accounts (status);
CREATE INDEX IF NOT EXISTS ix_social_accounts_tenant
    ON social_accounts (tenant_id);

-- 表 social_campaigns 的结构 (2025-10-24)
CREATE TABLE IF NOT EXISTS social_campaigns (
    id VARCHAR NOT NULL PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    schedule_strategy VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'draft',
    created_by VARCHAR NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_social_campaigns_tenant
    ON social_campaigns (tenant_id);
CREATE INDEX IF NOT EXISTS ix_social_campaigns_status
    ON social_campaigns (status);

-- 表 social_posts 的结构 (2025-10-24)
CREATE TABLE IF NOT EXISTS social_posts (
    id VARCHAR NOT NULL PRIMARY KEY,
    campaign_id VARCHAR,
    account_id VARCHAR NOT NULL,
    title VARCHAR,
    caption TEXT,
    media_assets JSON,
    metadata JSON,
    schedule_time BIGINT,
    status VARCHAR NOT NULL DEFAULT 'draft',
    approval_user_id VARCHAR,
    approval_time BIGINT,
    created_by VARCHAR NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT,
    FOREIGN KEY (campaign_id) REFERENCES social_campaigns (id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES social_accounts (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_social_posts_account
    ON social_posts (account_id);
CREATE INDEX IF NOT EXISTS ix_social_posts_campaign
    ON social_posts (campaign_id);
CREATE INDEX IF NOT EXISTS ix_social_posts_status
    ON social_posts (status);
CREATE INDEX IF NOT EXISTS ix_social_posts_schedule_time
    ON social_posts (schedule_time);

-- 表 social_automation_runs 的结构 (2025-10-24)
CREATE TABLE IF NOT EXISTS social_automation_runs (
    id VARCHAR NOT NULL PRIMARY KEY,
    post_id VARCHAR,
    trigger_source VARCHAR NOT NULL,
    mcp_request_id VARCHAR,
    status VARCHAR NOT NULL,
    result_payload JSON,
    screenshot_path VARCHAR,
    har_path VARCHAR,
    proxy_exit_ip VARCHAR,
    duration_ms BIGINT,
    error_reason TEXT,
    created_at BIGINT NOT NULL,
    updated_at BIGINT,
    FOREIGN KEY (post_id) REFERENCES social_posts (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_social_automation_runs_post
    ON social_automation_runs (post_id);
CREATE INDEX IF NOT EXISTS ix_social_automation_runs_status
    ON social_automation_runs (status);
