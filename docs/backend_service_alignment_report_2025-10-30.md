# 后台对接 OwenAI 服务端同步报告（2025-10-30）

## 1. 本次完成
- 《docs/backend_service_integration.md》已替换为 OwenAI 实际端点（/api/v1/external/admin/**、/api/v1/hsai/**、/api/v1/billing/**、/api/v1/credit/**），并标注缺失接口：客户重置密码 / 启用禁用、公司 CRUD、任务模板与依赖维护、计费汇总。
- 《docs/backend_service_api_mapping.md》重新整理为“业务端已提供 / 缺失 / 后台影响”四列表格，便于快速审阅当前能力。
- 《PROJECTWIKI.md》同步新增 API 现状、鉴权约束与模块待办，架构图更新为三路 API 通道（客户 / 业务 / 计费），确保知识库与文档/代码一致。

## 2. 模块对接状态总览
| 模块 | 可用端点 | 缺口 | 后台策略 |
| --- | --- | --- | --- |
| 客户账号 | `GET/POST/PUT/DELETE /api/v1/external/admin/users`，`PUT /api/v1/users/{user_id}/credit` | 重置密码、启用/禁用 | 保留操作入口，待接口上线；其余操作可切换为 API 调用 |
| 公司 | （无） | 全量 CRUD | 仅允许只读直连 `companies` 表，新增/编辑暂冻结 |
| 项目 | `/api/v1/hsai/projects/**` | 无 | 更新调用前缀，使用业务端校验完成度 |
| 任务 | `/api/v1/hsai/tasks/**`、任务状态操作、进度更新、模板查询 | 模板增删改、依赖维护 | 先迁移 CRUD + 状态流程，模板/依赖保留 ORM 兜底 |
| 计费 | `/api/v1/billing/billing/**`、`/api/v1/credit/**`、`PUT /api/v1/users/{user_id}/credit` | 公司级汇总 | 调账统一走用户积分接口，汇总数据暂用报表计算 |

## 3. 优先动作
1. **接口补齐协同**  
   - 客户重置密码 / 启用禁用；负责人：业务后端 Team-A，目标发布时间 2025-11-05。  
   - 公司 CRUD；负责人：业务后端 Team-B，目标发布时间 2025-11-12。  
   - 任务模板 CRUD 与依赖接口；负责人：AI 工作流小组，目标发布时间 2025-11-19。  
   - 计费公司汇总；负责人：Billing 小组，目标发布时间 2025-11-26。
2. **后台改造排期**  
   - Sprint 1：接入客户/项目/任务现有 API，完成 OAuth2 客户端与缓存。  
   - Sprint 2：计费模块改造 + 调账路径切换。  
   - Sprint 3：在接口补齐后关闭 ORM 写路径，增加集成测试。
3. **风险与回滚**  
   - 若接口延迟上线，保持 Feature Flag 仅在预生产开启。  
   - OAuth2 客户端需具备回退方案（退回旧 API Key 鉴权）以防 token 服务故障。

## 4. 验证建议
- 新增集成测试覆盖：token 获取失败、scope 不匹配、接口 4xx/5xx 重试、timeout 处理。
- 日志与审计：确认 Header 中 `X-Operator-*` 字段在业务端落库，并将操作 ID 写入后台操作日志（`admin_audit_log`）。
- 联调 checklist：参考《docs/backend_service_integration.md》“迁移步骤”章节，逐模块完成 smoke test 与数据一致性检查。

## 5. 文档索引
- 接口设计与迁移指南：《docs/backend_service_integration.md》
- 模块现状映射表：《docs/backend_service_api_mapping.md》
- 项目知识库（架构/待办追踪）：`PROJECTWIKI.md`（章节：模块文档 / REST）
