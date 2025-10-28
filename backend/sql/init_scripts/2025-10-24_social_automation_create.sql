-- Social automation core tables created on 2025-10-24

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
