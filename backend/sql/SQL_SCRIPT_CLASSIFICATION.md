# SQL脚本分类说明

本文档对项目中的SQL脚本进行分类说明，便于维护和查找。

## 1. 数据库版本管理表

用于跟踪数据库迁移历史的表：

- [alembic_version_create_2025-10-04.sql](init_scripts/alembic_version_create_2025-10-04.sql) - Alembic版本跟踪表

## 2. 用户认证相关表

处理用户认证和权限的表：

- [auth_create_2025-10-04.sql](init_scripts/auth_create_2025-10-04.sql) - 用户认证表
- [user_create_2025-10-04.sql](init_scripts/user_create_2025-10-04.sql) - 用户信息表

## 3. 聊天对话相关表

处理聊天会话和消息的表：

- [chat_create_2025-10-04.sql](init_scripts/chat_create_2025-10-04.sql) - 聊天会话表
- [message_create_2025-10-04.sql](init_scripts/message_create_2025-10-04.sql) - 消息记录表
- [chatidtag_create_2025-10-04.sql](init_scripts/chatidtag_create_2025-10-04.sql) - 聊天标签关联表
- [message_reaction_create_2025-10-04.sql](init_scripts/message_reaction_create_2025-10-04.sql) - 消息反应表

## 4. 知识库和文档管理表

处理知识库和文档存储的表：

- [document_create_2025-10-04.sql](init_scripts/document_create_2025-10-04.sql) - 文档表
- [knowledge_create_2025-10-04.sql](init_scripts/knowledge_create_2025-10-04.sql) - 知识库表

## 5. 模型和工具管理表

处理AI模型和工具的表：

- [model_create_2025-10-04.sql](init_scripts/model_create_2025-10-04.sql) - AI模型表
- [tool_create_2025-10-04.sql](init_scripts/tool_create_2025-10-04.sql) - 工具表
- [function_create_2025-10-04.sql](init_scripts/function_create_2025-10-04.sql) - 函数表

## 6. 提示词和配置管理表

处理提示词和系统配置的表：

- [prompt_create_2025-10-04.sql](init_scripts/prompt_create_2025-10-04.sql) - 提示词表
- [config_create_2025-10-04.sql](init_scripts/config_create_2025-10-04.sql) - 系统配置表

## 7. 文件和文件夹管理表

处理文件存储和组织的表：

- [file_create_2025-10-04.sql](init_scripts/file_create_2025-10-04.sql) - 文件表
- [folder_create_2025-10-04.sql](init_scripts/folder_create_2025-10-04.sql) - 文件夹表

## 8. 信用和计费系统表

处理用户积分和计费的表：

- [credit_create_2025-10-04.sql](init_scripts/credit_create_2025-10-04.sql) - 用户积分表
- [credit_log_create_2025-10-04.sql](init_scripts/credit_log_create_2025-10-04.sql) - 积分记录表
- [trade_ticket_create_2025-10-04.sql](init_scripts/trade_ticket_create_2025-10-04.sql) - 交易票据表

## 9. 组织和权限管理表

处理用户组和权限的表：

- [group_create_2025-10-04.sql](init_scripts/group_create_2025-10-04.sql) - 用户组表
- [channel_create_2025-10-04.sql](init_scripts/channel_create_2025-10-04.sql) - 频道表
- [channel_member_create_2025-10-04.sql](init_scripts/channel_member_create_2025-10-04.sql) - 频道成员表

## 10. 反馈和评价系统表

处理用户反馈和评价的表：

- [feedback_create_2025-10-04.sql](init_scripts/feedback_create_2025-10-04.sql) - 用户反馈表
- [memory_create_2025-10-04.sql](init_scripts/memory_create_2025-10-04.sql) - 用户记忆表
- [tag_create_2025-10-04.sql](init_scripts/tag_create_2025-10-04.sql) - 标签表
- [note_create_2025-10-04.sql](init_scripts/note_create_2025-10-04.sql) - 笔记表

## 11. HSAI项目主业务表

HSAI项目的主业务表：

- [hsai_companies_create_2025-10-07.sql](init_scripts/hsai_companies_create_2025-10-07.sql) - 公司表
- [hsai_projects_create_2025-10-05.sql](init_scripts/hsai_projects_create_2025-10-05.sql) - 项目表
- [hsai_tasks_create_2025-10-04.sql](init_scripts/hsai_tasks_create_2025-10-04.sql) - 任务表
- [hsai_workflows_create_2025-10-04.sql](init_scripts/hsai_workflows_create_2025-10-04.sql) - 工作流表
- [hsai_workflow_executions_create_2025-10-04.sql](init_scripts/hsai_workflow_executions_create_2025-10-04.sql) - 工作流执行表
- [hsai_cards_create_2025-10-04.sql](init_scripts/hsai_cards_create_2025-10-04.sql) - 卡片表

## 12. HSAI素材管理表

处理素材存储和管理的表：

- [hsai_material_folders_create_2025-10-04.sql](init_scripts/hsai_material_folders_create_2025-10-04.sql) - 素材文件夹表
- [hsai_materials_create_2025-10-04.sql](init_scripts/hsai_materials_create_2025-10-04.sql) - 素材表
- [hsai_material_tags_create_2025-10-04.sql](init_scripts/hsai_material_tags_create_2025-10-04.sql) - 素材标签表

## 13. HSAI社交媒体管理表

处理社交媒体账号和发布任务的表：

- [hsai_account_groups_create_2025-10-04.sql](init_scripts/hsai_account_groups_create_2025-10-04.sql) - 账号分组表
- [hsai_platform_accounts_create_2025-10-04.sql](init_scripts/hsai_platform_accounts_create_2025-10-04.sql) - 平台账号表
- [hsai_publish_tasks_create_2025-10-04.sql](init_scripts/hsai_publish_tasks_create_2025-10-04.sql) - 发布任务表
- [hsai_publish_records_create_2025-10-04.sql](init_scripts/hsai_publish_records_create_2025-10-04.sql) - 发布记录表

## 14. HSAI数据分析表

处理数据分析和统计的表：

- [hsai_analytics_create_2025-10-04.sql](init_scripts/hsai_analytics_create_2025-10-04.sql) - 数据分析表
- [hsai_viral_videos_create_2025-10-04.sql](init_scripts/hsai_viral_videos_create_2025-10-04.sql) - 爆款视频表
- [hsai_video_learning_status_create_2025-10-04.sql](init_scripts/hsai_video_learning_status_create_2025-10-04.sql) - 视频学习状态表

## 15. 计费系统表

处理API使用记录和计费配置的表：

- [hsai_business_api_usage_log_create_2025-10-10.sql](init_scripts/hsai_business_api_usage_log_create_2025-10-10.sql) - API使用记录表
- [billing_config_create_2025-10-10.sql](init_scripts/billing_config_create_2025-10-10.sql) - 计费配置表
- [billing_config_default_data_2025-10-10.sql](init_scripts/billing_config_default_data_2025-10-10.sql) - 计费配置默认数据

## 16. 完整数据库初始化脚本

包含所有表结构的完整初始化脚本：

- [full_database_init_2025-10-04.sql](init_scripts/full_database_init_2025-10-04.sql) - 完整数据库初始化脚本

## 17. 数据库迁移历史表

用于跟踪数据库迁移历史的表：

- [migratehistory_create_2025-10-04.sql](init_scripts/migratehistory_create_2025-10-04.sql) - 数据库迁移历史表