# HSAI 素材管理与 FFmpeg OSS 服务对齐实施方案（2025-11-05）

## 1. 背景
- 需求基准：
  - 《318-HSAI 接口模块功能描述文档》要求素材模块提供文件夹树、OSS 直传、缩略图/下载直链、独立搜索与统计接口等能力。
  - 《OwenAI_FFmpeg_API》定义了 `http://192.168.20.31:8082` 上的 `/oss` 系列接口，用于生成签名下载链接、上传对象、遍历目录树等操作。
- 现状回顾（2025-11-05）：
  - `backend/open_webui/routers/hsai_materials.py` 已实现基础的上传、列表、统计、回收站管理等功能，但仍以本地存储为默认模式。
  - OSS Upload 通过 `boto3` 兼容接口实现，缺少与 FFmpeg 服务的联动，也未输出签名下载链接。
  - 搜索接口与需求文档存在路径和字段能力差距，未匹配标签或分类信息。

## 2. 差距列表
| 编号 | 差距描述 | 影响 |
| ---- | -------- | ---- |
| GAP-01 | 缺少显式的 `GET /hsai/materials/search`、`GET /hsai/materials/stats` 路由，当前仅通过 `/` + query 参数内部判定 | 与需求文档不符、难以对外发布接口文档 |
| GAP-02 | 检索范围仅覆盖名称/描述，未支持标签（`tags`）与分类代码（`scene_code`、`technique_code`、`properties_code`） | 无法满足“标签匹配”场景，搜索体验不足 |
| GAP-03 | 下载接口返回 `s3://` 或 Base64 包装 URL，未生成 CDN/签名直链，且未复用 `/oss/download-url` | 前端/第三方服务无法直接访问素材，权限控制缺失 |
| GAP-04 | 上传流程先写入本地再转存 OSS，缺少分片/断点机制，并未调用 FFmpeg `/oss/upload` | 大文件效率低，转码服务无法感知素材 |
| GAP-05 | 配置层缺少 FFmpeg API 端点 & 密钥，`STORAGE_PROVIDER` 默认 local，OSS 关键参数未填充 | 环境切换困难，无法面向生产启用 OSS |

## 3. 目标定义
1. 对齐接口形态：补齐 `/search` 与 `/stats`，保持返回体与文档一致。
2. 强化检索能力：实现标签、分类字段的模糊搜索，返回 `properties_code` 为列表。
3. 提供安全下载：在 OSS 模式下生成带有效期的 HTTPS 签名链接；可根据配置切换 CDN 域名。
4. 打通 FFmpeg 服务：新增 `FFMPEG_API` 客户端，复用其 `/oss/*` 系列能力处理上传、目录树与对象删除。
5. 配置与治理：填写 OSS 控制参数，规范密钥注入，形成回滚与验证策略。

## 4. 实施步骤
### 4.1 接口补齐（负责人：后端）
1. 新增 `@router.get("/search")` 与 `@router.get("/stats")` 路由，复用既有分页/统计逻辑，保证响应字段与 318 文档一致。
2. 更新 FastAPI OpenAPI 元数据（保持 `summary`、`response_model` 与文档同步），同步生成文档/接口清单。

### 4.2 搜索能力增强
1. 扩展 `HSAIMaterials.search_materials()`，新增对 `tags`（JSON 列）、`scene_code`、`technique_code`、`properties_code` 的匹配条件。
2. 输出 `properties_code` 为数组；对 tags 使用 `ANY`/`ilike`，避免性能问题时可考虑倒排索引或外部搜索引擎。
3. 增加必要索引（PostgreSQL：`GIN` -> `tags`，B-tree -> `scene_code` 等），并添加 Alembic migration。

### 4.3 下载签名 URL
1. 在 `S3StorageProvider` 内新增 `generate_download_url(key, expires)` 方法，使用 `boto3.generate_presigned_url`；当配置启用 CDN 域名时替换主机名。
2. `GET /hsai/materials/{id}/download`：
   - OSS 模式：调用上述方法，根据请求参数决定有效期（默认 900s）。
   - Local 模式：维持原路径回传逻辑。
3. 为避免历史数据缺少 `oss_key`：在获取时若无 `oss_key`，尝试从 `file_path` 解析。

### 4.4 FFmpeg OSS 服务集成
1. 新建 `open_webui/integrations/ffmpeg_oss.py`（示例）：
   - 统一读取 `FFMPEG_API_BASE_URL`、`FFMPEG_API_KEY`。
   - 封装 `upload_file(stream, path)`, `generate_download_url(object_name, expires)`, `list_tree(directories)`。
