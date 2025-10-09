# SQL脚本分类文档

本文档对 `backend/sql` 目录中的所有SQL脚本按照新的目录结构进行分类，便于理解和维护。

## 目录结构说明

- `init_scripts/` - 包含所有用于初始化表结构的SQL脚本
- `schema_updates/` - 包含所有用于修改现有表结构的SQL脚本

## 1. 核心系统表

这些表是系统运行的基础表：

- [alembic_version_create_2025-10-04.sql](init_scripts/alembic_version_create_2025-10-04.sql) - 版本控制表
- [auth_create_2025-10-04.sql](init_scripts/auth_create_2025-10-04.sql) - 用户认证表
- [user_create_2025-10-04.sql](init_scripts/user_create_2025-10-04.sql) - 用户信息表
- [config_create_2025-10-04.sql](init_scripts/config_create_2025-10-04.sql) - 系统配置表
- [migratehistory_create_2025-10-04.sql](init_scripts/migratehistory_create_2025-10-04.sql) - 迁移历史表

## 2. 聊天与通信相关表

处理聊天、消息和通信功能的表：

- [chat_create_2025-10-04.sql](init_scripts/chat_create_2025-10-04.sql) - 聊天会话表
- [chatidtag_create_2025-10-04.sql](init_scripts/chatidtag_create_2025-10-04.sql) - 聊天标签关联表
- [message_create_2025-10-04.sql](init_scripts/message_create_2025-10-04.sql) - 消息表
- [message_reaction_create_2025-10-04.sql](init_scripts/message_reaction_create_2025-10-04.sql) - 消息反应表
- [channel_create_2025-10-04.sql](init_scripts/channel_create_2025-10-04.sql) - 频道表
- [channel_member_create_2025-10-04.sql](init_scripts/channel_member_create_2025-10-04.sql) - 频道成员表

## 3. AI模型与工具相关表

管理AI模型、工具和函数的表：

- [model_create_2025-10-04.sql](init_scripts/model_create_2025-10-04.sql) - AI模型表
- [tool_create_2025-10-04.sql](init_scripts/tool_create_2025-10-04.sql) - 工具表
- [function_create_2025-10-04.sql](init_scripts/function_create_2025-10-04.sql) - 函数表
- [prompt_create_2025-10-04.sql](init_scripts/prompt_create_2025-10-04.sql) - 提示词表

## 4. 文件与知识库相关表

处理文件存储和知识管理的表：

- [file_create_2025-10-04.sql](init_scripts/file_create_2025-10-04.sql) - 文件表
- [document_create_2025-10-04.sql](init_scripts/document_create_2025-10-04.sql) - 文档表
- [knowledge_create_2025-10-04.sql](init_scripts/knowledge_create_2025-10-04.sql) - 知识库表
- [folder_create_2025-10-04.sql](init_scripts/folder_create_2025-10-04.sql) - 文件夹表

## 5. 信用与计费相关表

处理用户信用和计费的表：

- [credit_create_2025-10-04.sql](init_scripts/credit_create_2025-10-04.sql) - 信用表
- [credit_log_create_2025-10-04.sql](init_scripts/credit_log_create_2025-10-04.sql) - 信用日志表
- [trade_ticket_create_2025-10-04.sql](init_scripts/trade_ticket_create_2025-10-04.sql) - 交易票据表

## 6. 组织与权限相关表

处理用户组织结构和权限的表：

- [group_create_2025-10-04.sql](init_scripts/group_create_2025-10-04.sql) - 用户组表
- [tag_create_2025-10-04.sql](init_scripts/tag_create_2025-10-04.sql) - 标签表
- [note_create_2025-10-04.sql](init_scripts/note_create_2025-10-04.sql) - 笔记表

## 7. HSAI核心业务表

HSAI项目的主业务表：

- [hsai_companies_create_2025-10-07.sql](init_scripts/hsai_companies_create_2025-10-07.sql) - 公司表
- [hsai_projects_create_2025-10-05.sql](init_scripts/hsai_projects_create_2025-10-05.sql) - 项目表
- [hsai_tasks_create_2025-10-04.sql](init_scripts/hsai_tasks_create_2025-10-04.sql) - 任务表
- [hsai_workflows_create_2025-10-04.sql](init_scripts/hsai_workflows_create_2025-10-04.sql) - 工作流表
- [hsai_workflow_executions_create_2025-10-04.sql](init_scripts/hsai_workflow_executions_create_2025-10-04.sql) - 工作流执行表
- [hsai_cards_create_2025-10-04.sql](init_scripts/hsai_cards_create_2025-10-04.sql) - 卡片表

