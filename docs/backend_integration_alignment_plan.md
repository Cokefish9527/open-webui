# 后台对接缺口对齐方案（2025-11-01）

## 1. 范围与目标
- **目的**：根据 `docs/integration_gap_checklist.md` 与现有实现，明确后台（Admin）与主业务服务端（Owen AI）的对齐路径，形成可执行的接口与文档更新计划。
- **输出**：差距清单→整改动作→验证/交付标准→文档与责任分工，覆盖客户、公司、项目、任务、计费及审计领域。
- **关联资料**：`docs/backend_service_integration.md`、`docs/task_system_design.md`、`docs/plan_ws_tester_fullstack.md`、`docs/410_websocket_test_page_manual.md`、`PROJECTWIKI.md#调试工具`。

## 2. 里程碑总览
```mermaid
flowchart LR
  GapReview[缺口复核\n(现状确认)] --> ContractAlign[接口契约对齐\n(API Draft/OAS)]
  ContractAlign --> Impl[服务端实现\n& 测试]
  Impl --> AdminAdapt[后台适配\n& 联调]
  AdminAdapt --> Verification[验收与审计\n(含WS工具)]
  Verification --> DocSync[文档&Wiki同步\n+ 发布说明]
```

- **节奏建议**：GapReview（D0）→ ContractAlign（D0-D1）→ Impl + AdminAdapt（D1-D3）→ Verification（D3）→ DocSync（D3）。

## 3. 缺口对齐明细

### 3.1 客户管理
| 缺口 | 当前状态 | 对齐策略 | 责任方 | 验收标准 |
| --- | --- | --- | --- | --- |
| 重置密码接口缺失 | ✅ `/external/admin/users/{user_id}/reset-password` 已上线（OAuth2 Bearer） | 后续补充审计 ID 与密码过期策略 | 服务端 | 1) 返回成功结果；2) 审计日志记录操作者；3) 文档同步 |
| 启用/禁用账号 | ✅ `/external/admin/users/{user_id}/enable` / `disable` 已上线 | 继续评估批量操作与审计字段 | 服务端 | 1) 返回 `active` 字段；2) 调用后状态即时生效；3) 文档同步 |
| 鉴权与令牌 | ✅ 已改为 OAuth2 Client Credentials，Bearer Token 持久化存储 | 后续补充 Token 吊销 API 及 `X-Operator-*` 审计头约束 | 双方 | 1) 令牌颁发接口返回 `expires_in`；2) Bearer 校验触发 401/403 时落日志；3) 安全策略文档更新 |

### 3.2 公司管理
| 缺口 | 当前状态 | 对齐策略 | 责任方 | 验收标准 |
| --- | --- | --- | --- | --- |
| 公司接口统一 | ✅ `organizations` 实体下线，新增 `/external/admin/companies` CRUD & 用户分配 | 删除公司前仍需对计费/项目做阻断校验 | 服务端主导，后台配合 | 1) OpenAPI 新增公司接口；2) 后台调用链全部切换；3) 删除失败返回阻断详情 |

### 3.3 项目相关
| 缺口 | 当前状态 | 对齐策略 | 责任方 | 验收标准 |
| --- | --- | --- | --- | --- |
| 删除校验粒度 | 文档要求检查未完成任务/计费；实现待确认 | 在服务端删除前执行：未完成任务数量=0、无挂起扣费工单、计费余额>=0；失败时返回详细冲突列表 | 服务端 | 1) 删除失败响应含 `blocking_dependencies`；2) 后台 UI 展示阻断详情；3) 集成测试覆盖待处理任务场景 |
| 蓝图绑定约束 | 仅提供 `workflow_id` 字段，无专门接口 | 新增 `GET/POST /api/v1/hsai/projects/{id}/blueprint` 维护唯一蓝图；或在 `PUT /projects/{id}` 校验 `workflow_id` 唯一性并返回蓝图状态 | 服务端 | 1) 重复绑定返回 409；2) `/summary` 接口同步蓝图字段 |
| 摘要接口字段对齐 | `/summary` 返回 `main_tasks/recurring_tasks` 等字段，与设计稿 `tasks/links` 不一致 | 服务端提供兼容字段（或前端更新解析逻辑）并更新 OpenAPI/WIKI，保证手册与实现一致 | 双方 | 1) 文档/前端与接口字段一致；2) `410_websocket_test_page_manual.md` 成功验收；3) 自动化契约测试通过 |