2. 上传逻辑调整：
   - 当启用 OSS 模式且配置 `USE_FFMPEG_OSS=true` 时，优先调用 FFmpeg `/oss/upload`，成功后写入返回的 OSS 路径。
   - 失败则回退到本地 `boto3` 上传，确保可用性。
3. 新增定时任务或后台脚本对比本地 `hsai_materials` 元数据与 `/oss/tree`，校验漂移。

### 4.5 配置与密钥管理
1. `.env` / 环境变量补齐（敏感信息走密钥管控平台）：
   ```env
   STORAGE_PROVIDER=s3
   S3_REGION_NAME=oss-cn-hangzhou
   S3_BUCKET_NAME=hsai-hz
   S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com
   S3_KEY_PREFIX=hsai/materials/
   S3_ADDRESSING_STYLE=virtual
   S3_USE_ACCELERATE_ENDPOINT=False
   S3_ENABLE_TAGGING=True
   FFMPEG_API_BASE_URL=http://192.168.20.31:8082
   FFMPEG_API_KEY=${INJECT_FROM_SECRETS}
   FFMPEG_API_TIMEOUT=30
   USE_FFMPEG_OSS=true
   ```
2. 将 AccessKey、SecretKey、API Key 通过 Vault/Secrets Manager 动态注入，禁止写入仓库。
3. 更新 `docs/600-699_部署运维/运维手册/612-OSS配置说明.md` 与 `PROJECTWIKI.md`，保持存储策略一致。

### 4.6 验证计划
| 验证项 | 检查内容 | 工具/步骤 |
| ------ | -------- | -------- |
| 单元测试 | 搜索（含标签/分类）、下载签名 URL 生成、FFmpeg 客户端错误处理 | pytest / httpx mock |
| 集成测试 | 上传 → 列表 → 下载 → 删除全链路；调用 FFmpeg `/oss/download-url` | 调试环境 + Postman |
| 性能测试 | 100MB 以上文件上传耗时（直传 vs 本地中转），并发搜索 | locust/自研脚本 |
| 安全检查 | 签名 URL 在过期后失效；未持有授权头无法调用 `/oss` | 调整 expires，复测 |

### 4.7 回滚策略
1. 配置层回滚：将 `STORAGE_PROVIDER` 切回 `local`，禁用 `USE_FFMPEG_OSS` 与相关环境变量。
2. 代码回滚：保持改动集中在独立提交，必要时 `git revert`；数据库索引/迁移需提供逆向脚本。
3. 数据复核：回滚后执行素材列表核查，确保原有文件可访问。

## 5. 风险与缓解
- **大文件上传性能**：若 FFmpeg 服务压力过大，可在初期保留本地直传为回退机制，并结合分片上传优化。
- **签名 URL 泄露**：通过短过期时间 + 用户态鉴权结合；必要时追加防盗链策略（Referer / 防火墙）。
- **OSS 元数据漂移**：引入定期一致性校验，出现缺失时自动重建。
- **搜索性能**：标签/分类匹配涉及 JSON 查询，建议在 PostgreSQL 部署 `GIN` 索引，并监控慢查询。

## 6. 时间线（预估）
| 阶段 | 任务 | 负责人 | 预计时长 |
| ---- | ---- | ------ | -------- |
| S1 | 接口补齐、搜索扩展、单元测试 | 后端 | 2 天 |
| S2 | FFmpeg 客户端封装、上传改造、集成测试 | 后端 | 3 天 |
| S3 | 配置落地、运维说明更新、性能验证 | 运维/后端 | 2 天 |
| S4 | 试运行与监控调优 | DevOps | 1 周（灰度阶段） |

## 7. 验收标准（DoD）
- `/hsai/materials/search`、`/hsai/materials/stats` 在 OpenAPI 与实际行为一致，返回体覆盖文档字段。
- 搜索结果支持名称/描述/标签/分类多条件匹配，并通过单元测试覆盖。
- OSS 模式下下载返回 HTTPS 签名链接，过期后不可访问。
- FFmpeg `/oss/upload`、`/oss/download-url` 集成验证通过，失败自动回退。
- `PROJECTWIKI.md`、运维手册同步更新，配置项在所有部署环境正确生效。

```mermaid
flowchart LR
    A[用戶上传素材] --> B{STORAGE_PROVIDER}
    B -->|local| C[本地磁盘保存]
    B -->|s3/oss| D{USE_FFMPEG_OSS}
    D -->|true| E[调用 FFmpeg /oss/upload]
    D -->|false| F[boto3 上传 S3/OSS]
    E --> G[写入素材元数据]
    F --> G
    G --> H[GET /hsai/materials/search]
    G --> I[GET /hsai/materials/{id}/download]
    I --> J[生成签名 URL /oss/download-url]
```
