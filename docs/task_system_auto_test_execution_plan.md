# 任务系统自动化测试实施计划（2025-11-06）

## 1. 阶段划分
| 阶段 | 目标 | 关键输出 |
| --- | --- | --- |
| P1 分析 | 梳理需求、现状、缺口 | `docs/task_system_auto_test_brainstorm.md` |
| P2 方案 | 确定整体技术路线与脚本清单 | `docs/task_system_auto_test_plan.md` |
| P3 计划 | 细化实现步骤、依赖、验收标准 | 本文档 |
| P4 执行 | 按计划交付脚本、文档和报告 | 代码、报告、WIKI 更新 |

## 2. 实施任务拆解
1. **Admin API 能力补齐**
   - 检查现有 `/api/v1/users`、`/api/v1/auths/add` 等接口。
   - 若缺失随机公司创建 & 注销能力，在 `backend/open_webui/routers` 下新增/扩展 Admin 模块。
   - 验收：CLI 可调用 API 完成创建/删除，Audit 日志正确记录。

2. **脚本开发**
   1. `tool/admin_user_lifecycle.py`
      - 调用 Admin API，支持 `create-random`、`delete` 子命令。
      - 生成公司/项目种子数据，返回账号、密码、token。
   2. `tool/reset_user_task_data.py`
      - 改造为 PostgreSQL/SQLAlchemy 实现，兼容旧参数。
   3. `tool/verify_task_system_nodes.py`
      - 校验任务/蓝图/状态日志/Outbox；输出 JSON 与人类可读摘要。
   4. `tool/collect_service_logs.py`
      - 读取配置目录，过滤关键字。
   5. `tool/orchestrate_task_system_auto_test.py`
      - 负责流程编排、重试、报告生成。
   - 验收：每个脚本均有 `--help`、`--config`；支持 dry-run。

3. **配置与模板**
   - 新增 `configs/task_system_auto_test.toml`（示例值）。
   - 新增 `reports/task_system_auto_test_report_TEMPLATE.md`。

4. **自动化流程执行**
   - 使用 orchestrator 脚本完成至少一次成功、一次失败路径。
   - 生成报告 `reports/task_system_auto_test_report_<timestamp>.md`。

5. **文档与 WIKI 更新**
   - `PROJECTWIKI.md`：新增流程章节 + 变更日志。
   - `docs/task_system_auto_test_log.md`：记录执行摘要。
   - 若新增 API，更新 `docs/backend_service_integration.md`、`docs/API文档检查报告.md`。

6. **交付审查**
   - 自检：lint、单测（如 applicable）。
   - 输出最终汇总：包含脚本路径、执行命令、报告位置、后续建议。

## 3. 资源与依赖
- **环境变量**：`DATABASE_URL`（PostgreSQL）、`ADMIN_API_TOKEN`、`REDIS_HOST/PORT`。
- **工具依赖**：`requests`/`httpx`、`psycopg2` 或 SQLAlchemy（复用项目依赖）。
- **日志路径**：默认 `logs/`（若无则由 config 指定）。

## 4. 风险清单
| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| Admin API 权限不足 | 无法创建账号 | 在计划阶段申请/配置管理员 token，脚本支持自检 |
| PostgreSQL 连接失败 | 校验脚本中断 | 预先通过 `tool/test_db_simple.py` 验证 DSN，增加重试 |
| Redis 未启动 | 蓝图触发失败 | orchestrator 在执行前检测 Redis，失败则跳过执行并报错 |
| 文档不同步 | 无法追溯 | 执行阶段结束前 checklist 确认 `PROJECTWIKI.md`/docs 更新 |

## 5. 时间与优先级
1. Admin API 检查/扩展（优先级 P0）
2. admin_user_lifecycle.py + reset_user_task_data.py 改造（P0）
3. verify/collect 脚本（P1）
4. orchestrator + configs + reports（P1）
5. 自动化执行 & 文档更新（P1）
6. 复盘与输出报告（P2）

## 6. 验收检查表
- [ ] 新增脚本具备 CLI 帮助与示例
- [ ] PostgreSQL/Redis 连接成功日志
- [ ] 报告模板 + 实际报告
- [ ] PROJECTWIKI/ docs 更新
- [ ] 变更说明列出代码 ↔ 文档链接

> 计划确认后进入执行阶段。
