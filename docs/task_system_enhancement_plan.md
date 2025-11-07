# 任务系统强化计划（2025-11-07）

## 1. 范围与目标
- 将任务模板从代码常量迁移到 Owen Admin 数据库，确保模板、脚本与任务逻辑一致。
- 在蓝图触发链路中增加并发防抖、模板缓存与执行轨迹，避免重复生成任务。
- 为“社媒矩阵创建 / 素材补充 / 视频学习”三类任务建立可自动判定的完成规则，并写回任务状态。
- 完成 PROJECTWIKI / docs 的同步，沉淀运行手册与脚本使用说明。

## 2. 工作项状态
| 序号 | 工作项 | 交付物 | 状态 | 备注 |
| --- | --- | --- | --- | --- |
| P1 | Owen Admin 模板加载与脚本 | `backend/open_webui/services/task_template_registry.py`、`tool/sync_admin_task_templates.py` | ✅ 2025-11-07 | 支持 `ADMIN_DATABASE_URL`、回退到本地模板 |
| P2 | 蓝图消息链路增强 | `utils/conversation_queue_handler.py` 去重 + 日志、蓝图同步耗时打点 | ✅ 2025-11-07 | Debounce + Token TTL、防并发锁 |
| P3 | 三大主线任务自动校验 | `services/task_completion_service.py`、社媒/素材/脚本数据源 | ✅ 2025-11-07 | 自动写入 `progress_metrics` 并补记 `task_state_logs` |
| P4 | 文档与运维知识同步 | PROJECTWIKI + 本计划文件 | ✅ 2025-11-07 | 本文即计划，WIKI、脚本说明已同步 |

## 3. 风险与缓解
- **模板缓存空值**：若 Owen Admin 不可达，注册中心将回退至本地常量并打 Warning；持续无法连接时通过 `ADMIN_DATABASE_URL` 切换到主库。
- **蓝图消息风暴**：Debounce（默认 20s）+ token TTL（默认 5 分钟）已在 handler 中配置，可通过环境变量覆盖；如需加速可调低 `BLUEPRINT_SYNC_DEBOUNCE_SECONDS`。
- **业务阈值差异**：`config` 中可覆盖 `platform/required_accounts/script_threshold` 等指标，未配置时按 DEFAULT_RULES。

## 4. 待办（滚动维护）
- [ ] 完成 PROJECTWIKI 任务章节的更新并记录脚本/命令。
- [ ] 与 Admin 团队确认素材清单模板编码（`MATERIAL_STD_V1`）与发布策略。
- [ ] 在素材上传、脚本导入等入口触发 `evaluate_project_tasks()`，缩短反馈链路。

