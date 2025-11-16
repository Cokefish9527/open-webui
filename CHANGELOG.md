# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) where applicable.

## [Unreleased]
### Added
- Runtime migration `ensure_materials_storage_schema()` plus SQLite regression test (`backend/test/test_materials_storage_schema.py`) to guarantee OSS 列自动补齐，详见 `PROJECTWIKI.md` 《ADR-2025-11-13》。
- `tool/auto_fix_bom.py`：可根据 `clean_special_chars` 日志或显式路径批量移除 UTF-8 BOM，便于串在字符扫描流程之后自动修复异常文件。
- feat: support WebSocket attachment forwarding——WebSocket 消息现在支持附件转发到 n8n webhook，详见 `PROJECTWIKI.md` 《WebSocket 附件透传》章节。
- POST `/hsai/video-learning/revoke-learning`：允许手动撤销爆款学习，删除 `hsai_business_video_content_learned` 副本并将 `hsai_video_learning_status` 恢复为 `pending`，细节见 `PROJECTWIKI.md` 《爆款学习状态机与撤销流程》。
- `GET|PATCH /api/v1/external/admin/users/{user_id}/permissions` 与 `GET|PATCH /api/v1/external/admin/companies/{company_id}/permissions`：后台客户管理可直接查询/批量更新账号角色与 `settings.permissions`，配套新增 `DEFAULT_CUSTOMER_ROLE`、`CUSTOMER_PERMISSION_TEMPLATE`、`ENABLE_CUSTOMER_PERMISSION_API` 配置，详见 `PROJECTWIKI.md` 《External Admin Router》。
- Playwright 端到端测试脚手架（`tests/playwright`）与 `npm run test:e2e` 流水线：包含自定义 fixtures、WebSocket 健康检查、缺陷报告器与示例场景，配套 `@playwright/test` 依赖。
- `scripts/prepare_test_accounts.py`：启动自动化测试前校验/创建租户“福州华商时代自动化测试”与 `test001@hsai.cc`~`test010@hsai.cc` 账号池，并在 `tests/playwright/artifacts/setup` 输出 JSON 报告，已绑定 `npm run pretest:e2e`。

### Changed
- `hsai_video_learning_status` 枚举现显式包含 `pending`，并追加 `mark_pending`/`upsert_status` 和新测试用例；Redis `video_learning_notification` 监听器重写为统一调用上述助手，杜绝删除行表示 pending 的隐患。
### Fixed
- 修复 `GET /api/v1/hsai/materials/` 因缺少 `oss_object_path` 列触发 `psycopg2.errors.UndefinedColumn` 的问题，`HSAIMaterials` 查询统一由 `_schema_aware_db()` 保证 schema。
- 追加修复：`HSAIMaterialsTable` 仍有 CRUD 直接使用 `get_db()`，`GET /api/v1/hsai/dashboard/recent-activities`/`GET /api/v1/hsai/materials/folders` 在未迁移库上读取 `oss_object_path` 会崩溃；现由 `backend/open_webui/models/hsai_materials.py:_schema_aware_db()` 全面托管，并新增 `backend/test/test_materials_storage_schema.py::{test_schema_guard_invokes_migration_once,test_get_materials_by_user_id_uses_schema_guard}` 防止回归。
- 引入 Ops Dashboard conversation dispatcher（`backend/open_webui/services/ops_dashboard_ingestor.py` + `main.py:lifespan`），通过队列与优雅停机避免 `_fire_and_forget` 悬挂任务，并补充 `test/test_ops_dashboard_ingestor.py` 覆盖，详见 `PROJECTWIKI.md` 《ADR-2025-11-14：Ops Dashboard 异步派发》。
- 修复 `backend/open_webui/routers/hsai_projects.py` 中 `get_project` 多余括号导致的 `SyntaxError`，Uvicorn 启动不再报错，参见 `PROJECTWIKI.md` 《HSAI Companies / Projects Routers》。
- 修复 `GET /hsai/projects/{project_id}/tasks` 缩进错误，`try` 块现正确包裹权限校验及查询逻辑，避免导入期 `IndentationError`。
- 修复 `GET /hsai/projects` 的 `status`/`pi`/`ps` 参数描述因编码破损触发的 `SyntaxError: unterminated string literal`，恢复为 UTF-8 中文提示。
- 重新注册 `hsai_companies` FastAPI 路由并移除 `external_admin` 中重复的 `/companies` 定义，`GET /api/v1/hsai/companies` 不再 404，`/api/v1/external/admin/companies` 始终返回 `PaginatedCompanyResponse`；详见 `backend/open_webui/main.py` 与 `routers/external_admin.py`。
