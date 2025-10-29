# ADR-20251029 战略蓝图同步与任务路由

## 背景
- Redis 队列在战略蓝图生成完成后会推送 `content_type=blue_image_content` 的消息，但后端缺少对蓝图内容的落库与任务联动逻辑。
- 现有任务体系要求主线任务与每日循环任务能够追溯来源，并在前端实时提示进度。缺失蓝图同步导致任务状态与用户认知出现漂移。
- 项目侧需要记录蓝图版本、执行节奏、循环配置以及更新日志，供后续决策与回滚参考。

## 决策
1. 在 `backend/open_webui/services` 下新增 `blueprint_sync_service.py`，由 `conversation_queue_handler` 在收到 `blue_image_content` 时调用，同步 n8n `hsai_extraction_blueprint` 最新记录。
2. 设计三张新表：
   - `hsai_blueprint_progress`（最新蓝图快照，按项目唯一）。
   - `hsai_blueprint_progress_history`（蓝图差异历史，记录变更快照与操作者）。
   - `hsai_task_blueprint_links`（蓝图与主线/循环任务关联，避免重复生成并提供追溯）。
3. 引入配置驱动的主线任务模板，生成社媒矩阵、素材补充、视频学习、每日发布循环四类任务；每日循环任务在所有前置模板完成后生成当日子任务。
4. 通过新事件 `hsai_task_blueprint_update` 通知前端刷新任务列表，原 `hsai_response` 继续承担消息回放。
5. 编写 `tool/add_blueprint_progress_tables.py` 负责 PostgreSQL 表初始化，遵循运行脚本 + PROJECTWIKI 更新同步策略。

## 影响
- `conversation_queue_handler` 逻辑扩展，需要加载蓝图同步服务并根据用户 session 定位 Socket 连接；增加了 Redis 消息处理耗时。
- 数据库增加三张表，依赖 PostgreSQL JSONB 与外键；项目部署需执行新脚本或 Alembic 迁移。
- 前端需要监听并消费 `hsai_task_blueprint_update`，以呈现主线任务与每日子任务的实时变化。
- PROJECTWIKI、CHANGELOG 更新以保证代码 ↔ 文档 ↔ 运维脚本的追溯闭环。

## 备选方案
1. **直接在任务表落地蓝图字段**：字段膨胀且难以管理历史，不利于多版本并存，放弃。
2. **n8n 侧完成任务落库**：需要跨库访问 Owen_ai 主库，提升耦合度且缺少业务校验，不采纳。
3. **仅记录蓝图文本**：缺乏结构化字段无法驱动循环任务和统计分析，无法满足业务要求。

## 实施与回滚
- 运行 `python tool/add_blueprint_progress_tables.py` 初始化新表，确认唯一约束与外键生效。
- 部署后观察 Redis 消费日志和 Socket 事件，若出现蓝图同步异常，可通过环境变量临时关闭（待后续为服务加开关）。
- 如需回滚：停止调用 `sync_blueprint_for_user`、删除新增表，并恢复旧版 PROJECTWIKI。注意清理 `hsai_task_blueprint_links` 孤立记录。

## 后续工作
- 在前端实现任务通知展示与每日循环进度看板。
- 将 `blueprint_task_templates` 配置化（数据库或管理后台），支持动态调整任务模板。
- 补充蓝图相关 API（查询当前蓝图、历史版本、任务映射）供外部系统调用。*** End Patch*** End Patch to=functions.apply_patch
