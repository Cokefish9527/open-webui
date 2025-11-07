# 任务系统后台配合说明（2025-11-07）

## 1. 背景
任务系统已完成蓝图触发、主线任务模板化、自动校验（社媒矩阵、素材补充、视频学习）等能力。为确保生产可用，需要后台管理系统（Owen Admin）提供模板、素材清单、监控与运维支撑。本文汇总已落地功能，并明确后台需配合的事项。

## 2. 已开发功能速览
1. **任务模板配置化**：`task_template_registry` 动态从 Owen_admin.public.`task_templates` 读取蓝图/项目模板，支持缓存与 fallback。
2. **企业信息收集模板**：蓝图消息触发后自动将 `company_info_collection` 任务标记为完成，避免重复人工处理。
3. **三大任务自动校验**：
   - 社媒矩阵：读取 `social_accounts`（Owen_ai）统计活跃账号数，与蓝图要求比对。
   - 素材补充：结合 `hsai_materials`（Owen_ai）与 `checklist_templates`（Owen_admin）判断素材数量及类别。
   - 视频学习：基于 `hsai_business_video_content_learned`（n8n）统计可用脚本库存，低于阈值自动拉起任务。
4. **蓝图消息防抖**：`conversation_queue_handler` 增加 Debounce + Token TTL + per-user Lock，避免重复同步；日志可追踪模板来源与耗时。
5. **任务进度可视化字段**：任务 `config.progress_metrics` 持续写入账号/素材/脚本缺口，方便前端展示。
6. **执行计划沉淀**：`docs/task_system_enhancement_plan.md` 记录所有交付里程碑，便于跨团队跟进。

## 3. 后台管理系统需配合事项
| 模块 | 需求 | 说明 |
| --- | --- | --- |
| 任务模板管理 | 提供 `task_templates` CRUD，字段必须包含 `template_key/title/task_type/task_category/config/prompt_config/status/version`；模板修改后需支持缓存刷新或推送通知。 | 目前通过 `tool/sync_admin_task_templates.py` 写入 `company_info_collection`，后续需在后台界面维护。 |
| 模板版本/发布 | 在后台展示模板版本、关联蓝图任务、最近发布记录，并支持回滚；保证 `status=active/published` 的模板才会被读取。 | 需要对接任务模板版本表 `task_template_versions`。 |
| 素材清单配置 | 后台需维护 `checklist_templates / checklist_scenes / checklist_items / checklist_publications`，并向业务侧提供模板编码（如 `MATERIAL_STD_V1`）；要支持按行业或企业规模生成清单。 | 任务系统读取 `code` 与 `required_items`，需确保字段准确填充。 |
| 社媒账号监控 | 提供账号绑定、状态变更、活跃性校验的后台操作界面，保证 `social_accounts.status` 准确（active / disabled）。 | 任务判定依赖 active 状态与 platform 字段。 |
| 视频脚本库配置 | 在后台或 n8n 控制台提供脚本状态维护（unused/pending/used），并允许设置脚本阈值。 | 任务模板可在 `config.script_threshold` 中覆盖默认值。 |
| 运维工具 | 暴露脚本入口（例如 `tool/sync_admin_task_templates.py`）以及 Debounce 配置项的管理界面，便于快速调整。 | 环境变量：`BLUEPRINT_SYNC_DEBOUNCE_SECONDS`、`BLUEPRINT_SYNC_TOKEN_TTL_SECONDS`。 |

## 4. API / 配置依赖
- `.env` 中必须配置 `ADMIN_DATABASE_URL` 指向 Owen_admin；若与主库同实例可复用账号，但需具备读取 `task_templates`、`checklist_*` 权限。
- 蓝图消息防抖参数默认 20s / 300s，可根据后台实际吞吐调整，建议提供配置项。
- Admin 侧每次模板/清单发布完成需通知主系统刷新缓存（可通过 Redis 事件或 REST Hook 实现）。

## 5. 建议的后台交付清单
1. **任务模板管理界面**：查询/新建/克隆/发布/回滚 + JSON 预览。
2. **素材清单管理**：模板 → 场景 → 条目三级结构编辑，支持批量导入、发布与撤回。
3. **社媒账号审核台**：展示企业绑定账号、状态、token 过期时间，一键同步至 `social_accounts`。
4. **脚本资源看板**：按企业统计脚本库存、消费记录，并可手动标记状态。
5. **运维面板**：显示蓝图同步耗时、任务自动完成日志、Debounce 命中率，提供开关/参数配置。

## 6. 后续联动
- 将素材上传、脚本导入等后台操作与 `task_completion_service.evaluate_project_tasks()` 打通，实现实时反馈。
- 在 Admin 发布模板或清单后自动触发任务系统缓存刷新（可调用 `/internal/task-templates/refresh`，待后端补充 API）。
- 计划逐步扩展“素材清单审核结果 → 任务完成”的反向同步，由后台审核操作直接回写 `progress_metrics`。
