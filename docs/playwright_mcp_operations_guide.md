# Playwright MCP 自动化运行与验证指引

本文档说明如何在本项目中启动 Open WebUI、配置 Playwright MCP 运行环境，并完成 TikTok 账号矩阵自动化的验证流程。

---

## 0. 最优方案概述

1. **架构原则**：继续沿用本仓库的多租户账号/任务/运行记录模型与 MCP Runner，保持与前端、审计、审批流的强绑定；在脚本层吸收 `social-auto-upload` 中的稳健做法（上传进度轮询、错误探测、人类输入节奏等），避免双栈维护。
2. **执行路径**：所有 TikTok 登录/抓取/发布均通过 `PlaywrightMCPService` 调用对应工具（`tiktok_login/fetch_creator/fetch_video/publish_video`），Runner 统一注入 `tenant_id`、`account_id`、`run_id` 元数据，脚本按租户/账号分层保存截图与 Cookie。
3. **多租户保障**：
   - 账号、任务、运行记录表均包含 `tenant_id`，API 在查询/执行前会校验租户隔离。
   - Runner 依赖的凭证、浏览器 Profile、VPN 配置需以 `tenant_id/account_id` 维度划分目录；脚本生成的产物写入 `PLAYWRIGHT_ARTIFACT_DIR/tenant_x/account_y/run_z`，方便追溯。
   - 后续如需引入 `social-auto-upload` 的 Python 逻辑，可通过 CLI/HTTP 旁路调用，并保持上述数据与产物目录约定不变。

---

## 1. 环境准备

1. **Python 3.11.x**
   - 推荐安装官方版本 3.11.9，并确保 `python`, `pip` 在 PATH 中。
   - 如使用项目脚本 `setup_and_start_python311.ps1`，需将 Python 安装在脚本默认查找路径或调整脚本配置。

2. **Node.js ≥ 18**
   - 用于构建/运行前端 Svelte 应用以及 Playwright 运行时。

3. **数据库与缓存**
   - PostgreSQL 作为主数据库。
   - Redis（可选）用于任务队列等扩展功能。

4. **环境变量 (`.env`)**
   在项目根目录复制 `.env.example` 为 `.env`，并补充：
   - 数据库、Redis 连接配置。
   - Playwright MCP 相关变量：
     ```
     # Runner 与后端在同一台主机时可直接使用 127.0.0.1
     PLAYWRIGHT_MCP_ENDPOINT=http://127.0.0.1:8080
     PLAYWRIGHT_CREDENTIAL_ROOT=D:/data/credentials
     SOCIAL_VPN_PROXY_DIR=D:/data/vpn-profiles
     PLAYWRIGHT_ARTIFACT_DIR=playwright-mcp-artifacts
     PLAYWRIGHT_HEADLESS=true
     ```
   - 以上目录需提前创建，确保服务有读写权限。

---

## 2. 后端启动流程

> 若 `setup_and_start_python311.ps1` 因缺少 Python 3.11 而失败，可按以下手动步骤执行。

1. **创建/激活虚拟环境**
   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

2. **安装依赖**
   ```powershell
    # 升级 pip 并安装后端依赖
    pip install --upgrade pip
    pip install -r backend/requirements.txt
   ```

3. **初始化数据库**
   - 在 PostgreSQL 中创建数据库。
   - 执行完整建表脚本：
     ```
     backend/sql/init_scripts/postgresql_full_database_init.sql
     ```
   - 如果是增量部署，可补充运行
     ```
     backend/sql/init_scripts/2025-10-24_social_automation_create.sql
     ```

4. **启动 API 服务**
   ```powershell
   uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
   ```
   - 如需代码热重载，可追加 `--reload`。
   - 运行过程中确认无报错日志，`/health`、`/health/db` 接口可正常访问。

---

## 3. 前端启动流程

1. **安装依赖**
   ```bash
   npm install
   ```

2. **开发模式**
   ```bash
   npm run dev -- --host
   ```
   - 浏览器访问 `http://<host>:5173`。

3. **生产构建 & 预览（可选）**
   ```bash
   npm run build
   npm run preview -- --host
   ```

---

## 4. Playwright MCP Runner 准备

1. **安装依赖**
   ```bash
   cd tool/playwright_mcp_scripts
   npm install playwright
   ```

2. **目录与文件约定**
   - `PLAYWRIGHT_CREDENTIAL_ROOT`：存放账号凭证 JSON，文件名需与 `encrypted_credentials_ref` 对应，推荐按 `tenant_<tenantId>/account_<accountId>.json` 归档便于隔离。示例：
     ```json
     {
       "username": "account@example.com",
       "password": "StrongPassword!",
       "cookies_path": "D:/data/credentials/tiktok_account_cookies.json"
     }
     ```
   - `SOCIAL_VPN_PROXY_DIR`：每个账号的代理配置，如 `wg-losangeles-01.json`：
     ```json
     {
       "server": "http://127.0.0.1:9020",
       "username": "proxy-user",
       "password": "proxy-pass"
     }
     ```
   - `PLAYWRIGHT_ARTIFACT_DIR`：执行后生成截图、HAR 等产物，脚本会自动以 `tenant_<id>/account_<id>/run_<runId>` 结构写入，便于审计。

