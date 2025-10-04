-- 表 trade_ticket 的结构
CREATE TABLE IF NOT EXISTS [trade_ticket] (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    amount NUMERIC(24, 12),
    detail JSON,
    created_at BIGINT
);
CREATE INDEX IF NOT EXISTS ix_trade_ticket_created_at ON [trade_ticket] (created_at);
CREATE INDEX IF NOT EXISTS ix_trade_ticket_user_id ON [trade_ticket] (user_id);