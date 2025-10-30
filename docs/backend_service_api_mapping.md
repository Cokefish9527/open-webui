# Owen AI 接口对接核查报告（2025-10-30）

## 1. 鉴权方案核实
- 业务端在 `docs/OwenAI_API.md` 中声明的认证方式为 Bearer Token。
- 集成文档已同步至 OAuth2 Client Credentials + 短期 JWT 模式：HTTPS 强制、可选请求签名，并要求携带操作员 Header 字段；后台需按约定实现 token 缓存与轮换。
- 待办：业务服务需开放 Client ID/Secret 发放与 token 撤销能力，未完成前无法上线正式环境。

## 2. 模块接口映射
| 模块 | 业务端已提供 | 缺失 / 差异 | 后台影响 |
| --- | --- | --- | --- |
| 客户管理 | `GET/POST/PUT/DELETE /api/v1/external/admin/users`；`PUT /api/v1/users/{user_id}/credit` | 缺少重置密码、启用/禁用接口；路径与旧文档不一致 | 更新请求路径；重置密码/启用禁用保持待办占位，避免直连数据库写操作 |
| 公司管理 | （暂无） | 列表、创建、更新、删除全部缺失 | 暂保留只读直连并加风险提示；上线前需业务补齐接口后切换 |
| 项目管理 | `GET/POST /api/v1/hsai/projects/`；`GET/PUT/DELETE /api/v1/hsai/projects/{project_id}`；`GET /api/v1/hsai/projects/{project_id}/tasks` | 路径前缀从 `/api/projects` 调整为 `/api/v1/hsai/projects` | 后台改造时需统一新前缀；其余能力满足需求 |
| 任务管理 | `GET/POST /api/v1/hsai/tasks/`；`GET/PUT /api/v1/hsai/tasks/{task_id}`；`POST /api/v1/hsai/tasks/{task_id}/start`/`cancel`/`assign`；`PUT /api/v1/hsai/tasks/{task_id}/progress`；`GET /api/v1/hsai/ai/task-templates` | 模板的 POST/PUT/DELETE 及任务依赖维护接口缺失 | 模板和依赖仍需直连 DB，必须在业务端补齐后迁移 |
| 计费管理 | `GET/POST/PUT/DELETE /api/v1/billing/billing/configs`；`GET/POST /api/v1/billing/billing/usage-logs`；`GET /api/v1/billing/billing/usage-logs/session/{session_id}`；`GET /api/v1/billing/billing/usage-logs/session/{session_id}/total`；`GET /api/v1/credit/logs`；`POST /api/v1/credit/tickets`；`PUT /api/v1/users/{user_id}/credit` | 未提供公司级汇总接口；路径包含重复 `billing` 前缀 | 文档已按真实路径更新；后台调账统一走 `/api/v1/users/{user_id}/credit` |

## 3. 文档同步建议
1. 《backend_service_integration.md》已按实际端点维护；新接口上线需立即更新表格与状态标记。
2. 《PROJECTWIKI.md》应引用本映射表，标记缺失接口的追踪责任人或 Issue，减少误判。
3. 若业务端交付新增接口，需同步更新本报告、集成文档以及 `CHANGELOG`，确保可追溯。

## 4. 后续动作
- 与业务团队确认缺失接口交付计划，明确负责人和里程碑。
- 后台改造阶段先实现鉴权与现有接口调用，缺失功能保持 Feature Flag 防守。
- 补齐接口后安排联调与自动化回归测试，重点覆盖 token 过期、权限校验、错误码解析场景。