3. **Runner 部署**
   - 根据实际情况实现一个 MCP Runner（HTTP/WebSocket 服务）调用 `tool/playwright_mcp_scripts` 中的 `execute` 方法。
   - 调通 `/tools` 与 `/execute` 接口，使后端 `PLAYWRIGHT_MCP_ENDPOINT` 能访问。若 Runner 与 WebUI 分属不同主机/容器，请把 `.env` 中的 `PLAYWRIGHT_MCP_ENDPOINT` 替换成 Runner 的可达地址（例如 Docker Compose 网络别名 `http://playwright-mcp-runner:8080`）。

4. **故障排查**
   - 如果后端日志出现 `MCP 请求失败 (HTTP xxx)` 或 `MCP 执行失败 [tool]: ...`，代表 Runner 返回了非 200 状态或 `status != "ok"` 的响应，具体内容已被写入日志信息。
   - 首先确认 Runner 的健康检查 `GET /health` 正常；然后使用 `curl` 或 `Invoke-WebRequest` 调用 `/tools`、`/execute`，核对返回体是否为 JSON 且包含 `status: "ok"`。

---

## 5. 后端接口快速验收

1. **账号管理**
   - 创建账号：
     ```
     POST /api/v1/social/accounts
     {
       "platform": "tiktok",
       "handle": "demo_account",
       "display_name": "Demo",
       "encrypted_credentials_ref": "demo_account",
       "playwright_profile_path": "D:/data/playwright/demo_account",
       "vpn_profile_id": "wg-la-01"
     }
     ```
   - 查询账号：`GET /api/v1/social/accounts`
   - 检查数据库 `social_accounts` 表是否插入记录。

2. **TikTok 自动登录**
   - `POST /api/v1/social/accounts/{id}/tiktok/login`
   - 返回结果中的 `artifacts` 应包含：
     - `screenshot_path`：登录成功截图
     - `cookies_path`：持久化 Cookie 位置
     - `health_status`：账号健康状态（预期 `healthy`）

3. **创作者 / 视频信息获取**
   - 创作者：
     ```
     POST /api/v1/social/accounts/{id}/tiktok/creator
     {
       "target_handle": "target_user"
     }
     ```
   - 视频：
     ```
     POST /api/v1/social/accounts/{id}/tiktok/video
     {
       "video_url": "https://www.tiktok.com/@.../video/..."
     }
     ```
   - 返回 `artifacts` 中应包含对应信息，观察 `tool/playwright_mcp_scripts` 下脚本是否正常执行。

4. **发布任务与执行**
   - 创建发布任务：
     ```
     POST /api/v1/social/posts
     {
       "account_id": "<account_id>",
       "title": "新品上线",
       "caption": "自动化发布示例 #AI",
       "media_assets": {
         "video": "D:/data/videos/demo.mp4",
         "cover": "D:/data/covers/demo.jpg"
       },
       "metadata": {
         "hashtags": ["#AI", "#demo"]
       }
     }
     ```
   - 查看列表：`GET /api/v1/social/posts`
   - 触发发布：`POST /api/v1/social/posts/{post_id}/publish`
   - 预期：
     - `social_posts.status` 先变为 `in_progress`，成功后更新为 `published`。
     - `social_automation_runs` 记录执行详情（运行耗时、截图路径等），并附带 `tenant_id/account_id/run_id` 元数据。
     - `PLAYWRIGHT_ARTIFACT_DIR/tenant_<id>/account_<id>/<run_id>` 下生成对应 run ID 的截图/日志，确认与数据库字段一致。

---

## 6. 前端界面验证

1. 登录 WebUI，侧边栏点击 **“社交账号自动化”**。
2. 在页面中完成以下操作，观察 UI 是否与后端数据同步：
   - 新增账号、查看状态与健康度。
   - 执行自动登录并查看返回日志。
   - 输入创作者账号 / 视频链接，查询信息。
   - 创建发布任务并点击“立即发布”，确认结果区域展示执行信息。

---

## 7. 故障排查建议

1. **Playwright 脚本报错**
   - 查看 Runner 日志与 `playwright-mcp-artifacts` 生成的截图。
   - 检查 TikTok 页面结构是否更新，需要调整 `tool/playwright_mcp_scripts` 中的选择器。

2. **账号登录失败**
   - 确认凭证 JSON 中 `username`、`password`、`cookies_path` 是否填写正确。
   - 检查代理是否可用，必要时更换 VPN/出口 IP。

3. **发布失败**
   - 关注返回 `artifacts` 中的 `publish_status` 与错误信息。
   - 确认视频文件路径存在、账号具备发布权限、TikTok 风控无异常。

4. **Runner 未响应**
   - 检查 `PLAYWRIGHT_MCP_ENDPOINT` 配置是否正确。
   - 手动请求 Runner `/tools`、`/execute` 接口确认服务在线。

---

## 8. 补充建议

1. 针对关键 API 编写 `pytest` 集成测试，可使用 mock MCP 客户端模拟响应。
2. 在 Runner 层加入重试与异常告警，确保平台 UI 第一时间反馈失败原因。
3. 定期更新浏览器指纹策略（User-Agent、Navigator 补丁、时区）降低被识别概率。
4. 对 MCP 运行结果进行审计存档，便于合规与风险排查。

---

以上流程覆盖了启动、配置及 TikTok 自动化的核心验收步骤，可按需扩展至多账号/多平台场景。*** End Patch
