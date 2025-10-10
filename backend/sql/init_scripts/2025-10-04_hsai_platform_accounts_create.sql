-- 表 hsai_platform_accounts 的结构
CREATE TABLE IF NOT EXISTS [hsai_platform_accounts] (
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
    config JSON,
    permissions JSON,
    status VARCHAR,
    last_sync_at BIGINT,
    follower_count BIGINT,
    following_count BIGINT,
    posts_count BIGINT,
    tags JSON,
    group_id VARCHAR,
    created_at BIGINT,
    updated_at BIGINT,
    FOREIGN KEY (group_id) REFERENCES hsai_account_groups(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_platform_accounts_platform_type ON [hsai_platform_accounts] (platform_type);
CREATE INDEX IF NOT EXISTS ix_hsai_platform_accounts_status ON [hsai_platform_accounts] (status);
CREATE INDEX IF NOT EXISTS ix_hsai_platform_accounts_group_id ON [hsai_platform_accounts] (group_id);
CREATE INDEX IF NOT EXISTS ix_hsai_platform_accounts_user_id ON [hsai_platform_accounts] (user_id);