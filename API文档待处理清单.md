
### 模型管理
- [x] 完善模型管理相关接口的中文描述

### 配置管理
- [x] 完善配置管理相关接口的中文描述

### 管线管理
- [x] 完善管线管理相关接口的中文描述

### 任务管理
- [x] 完善任务管理相关接口的中文描述

# API文档待处理清单

## 说明
本清单用于跟踪API文档的改进工作。已完成的项目请在 `[ ]` 中标记为 `[x]`。

## 计费管理API (billing)

### 重复标签问题
- [x] 修复重复标签问题：接口同时使用了"billing"和"计费管理"标签

### 接口完整性检查
- [x] 获取用户所属公司的积分余额 (`GET /api/v1/billing/billing/user/credit`)
- [x] 获取计费配置列表 (`GET /api/v1/billing/billing/configs`)
- [x] 创建计费配置 (`POST /api/v1/billing/billing/configs`)
- [x] 获取计费配置详情 (`GET /api/v1/billing/billing/configs/{config_id}`)
- [x] 更新计费配置 (`PUT /api/v1/billing/billing/configs/{config_id}`)
- [x] 删除计费配置 (`DELETE /api/v1/billing/billing/configs/{config_id}`)
- [x] 获取API使用记录列表 (`GET /api/v1/billing/billing/usage-logs`)
- [x] 创建API使用记录 (`POST /api/v1/billing/billing/usage-logs`)
- [x] 根据会话ID获取API使用记录 (`GET /api/v1/billing/billing/usage-logs/session/{session_id}`)
- [x] 根据会话ID获取总消耗积分 (`GET /api/v1/billing/billing/usage-logs/session/{session_id}/total`)

## 全局API文档改进任务

### 中文描述完整性
- [ ] 为缺少中文描述的330个接口添加中文摘要和描述
  - 进度：已完成 auths/对话管理/文件管理/知识库管理/模型管理/配置管理/管线管理/任务管理 的关键端点补充；仍有 330 个接口在 openapi.json 中未体现中文描述（待统一重新生成或补写装饰器描述）。

### 接口文档标准化
- [x] 统一接口文档格式，确保所有接口都有：
  - [x] 清晰的接口摘要
  - [x] 详细的接口描述
  - [x] 完整的请求参数说明
  - [x] 明确的响应结构说明
  - [x] 可能的错误码说明

### 重复标签处理
- [x] 检查并处理所有重复标签问题，确保标签使用一致性

## HSAI相关API

### HSAI 任务管理
- [x] 完善循环任务相关接口的描述：
  - [x] 启动循环任务 (`POST /api/v1/hsai/tasks/{task_id}/recurring/activate`)
  - [x] 暂停循环任务 (`POST /api/v1/hsai/tasks/{task_id}/recurring/pause`)
  - [x] 恢复循环任务 (`POST /api/v1/hsai/tasks/{task_id}/recurring/resume`)
  - [x] 循环任务交接外部控制 (`POST /api/v1/hsai/tasks/{task_id}/recurring/handover`)
  - [x] 同步循环任务状态 (`POST /api/v1/hsai/tasks/{task_id}/recurring/sync`)
  - [x] 循环任务状态日志 (`GET /api/v1/hsai/tasks/{task_id}/recurring/logs`)
  - [x] 模拟循环任务调度 (`POST /api/v1/hsai/tasks/{task_id}/simulate`)

### HSAI 素材管理
- [x] 检查并完善所有HSAI素材管理接口的中文描述

### HSAI 项目管理
- [x] 修复项目管理接口中的乱码问题
- [x] 完善项目管理接口的中文描述

## 其他API模块

### 用户管理
- [x] 完善用户管理相关接口的中文描述

### 对话管理
- [x] 完善对话管理相关接口的中文描述

### 知识库管理
- [x] 完善知识库管理相关接口的中文描述

### 工具管理
- [x] 完善工具管理相关接口的中文描述

## 技术债处理

### 重复接口清理
- [x] 检查并清理重复的外部管理接口：
  - [x] 创建用户接口重复
  - [x] 获取用户列表接口重复
  - [x] 更新用户接口重复
  - [x] 删除用户接口重复
  - [x] 创建组织接口重复
  - [x] 获取组织列表接口重复
  - [x] 更新组织接口重复
  - [x] 删除组织接口重复
  - [x] 分配用户到组织接口重复
  - [x] 从组织移除用户接口重复