## 8. HSAI素材管理表

处理素材存储和管理的表：

- [hsai_material_folders_create_2025-10-04.sql](init_scripts/hsai_material_folders_create_2025-10-04.sql) - 素材文件夹表
- [hsai_materials_create_2025-10-04.sql](init_scripts/hsai_materials_create_2025-10-04.sql) - 素材表
- [hsai_material_tags_create_2025-10-04.sql](init_scripts/hsai_material_tags_create_2025-10-04.sql) - 素材标签表

## 9. HSAI社交媒体管理表

处理社交媒体账号和发布任务的表：

- [hsai_account_groups_create_2025-10-04.sql](init_scripts/hsai_account_groups_create_2025-10-04.sql) - 账号分组表
- [hsai_platform_accounts_create_2025-10-04.sql](init_scripts/hsai_platform_accounts_create_2025-10-04.sql) - 平台账号表
- [hsai_publish_tasks_create_2025-10-04.sql](init_scripts/hsai_publish_tasks_create_2025-10-04.sql) - 发布任务表
- [hsai_publish_records_create_2025-10-04.sql](init_scripts/hsai_publish_records_create_2025-10-04.sql) - 发布记录表

## 10. HSAI数据分析表

处理数据分析和统计的表：

- [hsai_analytics_create_2025-10-04.sql](init_scripts/hsai_analytics_create_2025-10-04.sql) - 分析数据表
- [hsai_viral_videos_create_2025-10-04.sql](init_scripts/hsai_viral_videos_create_2025-10-04.sql) - 病毒视频表
- [hsai_video_learning_status_create_2025-10-04.sql](init_scripts/hsai_video_learning_status_create_2025-10-04.sql) - 视频学习状态表

## 11. 数据库结构变更脚本

用于修改现有表结构的脚本，位于 `schema_updates/` 目录中：

- [hsai_projects_alter_2025-10-07.sql](schema_updates/hsai_projects_alter_2025-10-07.sql) - 项目表结构扩展
- [hsai_tasks_alter_2025-10-05.sql](schema_updates/hsai_tasks_alter_2025-10-05.sql) - 任务表结构修改
- [hsai_users_alter_2025-10-07.sql](schema_updates/hsai_users_alter_2025-10-07.sql) - 用户表结构扩展
- [hsai_tasks_remove_unused_fields_2025-10-07.sql](schema_updates/hsai_tasks_remove_unused_fields_2025-10-07.sql) - 移除任务表冗余字段
- [hsai_companies_create_2025-10-07.sql](schema_updates/hsai_companies_create_2025-10-07.sql) - 公司表创建脚本
- [hsai_users_alter_add_company_id_2025-10-07.sql](schema_updates/hsai_users_alter_add_company_id_2025-10-07.sql) - 用户表添加公司关联字段
- [hsai_projects_alter_add_company_id_2025-10-07.sql](schema_updates/hsai_projects_alter_add_company_id_2025-10-07.sql) - 项目表添加公司关联字段
- [hsai_tasks_alter_add_project_id_and_prompt_config_2025-10-07.sql](schema_updates/hsai_tasks_alter_add_project_id_and_prompt_config_2025-10-07.sql) - 任务表添加项目关联和提示词配置字段
- [001_create_redis_queue_messages_table.sql](schema_updates/001_create_redis_queue_messages_table.sql) - Redis队列消息表创建脚本

## 12. 完整数据库初始化脚本

包含所有表结构的完整初始化脚本，位于 `init_scripts/` 目录中：

- [full_database_init_2025-10-04.sql](init_scripts/full_database_init_2025-10-04.sql) - 完整数据库初始化脚本

## 13. 反馈与监控表

处理用户反馈和系统监控的表：

- [feedback_create_2025-10-04.sql](init_scripts/feedback_create_2025-10-04.sql) - 用户反馈表
- [memory_create_2025-10-04.sql](init_scripts/memory_create_2025-10-04.sql) - 内存状态表

## 分类说明

此分类基于表的主要功能和业务领域进行划分，有助于开发人员快速定位相关表结构和理解系统架构。每个分类中的脚本按照创建时间排序，便于跟踪表结构的演进过程。