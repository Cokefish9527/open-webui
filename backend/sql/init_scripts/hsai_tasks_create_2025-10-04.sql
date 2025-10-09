-- 表 hsai_tasks 的结构
CREATE TABLE IF NOT EXISTS [hsai_tasks] (
    id VARCHAR NOT NULL PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT,
    task_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    chat_id VARCHAR,
    config JSON,
    inputs JSON,
    outputs JSON,
    workflow_id VARCHAR,
    parent_task_id VARCHAR,
    progress BIGINT NOT NULL,
    started_at BIGINT,
    completed_at BIGINT,
    error_message TEXT,
    retry_count BIGINT NOT NULL,
    priority BIGINT,
    tags JSON,
    created_at BIGINT,
    updated_at BIGINT,
    assignee_id VARCHAR,
    collaborators JSON,
    shared_sessions JSON,
    FOREIGN KEY (workflow_id) REFERENCES hsai_workflows(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (parent_task_id) REFERENCES hsai_tasks(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_assignee_id ON [hsai_tasks] (assignee_id);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_type ON [hsai_tasks] (task_type);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_status ON [hsai_tasks] (status);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_user_id ON [hsai_tasks] (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_chat_id ON [hsai_tasks] (chat_id);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_priority ON [hsai_tasks] (priority);