### 3.4 任务 / 模板 / 依赖
| 缺口 | 当前状态 | 对齐策略 | 责任方 | 验收标准 |
| --- | --- | --- | --- | --- |
| 任务模板 CRUD | 仅 `GET /api/v1/hsai/ai/task-templates` | 扩展 `POST/PUT/DELETE`，payload 与后台表单一致，返回模板版本号 | 服务端 | 1) CRUD 全链路测试；2) 模板更新触发 WS/审计；3) 文档示例齐全 |
| 任务依赖维护 | `task_dependencies` 未暴露接口 | 新增 `/api/v1/hsai/tasks/{id}/dependencies`（POST 添加、DELETE 移除），服务端校验循环依赖 | 服务端 | 1) 接口阻止环形依赖；2) 前端/后台显示最新依赖；3) 日志记录操作员 |
| 任务列表 project 过滤 | 任务列表 API 不支持 `project_id` 查询，需走 `/projects/{id}/tasks` | 增加 `project_id` 过滤参数或提供统一查询，使后台/调试页无需二次调用 | 服务端 | 1) `GET /hsai/tasks?project_id=` 生效；2) 回归测试覆盖 |
| 进度同步 | 仅 `PUT`，需确认 body 格式 | 固化请求体 `{progress: int}`，返回最新任务（含 `progress`/`updated_at`）；允许幂等 | 服务端 | 1) 文档明确；2) 后台调用后 UI 实时刷新 |

### 3.5 计费模块
| 缺口 | 当前状态 | 对齐策略 | 责任方 | 验收标准 |
| --- | --- | --- | --- | --- |
| 公司账单汇总 | 缺 `GET /api/billing/companies` | 新增 `/api/v1/billing/companies/summary`（支持公司/时间过滤），返回余额、消费、最后结算时间 | 服务端 | 1) 返回含 `balance`, `total_usage`, `last_settlement_at`; 2) 后台账单页改用 API；3) 单测覆盖 |
| 积分同步返回 | `PUT /api/v1/users/{id}/credit` 已有，但需确认回包 | 标准化响应 `{success, balance_after, audit_id}`，后台据此刷新余额 & 写入审计 | 服务端 | 1) 接口返回最新余额；2) 审计日志含操作者/备注；3) CHANGELOG 记录 |

### 3.6 审计与通知
| 缺口 | 当前状态 | 对齐策略 | 责任方 | 验收标准 |
| --- | --- | --- | --- | --- |
| 高风险操作审计 ID | 多数接口未返回 | 为删除/批扣/状态迁移等端点增加 `audit_id` 字段，并要求后台提交 `X-Operator-*` | 服务端 | 1) 所列操作均返回审计 ID；2) 审计表可按 ID 追踪详情 |
| 事件通知 | 无统一机制 | 确认是否需要 webhook；如需，设计 `/api/v1/admin/webhooks` 管理订阅，推送关键事件 | 双方 | 1) 事件推送含签名；2) 后台可选择订阅/取消；3) 文档列出事件格式 |

### 3.7 通用事项
| 缺口 | 当前状态 | 对齐策略 | 责任方 | 验收标准 |
| --- | --- | --- | --- | --- |
| OpenAPI 与示例 | 新增接口未同步 | 合并 PR 时强制更新 `openapi.json` 与示例；引入 CI 校验 | 服务端 | 1) CI 校验失败即阻止合并；2) 文档更新在同一提交 |
| 分页参数统一 | 后台使用 `pi/ps`，部分接口使用 `page/size` | 统一命名或支持双写（query alias）；在 SDK 中封装 | 双方 | 1) 后台 & WS 调试页无需转换；2) API 文档注明参数别名 |
| 文档追溯 | 缺乏双向链接 | 每项改动更新 `PROJECTWIKI.md` & `CHANGELOG.md` 并引用本方案章节 | 双方 | 1) WIKI 建立代码↔文档映射；2) Changelog 记录版本 |

## 4. 验证与文档要求
- **验收清单**：更新 `API文档检查报告.md`、`API文档待处理清单.md`，并在 `PROJECTWIKI.md` 的“调试工具 / 接口对齐”小节附本方案链接。
- **测试策略**：单元测试 + 集成测试（FastAPI/TestClient）+ WebSocket 调试页手动回归。计划引入契约测试校验关键接口字段。
- **回滚策略**：每项接口调整需提供向后兼容方案（例如保留旧字段或 Feature Flag）。若上线失败，可通过环境变量关闭新接口或回退至旧路由。

## 5. 责任分配与后续动作
| 事项 | 负责人 | 截止时间（建议） | 备注 |
| --- | --- | --- | --- |
| API 契约评审（客户+公司+任务） | 服务端负责人 @backend-lead | D1 18:00 | 需要后台代表参与确认字段 |
| 鉴权/审计方案实现 | 服务端 | D2 | OAuth2 已上线；审计 ID 返回与文档追踪继续推进 |
| Backoffice 适配（客户/公司/任务页面） | 后台 FE/BE | D3 | 完成 API 替换与回归 |
| 文档同步（OpenAPI + WIKI + 手册） | 文档负责人 | D3 | 引用本方案编号 |
| 验收会 & 发布 | 双方 | D3 下午 | 依据验收清单逐项走查 |

---
> 后续任何接口或文档更新须在提交信息中引用本方案文件，并确保与 `PROJECTWIKI.md`、`CHANGELOG.md` 建立双向链接，以满足文档治理要求。***
