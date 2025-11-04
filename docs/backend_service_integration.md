# 后台与主业务服务对接设计（2025-10-30）

## 1. 背景与目标
- 目前后台（HSAI Admin）在客户、公司、项目、任务等模块直接读写数据库，导致业务校验缺失、审计困难、不同系统数据容易漂移。
- 主业务服务端（Owen AI）已经托管核心业务逻辑和数据，要求后台改为通过业务接口调用，实现权限一致、流程可追溯。
- 本文梳理后台涉及的核心业务数据表、现有后台页面/接口，并给出“服务端 API ↔ 后台调用”两端协同设计，供后续对接开发参考。

---

## 2. 业务模块与数据表（按数据库划分）

### 2.1 Owen_ai 数据库（PostgreSQL，schema `public`）
| 模块 | 后台页面 / 功能 | 当前数据表 | 说明 |
| --- | --- | --- | --- |
| 客户管理 | `/system/customer/` 列表、增删改、重置密码、启用/禁用 | `"user"`, `auth` | 账号信息与认证信息；密码已统一使用 `bcrypt`（12 轮）。 |

> 说明：后台页面直接操作 `WebUIUser`（表 `"user"`）与 `WebUIAuth`（表 `auth`），已确认线上库为 `Owen_ai`。需在主业务服务提供客户管理 API。

### 2.2 主业务数据库（默认 SQLite `pear.db`，可在生产映射至 MySQL/PG）
| 模块 | 后台页面 / 功能 | 数据模型（SQLAlchemy） | 数据表 |
| --- | --- | --- | --- |
| 公司管理 | `/system/company_project/company` | `Company` | `companies` |
| 项目管理 | `/system/company_project/project` | `Project` | `hsai_projects` |
| 任务管理 | `/system/task/…` | `Job`, `TaskTemplate`, `TaskDependency` 等 | `hsai_tasks`, `task_templates`, `task_dependencies` 等 |
| 计费管理 | `/system/billing/…` | `BillingConfig`, `CompanyCreditLog`, `APIUsageLog` | `billing_config`, `billing_company_credit_log`, `billing_api_usage_log` |
| 任务权限/菜单相关 | `/system/task…` 等 | `Power`, `Role`, `User` 等 | `admin_power`, `admin_role`, `admin_user` 等 |

> 注：后台对以上表也直接 CRUD。若主业务服务端已有对应逻辑，应统一改为接口调用，并只保留必要的只读查询。

---

## 3. 对接设计：服务端 API ↔ 后台调用

### 3.1 统一约束
1. **后台仅通过业务服务端 API 改写业务数据。** 禁止再直接对业务数据库执行写操作（必要只读查询需评审后保留），确保所有变更都能在业务服务端留痕审计。
2. **接口鉴权方案。**
   - **认证流程**：后台通过主业务提供的 OAuth2 Client Credentials（或等价内部签发）获取短期 JWT（建议 5~15 分钟有效），所有请求在 Authorization: Bearer <token> 中携带；客户端密钥必须存放于密钥管理服务，禁止写死在代码或配置。
   - **Token 内容**：JWT 需包含 sub（后台管理员唯一标识）、ud（固定为 dmin-console）、scope（允许的接口范围）与 exp（到期时间）；业务服务端据此进行二次授权。
   - **刷新与撤销**：后台通过 refresh token 或重新获取流程定期轮换 JWT；当管理员被禁用或密钥轮换时，业务端需支持让旧 token 即刻失效（黑名单 / 版本号策略）。
   - **请求完整性**：所有调用强制使用 HTTPS，可按安全等级启用请求签名（timestamp + nonce + HMAC）或双向 TLS。
   - **审计字段**：后台需在 Header 中附带 X-Operator-Id、X-Operator-Name、X-Operator-IP 等信息，业务端回传操作 ID 并写入自身审计表，后台同步记录。
   - **限流与风控**：业务端按 IP、scope、接口进行限流；重置密码、批量删除、调账等敏感操作需二次确认并生成详尽日志，禁止绕过服务写数据库（报表只读除外）。
3. **响应结构统一为 { success, code, msg, data }**，后台沿用现有 	able_api / success_api 适配层解析。
4. **时间格式采用 ISO8601（UTC）或毫秒级时间戳**，后台 _serialize_timestamp 已就绪，无需额外转换。

