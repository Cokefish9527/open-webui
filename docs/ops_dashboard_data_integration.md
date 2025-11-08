# 管理端首页数据对接清单

> 本文档为运营化首页改版的数据落地指南，包含需要新增的数据表、字段字典与跨团队对接事项。所有新增依赖请在执行过程中持续补充，保持单一真相源。

## 1. 数据表设计

### 1.1 conversation_sessions（会话主表）
```sql
CREATE TABLE conversation_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    company_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    channel VARCHAR(32) NOT NULL,                -- web / api / wechat / sms
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    duration_seconds INT,
    turn_count INT DEFAULT 0,
    is_bounced BOOLEAN DEFAULT FALSE,            -- true = 1 轮内结束/用户未回复
    max_latency_ms INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_conv_sessions_company_started ON conversation_sessions(company_id, started_at DESC);
CREATE INDEX idx_conv_sessions_user_started ON conversation_sessions(user_id, started_at DESC);
```

**用途**：支撑首页 KPI「会话质量」、「活跃度漏斗」等指标，提供最短/最长会话、跳出率等数据。

### 1.2 conversation_messages（会话消息表，可选）
```sql
CREATE TABLE conversation_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES conversation_sessions(session_id),
    seq INT NOT NULL,
    role VARCHAR(16) NOT NULL,                   -- user / assistant / system
    content JSONB,
    tokens INT,
    latency_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_conv_messages_session_seq ON conversation_messages(session_id, seq);
```

**用途**：用于更细粒度的轮次分析（平均轮次、响应延迟）。如已有消息存储，可通过视图映射。

### 1.3 user_activity_daily（活跃度日表）
```sql
CREATE TABLE user_activity_daily (
    stat_date DATE NOT NULL,
    company_id BIGINT,
    user_id BIGINT,
    login_count INT DEFAULT 0,
    api_call_count INT DEFAULT 0,
    conversation_count INT DEFAULT 0,
    PRIMARY KEY (stat_date, user_id)
);
CREATE INDEX idx_user_activity_daily_company_date ON user_activity_daily(company_id, stat_date);
```

**用途**：DAU/WAU、活跃公司、活跃漏斗的基础数据，由 ETL/定时任务写入。

### 1.4 system_metrics_hourly（系统稳定性指标）
```sql
CREATE TABLE system_metrics_hourly (
    stat_hour TIMESTAMP NOT NULL,
    metric VARCHAR(64) NOT NULL,                 -- job_success_rate / api_5xx / avg_latency
    value NUMERIC(10,4) NOT NULL,
    dimension JSONB,                             -- {"service": "billing-api"}
    PRIMARY KEY (stat_hour, metric, COALESCE((dimension->>'service'), 'all'))
);
```

**用途**：支撑首页「系统稳定性」卡片与告警流，指标来源 JobLog、Nginx、APM、限流系统。

## 2. 指标字段字典
| 指标 | 字段来源 | 说明 |
| --- | --- | --- |
| 积分用量趋势 | `company_credit_logs`（既有） | 聚合 daily sum(consumed_amount)；剩余额度来自公司积分表 |
| 活跃用户数 | `user_activity_daily.login_count` | stat_date 取当天，count(distinct user_id) |
| 活跃公司数 | `user_activity_daily.conversation_count` | company_id 去重 |
| 计划任务成功率 | `system_metrics_hourly` metric=`job_success_rate` | 由 JobLog 聚合 |
| API 5xx | `system_metrics_hourly` metric=`api_5xx` | 来源 Nginx/APM |
| 对话跳出率 | `conversation_sessions.is_bounced` | 计算 bounced / total |
| 最短/最长会话 | `conversation_sessions.duration_seconds` | min/max 取最近 7 天 |

> 若指标需要额外维度（渠道、行业等），请在 `dimension` JSON 中补充并在此表维护解释。

## 3. 对接责任清单
| 模块 | 负责团队 | 数据来源 | 交付内容 | 更新频率 | 里程碑 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| 会话日志 | 业务研发 | 聊天服务或第三方 Bot | 建表 + 回填 90 天历史；实时写入/同步方案 | 实时 | T+5 完成历史；T+7 接入实时 | 需 session_id 统一生成规范 |
| 活跃度统计 | 数据/BI | 登录日志、API Gateway 日志 | 生成 `user_activity_daily`，配置 ETL | 每日 T+1 | T+3 完成调度 | 登录日志如在 ELK 需导出任务 |
| 系统稳定性 | 运维/平台 | JobLog、APM、限流系统 | 采集写入 `system_metrics_hourly`，提供告警 Webhook | 每小时 | T+4 完成初版 | 指标字典需在 wiki 同步 |
| 积分数据 | 计费小组 | Billing DB | 复用现有日志，提供聚合视图 | 实时 | 已具备 | 需确认性能上限 |
| CRM/回访 | 运营 | CRM 系统 | 提供回访入口/链接 | 视业务 | T+7 | 暂无接口时可先放说明链接 |

## 4. 接口与权限
- 统一新增 `GET /system/index/ops_dashboard`，由后台汇总 KPI、排行榜、告警等数据。
- 根据角色控制卡片可见性：
  - 运营角色：全部可见；
  - 计费/财务：仅积分相关卡片；
  - 技术/运维：系统稳定性、告警流。
- 若接口调用外部服务（CRM、APM），需通过 service account 或已有凭证接入，禁止在仓库存储密钥，遵循 `.env.example` / CI 注入策略。

## 5. 执行节奏
1. 表结构评审（DBA/后端/数据） → 建表脚本进入 migrations。
2. 数据导入 & ETL：完成历史数据回填、调度配置，输出校验报表。
3. API / 前端联调：`/system/index/ops_dashboard` 接口完成后再进行页面开发。
4. 文档维护：
   - 在 `PROJECTWIKI.md` 的「数据模型」「运维指标」「首页方案」章节引用本文件；
   - 追加新数据依赖时，同步更新本清单与 WIKI。

---

如对字段定义、同步机制有任何变动，请在文档末尾追加“更新记录”，并同步至相关负责人。
