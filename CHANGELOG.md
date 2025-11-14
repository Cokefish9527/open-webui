# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) where applicable.

## [Unreleased]
### Added
- Runtime migration `ensure_materials_storage_schema()` plus SQLite regression test (`backend/test/test_materials_storage_schema.py`) to guarantee OSS 列自动补齐，详见 `PROJECTWIKI.md` “ADR-2025-11-13”。

### Fixed
- 修复 `GET /api/v1/hsai/materials/` 因缺少 `oss_object_path` 列触发 `psycopg2.errors.UndefinedColumn` 的问题，`HSAIMaterials` 查询统一由 `_schema_aware_db()` 保证 schema。
- 引入 Ops Dashboard conversation dispatcher（`backend/open_webui/services/ops_dashboard_ingestor.py` + `main.py:lifespan`），通过队列与优雅停机避免 `_fire_and_forget` 悬挂任务，并补充 `test/test_ops_dashboard_ingestor.py` 覆盖，详见 `PROJECTWIKI.md` “ADR-2025-11-14：Ops Dashboard 异步派发”。
- 修复 `backend/open_webui/routers/hsai_projects.py` 中 `get_project` 多余括号导致的 `SyntaxError`，Uvicorn 启动不再报错，参阅 `PROJECTWIKI.md` “HSAI Companies / Projects Routers”。
- 修复 `GET /hsai/projects/{project_id}/tasks` 缩进错误，`try` 块现正确包裹权限校验及查询逻辑，避免导入期 `IndentationError`。
- 修复 `GET /hsai/projects` 的 `status/pi/ps` 参数描述因编码破损触发的 `SyntaxError: unterminated string literal`，恢复为 UTF-8 中文提示。
- 重新注册 `hsai_companies` FastAPI 路由并移除 `external_admin` 中重复的 `/companies` 定义，`GET /api/v1/hsai/companies` 不再 404，`/api/v1/external/admin/companies` 始终返回 `PaginatedCompanyResponse`；详见 `backend/open_webui/main.py` 与 `routers/external_admin.py`。