### 3.2 客户管理 API
| 功能 | 业务端 API（当前实现） | 状态 | 后台调用点 / 备注 |
| --- | --- | --- | --- |
| 查询客户列表 | `GET /api/v1/external/admin/users` | ✅ 已提供 | `/system/customer/data` 按姓名、邮箱、公司筛选 |
| 创建客户 | `POST /api/v1/external/admin/users` | ✅ 已提供 | `/system/customer/save` 需携带初始密码、公司信息 |
| 更新客户资料 | `PUT /api/v1/external/admin/users/{user_id}` | ✅ 已提供 | `/system/customer/update`，保持字段映射一致；未传 `password` 时沿用原密码 |
| 删除客户 | `DELETE /api/v1/external/admin/users/{user_id}` | ✅ 已提供 | `/system/customer/remove/{id}`，删除前需由业务端校验依赖 |
| 调整积分 | `PUT /api/v1/users/{user_id}/credit` | ✅ 已提供 | 由计费模块调用，返回最新余额 |
| 重置密码 | （缺失） | ⚠️ 待业务补充 | `/system/customer/resetPassword` 仍需保留占位逻辑 |
| 启用/禁用账号 | （缺失） | ⚠️ 待业务补充 | `/system/customer/enable` / `/system/customer/disable` 待接业务端开关接口 |

### 3.3 公司管理 API
| 功能 | 业务端 API（当前实现） | 状态 | 备注 |
| --- | --- | --- | --- |
| 列表查询 | （缺失） | ⚠️ 待业务补充 | 后台暂仍直接访问 `companies` 表，仅限只读 |
| 创建公司 | （缺失） | ⚠️ 待业务补充 | 需支持公司基本信息、负责人设置 |
| 更新公司 | （缺失） | ⚠️ 待业务补充 | 应包含联系人、状态、配置 JSON 等字段 |
| 删除公司 | （缺失） | ⚠️ 待业务补充 | 需服务端执行依赖校验（项目、任务、计费） |

### 3.4 项目管理 API
| 功能 | 业务端 API（当前实现） | 状态 | 说明 |
| --- | --- | --- | --- |
| 列表查询 | `GET /api/v1/hsai/projects/` | ✅ 已提供 | 支持分页、公司 ID、状态、负责人等过滤 |
| 创建项目 | `POST /api/v1/hsai/projects/` | ✅ 已提供 | 需传入公司 ID、业务名、负责人、配置 JSON |
| 获取详情 | `GET /api/v1/hsai/projects/{project_id}` | ✅ 已提供 | 返回项目基础信息及关联统计 |
| 更新项目 | `PUT /api/v1/hsai/projects/{project_id}` | ✅ 已提供 | 更新描述、状态、负责人、配置 |
| 删除项目 | `DELETE /api/v1/hsai/projects/{project_id}` | ✅ 已提供 | 服务端检查未完成任务后允许删除 |
| 项目任务查看 | `GET /api/v1/hsai/projects/{project_id}/tasks` | ✅ 已提供 | 后台项目详情页内嵌任务列表 |

### 3.5 任务管理 / 模板 / 依赖 API
| 功能 | 业务端 API（当前实现） | 状态 | 说明 |
| --- | --- | --- | --- |
| 任务列表 / 过滤 | `GET /api/v1/hsai/tasks/` | ✅ 已提供 | 支持项目、负责人、状态、业务标签等查询 |
| 创建任务 | `POST /api/v1/hsai/tasks/` | ✅ 已提供 | 需传入配置 JSON、优先级、模板引用等 |
| 查看任务详情 | `GET /api/v1/hsai/tasks/{task_id}` | ✅ 已提供 | 返回进度、配置、依赖等信息 |
| 更新任务 | `PUT /api/v1/hsai/tasks/{task_id}` | ✅ 已提供 | 更新描述、配置、负责人、标签等 |
| 状态操作 | `POST /api/v1/hsai/tasks/{task_id}/start`<br>`POST /api/v1/hsai/tasks/{task_id}/cancel`<br>`POST /api/v1/hsai/tasks/{task_id}/assign` | ✅ 已提供 | 覆盖启动、取消、指派等高频动作 |
| 更新进度 | `PUT /api/v1/hsai/tasks/{task_id}/progress` | ✅ 已提供 | 支持百分比与状态同步 |
| 模板列表 | `GET /api/v1/hsai/ai/task-templates` | ✅ 已提供 | 返回模板元数据，供后台下拉使用 |
| 模板创建 / 更新 / 删除 | （缺失） | ⚠️ 待业务补充 | 后台模板维护界面需等待业务端补齐 POST/PUT/DELETE 接口 |
| 依赖管理 | （缺失） | ⚠️ 待业务补充 | 需提供创建/删除依赖的接口以替换本地 SQL 操作 |

