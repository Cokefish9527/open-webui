-- 表 hsai_cards 的结构
CREATE TABLE IF NOT EXISTS [hsai_cards] (
    id VARCHAR NOT NULL PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT,
    card_type VARCHAR NOT NULL,
    status VARCHAR,
    user_id VARCHAR NOT NULL,
    chat_id VARCHAR,
    task_id VARCHAR,
    content JSON,
    config JSON,
    actions JSON,
    position JSON,
    style JSON,
    is_pinned BOOLEAN,
    is_collapsed BOOLEAN,
    sort_order BIGINT,
    created_at BIGINT,
    updated_at BIGINT,
    FOREIGN KEY (task_id) REFERENCES hsai_tasks(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_cards_type ON [hsai_cards] (card_type);
CREATE INDEX IF NOT EXISTS ix_hsai_cards_user_id ON [hsai_cards] (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_cards_chat_id ON [hsai_cards] (chat_id);
CREATE INDEX IF NOT EXISTS ix_hsai_cards_status ON [hsai_cards] (status);