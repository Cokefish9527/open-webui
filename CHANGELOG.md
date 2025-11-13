# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) where applicable.

## [Unreleased]
### Added
- Runtime migration `ensure_materials_storage_schema()` plus SQLite regression test (`backend/test/test_materials_storage_schema.py`) to guarantee OSS 列自动补齐，详见 `PROJECTWIKI.md` 的 “ADR-2025-11-13” 小节。

### Fixed
- 修复 `GET /api/v1/hsai/materials/` 由于缺少 `oss_object_path` 列导致的 `psycopg2.errors.UndefinedColumn`，所有 `HSAIMaterials` 查询现由 `_schema_aware_db()` 自动保障 schema。
