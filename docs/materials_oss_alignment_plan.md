# 素材管理 OSS 对齐方案（待执行）

## 背景
- 目标：素材清单目录与 OSS 实际文件结构保持一致，用户看到的目录=后台发布的场景树，文件列表= OSS 真实内容。
- 进展：模型已引入 `oss_object_path`，`_store_material_file()` 支持自定义对象键，清单节点可获取 `scene_name`。
- 未完成：上传路径改造、OSS 列表/缓存、差异同步、文档更新。

## 待办拆解
### 1. 上传路径改造
1.1 单文件上传：
- 依据 `folder_id` 对应的清单节点生成：
  - `company_segment = _resolve_company_display(user)`（允许中文，清洗非法字符）。
  - `scene_segment = scene_name/scene_code`。
  - `object_key = {company_segment}/{scene_segment}/{项目名称+扩展名}`。
- 将 `object_key` 传入 `_store_material_file(oss_object_path=…)`，并写入 `material_metadata['oss_object_path']`、`HSAIMaterialForm.oss_object_path`。

1.2 ZIP 上传：
- 对压缩包内每个文件使用同样规则生成对象键；
- 若 OSS 上传成功但 DB 写入失败，沿用现有回滚逻辑删除 OSS 对象。

### 2. OSS 列表与差异同步
2.1 `oss_material_repository`：
- 在现有 S3 封装上增加 30s 内存缓存，Key=公司ID+场景code；上传成功后立即失效对应缓存，避免协同账号看到旧数据。

2.2 `/hsai/materials/folders`：
- 清单树生成后，并行调用 OSS `list_objects_v2` 拉取真实文件；
- 节点字段新增 `oss_object_path / oss_last_modified / sync_status`。`sync_status` 取值：`in_sync`、`oss_only`、`db_only`、`unknown`。

2.3 `/hsai/materials`：
- 查询 `hsai_materials` 得到结构化信息；
- 同步 OSS 列表 → 以 OSS 为准合并：
  - OSS 有 / DB 无 → 异步写入 `hsai_materials`，响应中 `source=oss_only`；
  - DB 有 / OSS 无 → `source=db_only` 并提示需清理处理；
- 响应体新增 `sync_status`、`source` 字段。

2.4 `/hsai/materials/{id}/download`：
- 优先使用 `oss_object_path` 生成签名 URL；若缺失则尝试 `oss_key` 或重新 list。

### 3. 文档与技术债务
- `docs/素材清单管理.md`：补充 OSS 命名规则、差异同步流程、`sync_status` 含义。
- `PROJECTWIKI.md`：在“素材清单驱动改造”章节补充本次改动，并记录技术债务（清单变更触发 OSS 路径迁移方案待定）。

### 4. 验证计划
- 单元 / 脚本：mock `oss_material_repository` 验证 `sync_status`，对 `_build_project_filename` 等函数编写测试。
- 手动：上传/ZIP 上传后检查 OSS 目录；多账号并发上传后立即刷新列表；删除/新增 OSS 文件验证差异同步与异步落库。

## 风险与缓解
- OSS 列表成本高 → 通过前缀分页+短期缓存+并发控制降低成本，如有需要引入后台定时同步。
- 异步落库失败 → 记录日志并加入简单重试队列，后续可接入任务系统。
- 回滚方案 → 预留 `LEGACY_OSS_PATH` 配置，紧急情况下可退回旧的 `company/user/hash` 组织策略并跳过 OSS 合并逻辑。

