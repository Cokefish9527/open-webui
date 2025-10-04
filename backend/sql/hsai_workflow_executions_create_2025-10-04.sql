-- 表 hsai_workflow_executions 的结构
CREATE TABLE IF NOT EXISTS [hsai_workflow_executions] (
    id VARCHAR NOT NULL PRIMARY KEY,
    workflow_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    trigger_task_id VARCHAR,
    status VARCHAR,
    progress BIGINT,
    inputs JSON,
    outputs JSON,
    execution_log JSON,
    started_at BIGINT,
    completed_at BIGINT,
    error_message TEXT,
    created_at BIGINT,
    updated_at BIGINT,
    FOREIGN KEY (trigger_task_id) REFERENCES hsai_tasks(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (workflow_id) REFERENCES hsai_workflows(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS ix_hsai_workflow_executions_user_id ON [hsai_workflow_executions] (user_id);
CREATE INDEX IF NOT EXISTS ix_hsai_workflow_executions_status ON [hsai_workflow_executions] (status);
CREATE INDEX IF NOT EXISTS ix_hsai_workflow_executions_workflow_id ON [hsai_workflow_executions] (workflow_id);