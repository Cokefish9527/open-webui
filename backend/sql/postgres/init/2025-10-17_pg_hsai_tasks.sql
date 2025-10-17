-- PostgreSQL 初始化：hsai_tasks（对齐当前 ORM，移除历史冗余字段）

CREATE TABLE IF NOT EXISTS hsai_tasks (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT,
    task_type VARCHAR NOT NULL,
    task_category VARCHAR,
    status VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    assignee_id VARCHAR,
    chat_id VARCHAR,
    project_id VARCHAR REFERENCES hsai_projects(id),
    config JSON,
    prompt_config JSON,
    workflow_id VARCHAR,
    parent_task_id VARCHAR,
    progress BIGINT DEFAULT 0,
    started_at BIGINT,
    completed_at BIGINT,
    priority BIGINT DEFAULT 0,
    created_at BIGINT,
    updated_at BIGINT
);

-- 覆盖常用查询的索引
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_user_id ON hsai_tasks (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_status ON hsai_tasks (status);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_task_type ON hsai_tasks (task_type);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_chat_id ON hsai_tasks (chat_id);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_assignee_id ON hsai_tasks (assignee_id);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_project_category ON hsai_tasks (project_id, task_category);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_user_status_updated ON hsai_tasks (user_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_hsai_tasks_priority ON hsai_tasks (priority);

