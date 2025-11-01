# 后台对接缺口清单（除 OSS & 安全策略）

- **来源**：docs/backend_service_integration.md · openapi.json
- **更新日期**：2025-11-01
- **用途**：与服务端团队确认仍需补齐的业务接口与能力。

## 1. 客户管理
- ✅ 新增 `/external/admin/users/{user_id}/reset-password` 重置密码接口（OAuth2 Bearer）。
- ✅ 新增 `/external/admin/users/{user_id}/enable|disable` 启用/禁用接口，结果返回最新启用状态。
- ⏳ 待补：批量操作与操作审计 ID 回传。

## 2. 公司管理
- ✅ 移除 `organizations` 实体，统一以 `companies` 表承载公司信息，并新增 `/external/admin/companies` 系列接口（创建 / 更新 / 删除 / 列表 / 用户分配）。
- ⏳ 删除公司前的计费/项目依赖校验仍待补充（见章节 5）。

## 3. 项目相关
- 当前接口满足 CRUD，但文档要求项目删除需检查未完成任务、计费等；需确认服务端是否已实现相关校验。
- 项目应绑定唯一“战略蓝图”(blueprint) 执行信息，现有数据模型仅提供 workflow_id 字段，缺少专门接口约束：
  - 建议新增 GET/POST /api/v1/hsai/projects/{id}/blueprint 管理接口；
  - 或在项目创建/更新时校验 workflow_id 与项目的唯一性。

## 4. 任务 / 模板 / 依赖
- **任务模板 CRUD**：后台需要 POST|PUT|DELETE /api/v1/hsai/ai/task-templates 以维护模板；服务端仅提供 GET。
- **任务依赖维护**：文档要求对 	ask_dependencies 进行新增/删除，但 OpenAPI 未暴露相关端点。
- **任务进度同步**：需确认 PUT /api/v1/hsai/tasks/{task_id}/progress 支持查询参数与请求体两种方式，否则后台需做适配。

## 5. 计费模块
- **公司账单汇总**：原文档引用 GET /api/billing/companies，OpenAPI 未提供；需新增接口汇总公司账单/余额信息。
- **额度同步**：PUT /api/v1/users/{user_id}/credit 存在，但需确认返回结构是否含最新余额以便后台更新。

## 6. 鉴权与通知
- ✅ 外部后台改用 OAuth2 Client Credentials，服务端颁发并持久化 Bearer Token；后续需补充 Token 吊销/审计回溯流程。
- 删除项目、删除任务、批量扣费等高风险操作需要服务端返回操作审计 ID；当前接口未说明。
- 建议提供 webhook / 通知机制，让后台在服务端发生关键事件时获得同步反馈（可选）。

## 7. 通用事项
- 所有新增/调整接口需同步更新官方 openapi.json，并提供示例请求/响应。
- 请确认分页参数命名与后台一致 (pi/ps vs page/size) 以减少适配成本。
- 计费模块改造（公司账单汇总 / 额度同步）暂缓，后续补充计划需单独排期。