### 3.6 计费管理 API
| 功能 | 业务端 API（当前实现） | 状态 | 说明 |
| --- | --- | --- | --- |
| 计费配置 | `GET /api/v1/billing/billing/configs`<br>`POST /api/v1/billing/billing/configs`<br>`PUT /api/v1/billing/billing/configs/{config_id}`<br>`DELETE /api/v1/billing/billing/configs/{config_id}` | ✅ 已提供 | 维护价格、配额、折扣等配置；注意双重 `billing` 前缀 |
| 使用记录 | `GET /api/v1/billing/billing/usage-logs`<br>`POST /api/v1/billing/billing/usage-logs` | ✅ 已提供 | 后台使用日志列表 / 导入 |
| 会话使用统计 | `GET /api/v1/billing/billing/usage-logs/session/{session_id}`<br>`GET /api/v1/billing/billing/usage-logs/session/{session_id}/total` | ✅ 已提供 | 按会话聚合，供详情页使用 |
| 积分流水 | `GET /api/v1/credit/logs` | ✅ 已提供 | 返回公司/用户积分调整历史 |
| 积分工单 | `POST /api/v1/credit/tickets` | ✅ 已提供 | 产生日志型调账请求 |
| 直接调账 | `PUT /api/v1/users/{user_id}/credit` | ✅ 已提供 | 后台调账主通道，返回最新余额 |
| 公司积分汇总 | （缺失） | ⚠️ 待业务补充 | 原 `GET /api/billing/companies` 需求未覆盖，需确认是否通过报表替代 |

---

## 4. 后台管理系统改造要点
1. **HTTP 客户端封装**：在 `applications/common/utils/api_client.py` 扩展/重构，支持向 Owen AI 服务发起 REST 调用，统一处理认证、错误码、重试等。
2. **页面适配**：将现有 SQLAlchemy 查询替换为 API 调用；对于分页接口，后台仍调用 `table_api` 返回前端习惯的结构。
3. **缓存与兜底**：对于只读数据（如公司/项目下拉），可在后台缓存一定时间，但写操作必须走 API。
4. **权限映射**：后台的 `Power`/`Role` 控制显示与按钮；业务权限由服务端 API 再次鉴权，避免绕过限制。
5. **日志与追踪**：后台提交操作时携带当前管理员 ID、账号、IP 等信息；服务端回写操作日志 ID，后台可持久保存以便溯源。

---

## 5. 后续迁移步骤
1. **与业务团队确认接口契约**（字段、鉴权、错误码、审计需求），并形成正式 API 文档。
2. **搭建联调环境**：为后台提供测试 API Endpoint，并配置 `WEBUI_DB_URL`、主业务 API URL/Key。
3. **逐模块改造**（建议顺序：客户 → 公司 → 项目 → 任务 → 计费），每完成一个模块即可切换到接口模式并回归测试。
4. **清理直连代码**：完成迁移后，删除后台中直接操作业务表的逻辑，仅保留必要的只读查询或改为 API。
5. **监控与告警**：上线后监控 API 调用成功率、时延、错误码；关键接口失败需告警并提供回退机制。

---

## 6. 附录：相关模型/类引用
- `applications/models/webui_user.py` → `public."user"` / `public.auth`（Owen_ai）
- `applications/models/company.py` → `companies`, `hsai_projects`
- `applications/models/job.py` → `hsai_tasks`
- `applications/models/billing.py` → `billing_config`, `billing_company_credit_log`, `billing_api_usage_log`
- `applications/models/admin_power.py` 等 → 后台自身权限系统

以上设计为后台改造提供基础标准，后续需结合实际 API 定义、鉴权方式、容错策略进一步细化。欢迎业务与后台共同评审后落地。***
