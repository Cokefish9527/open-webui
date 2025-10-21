# 数据库迁移报告

- 启动时间：2025-10-21T08:32:51
- 结束时间：2025-10-21T08:32:56
- 总耗时：4.55 秒
- 模式：recreate
- Dry-run：否
- SQLite 源：`backend/data/webui.db`
- PostgreSQL 目标：`host=pgm-bp1x8d937cl58d1afo.pg.rds.aliyuncs.com port=5432 dbname=Owen_ai user=hsai password=******` / schema=`public`
- 处理数据表：47 个
- 成功迁移行数：859

## 备份与输出
- （未启用备份）

## 明细

| 表名 | 行数 | 耗时(s) | 新增索引 | 警告 | 状态 |
| --- | ---: | ---: | --- | --- | --- |
| `alembic_version` | 1 | 0.08 |  |  | ok |
| `auth` | 6 | 0.08 | auth_id |  | ok |
| `billing_config` | 2 | 0.12 | ix_billing_config_active<br/>ix_billing_config_key<br/>ix_billing_config_type |  | ok |
| `channel` | 0 | 0.04 |  |  | ok |
| `channel_member` | 0 | 0.04 |  |  | ok |
| `chat` | 31 | 0.16 | chat_share_id<br/>chat_id |  | ok |
| `chatidtag` | 0 | 0.06 | chatidtag_id |  | ok |
| `companies` | 2 | 0.10 | ix_companies_status<br/>ix_companies_owner_user_id |  | ok |
| `config` | 1 | 0.06 |  |  | ok |
| `credit` | 5 | 0.06 |  |  | ok |
| `credit_log` | 10 | 0.10 | ix_credit_log_created_at<br/>ix_credit_log_user_id |  | ok |
| `document` | 0 | 0.08 | document_name<br/>document_collection_name |  | ok |
| `feedback` | 0 | 0.04 |  |  | ok |
| `file` | 1 | 0.08 | file_id |  | ok |
| `folder` | 0 | 0.04 |  |  | ok |
| `function` | 0 | 0.06 | function_id |  | ok |
| `group` | 0 | 0.04 |  |  | ok |
| `hsai_account_groups` | 0 | 0.06 | ix_hsai_account_groups_user_id |  | ok |
| `hsai_analytics` | 0 | 0.13 | ix_hsai_analytics_user_id<br/>ix_hsai_analytics_period<br/>ix_hsai_analytics_date<br/>ix_hsai_analytics_dimension |  | ok |
| `hsai_business_api_usage_log` | 5 | 0.06 |  |  | ok |
| `hsai_material_tags` | 0 | 0.08 | ix_hsai_material_tags_user_id<br/>ix_hsai_material_tags_name |  | ok |
| `hsai_publish_tasks` | 0 | 0.12 | ix_hsai_publish_tasks_user_id<br/>ix_hsai_publish_tasks_status<br/>ix_hsai_publish_tasks_priority<br/>ix_hsai_publish_tasks_scheduled_at |  | ok |
| `hsai_video_learning_logs` | 0 | 0.04 |  |  | ok |
| `hsai_video_learning_status` | 60 | 0.06 |  |  | ok |
| `hsai_viral_videos` | 0 | 0.04 |  |  | ok |
| `hsai_workflows` | 0 | 0.10 | ix_hsai_workflows_category<br/>ix_hsai_workflows_status<br/>ix_hsai_workflows_user_id |  | ok |
| `knowledge` | 0 | 0.04 |  |  | ok |
| `memory` | 0 | 0.06 | memory_id |  | ok |
| `message` | 0 | 0.04 |  |  | ok |
| `message_reaction` | 0 | 0.04 |  |  | ok |
| `migratehistory` | 18 | 0.06 |  |  | ok |
| `model` | 0 | 0.06 | model_id |  | ok |
| `note` | 0 | 0.04 |  |  | ok |
| `prompt` | 0 | 0.06 | prompt_command |  | ok |
| `redis_queue_messages` | 514 | 0.20 | idx_redis_queue_messages_created_at<br/>idx_redis_queue_messages_status<br/>idx_redis_queue_messages_queue_name |  | ok |
| `tag` | 3 | 0.06 |  |  | ok |
| `tool` | 0 | 0.06 | tool_id |  | ok |
| `trade_ticket` | 0 | 0.08 | ix_trade_ticket_created_at<br/>ix_trade_ticket_user_id |  | ok |
| `hsai_projects` | 2 | 0.10 | ix_hsai_projects_status<br/>ix_hsai_projects_user_id |  | ok |
| `user` | 10 | 0.12 | user_oauth_sub<br/>user_id<br/>user_api_key |  | ok |
| `hsai_platform_accounts` | 0 | 0.12 | ix_hsai_platform_accounts_platform_type<br/>ix_hsai_platform_accounts_status<br/>ix_hsai_platform_accounts_group_id<br/>ix_hsai_platform_accounts_user_id |  | ok |
| `hsai_publish_records` | 0 | 0.12 | ix_hsai_publish_records_status<br/>ix_hsai_publish_records_account_id<br/>ix_hsai_publish_records_task_id<br/>ix_hsai_publish_records_published_at |  | ok |
| `hsai_cards` | 0 | 0.12 | ix_hsai_cards_type<br/>ix_hsai_cards_user_id<br/>ix_hsai_cards_chat_id<br/>ix_hsai_cards_status |  | ok |
| `hsai_material_folders` | 22 | 0.10 | ix_hsai_material_folders_parent_id<br/>ix_hsai_material_folders_user_id |  | ok |
| `hsai_materials` | 155 | 0.62 | ix_hsai_materials_folder_id<br/>ix_hsai_materials_status<br/>ix_hsai_materials_user_id<br/>ix_hsai_materials_type |  | ok |
| `hsai_tasks` | 11 | 0.18 | ix_hsai_tasks_assignee_id<br/>ix_hsai_tasks_type<br/>ix_hsai_tasks_status<br/>ix_hsai_tasks_user_id<br/>ix_hsai_tasks_chat_id<br/>ix_hsai_tasks_priority |  | ok |
| `hsai_workflow_executions` | 0 | 0.10 | ix_hsai_workflow_executions_user_id<br/>ix_hsai_workflow_executions_status<br/>ix_hsai_workflow_executions_workflow_id |  | ok |

## 回滚建议

1. 若迁移后数据异常，可通过以下方式回滚：
   - 使用报告中列出的 `pg_dump` 备份（若已启用）恢复。
   - 或者重新执行脚本，加上 `--mode=recreate --strict` 以保证失败即回滚。
2. 如需仅回滚某张表，可在 PostgreSQL 中执行：
   ```sql
   TRUNCATE TABLE "<schema>"."<table>" CASCADE;
   ```
   再重新运行脚本，并加上 `--tables <table>` 限定范围（未来版本支持）。
3. 执行回滚前建议先使用 `BEGIN; ... ROLLBACK;` 验证恢复脚本的正确性。