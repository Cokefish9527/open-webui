# 基于任务的对话管理系统准备工作文档

根据 [96-基于任务的对话管理系统优化方案.md](96-基于任务的对话管理系统优化方案.md) 方案，整理系统实施前需要完成的准备工作。

## 1. 数据库准备

### 1.1 表结构要求

确保以下表结构已正确创建并包含所有必要字段：

#### companies表（公司表）
- id: VARCHAR NOT NULL PRIMARY KEY
- name: VARCHAR NOT NULL
- description: TEXT
- owner_user_id: VARCHAR NOT NULL
- company_info: JSON
- status: VARCHAR DEFAULT 'active'
- config: JSON
- created_at: BIGINT
- updated_at: BIGINT

#### user表（用户表）
- id: VARCHAR(255) NOT NULL PRIMARY KEY
- name: VARCHAR(255) NOT NULL
- email: VARCHAR(255) NOT NULL
- role: VARCHAR(255) NOT NULL
- profile_image_url: TEXT NOT NULL
- api_key: VARCHAR(255)
- created_at: INTEGER NOT NULL
- updated_at: INTEGER NOT NULL
- last_active_at: INTEGER NOT NULL
- settings: TEXT
- info: TEXT
- oauth_sub: TEXT
- info_collection_completed: INTEGER DEFAULT '0'
- business_name: TEXT
- **company_id: VARCHAR(255) REFERENCES companies(id)** （新增字段）

#### hsai_projects表（项目表）
- id: VARCHAR NOT NULL PRIMARY KEY
- name: VARCHAR NOT NULL
- description: TEXT
- business_name: VARCHAR NOT NULL
- company_info: JSON
- user_id: VARCHAR NOT NULL
- status: VARCHAR DEFAULT 'active'
- config: JSON
- created_at: BIGINT
- updated_at: BIGINT
- **company_id: VARCHAR(255) REFERENCES companies(id)** （新增字段）

#### hsai_tasks表（任务表）
- id: VARCHAR NOT NULL PRIMARY KEY
- title: VARCHAR NOT NULL
- description: TEXT
- task_type: VARCHAR NOT NULL
- status: VARCHAR NOT NULL
- user_id: VARCHAR NOT NULL
- chat_id: VARCHAR
- config: JSON
- inputs: JSON
- outputs: JSON
- workflow_id: VARCHAR
- parent_task_id: VARCHAR
- progress: BIGINT NOT NULL
- started_at: BIGINT
- completed_at: BIGINT
- error_message: TEXT
- retry_count: BIGINT NOT NULL
- priority: BIGINT
- tags: JSON
- created_at: BIGINT
- updated_at: BIGINT
- assignee_id: VARCHAR
- collaborators: JSON
- shared_sessions: JSON
- **project_id: VARCHAR REFERENCES hsai_projects(id)** （新增字段）
- **task_category: VARCHAR** （新增字段）
- **prompt_config: JSON** （新增字段）

### 1.2 索引要求

确保创建以下索引以提高查询性能：
- ix_companies_owner_user_id ON companies (owner_user_id)
- ix_companies_status ON companies (status)
- ix_hsai_projects_user_id ON hsai_projects (user_id)
- ix_hsai_projects_status ON hsai_projects (status)
- ix_hsai_tasks_assignee_id ON hsai_tasks (assignee_id)
- ix_hsai_tasks_type ON hsai_tasks (task_type)
- ix_hsai_tasks_status ON hsai_tasks (status)
- ix_hsai_tasks_user_id ON hsai_tasks (user_id)
- ix_hsai_tasks_chat_id ON hsai_tasks (chat_id)
- ix_hsai_tasks_priority ON hsai_tasks (priority)

## 2. 功能模块准备

### 2.1 用户与公司管理模块
- 用户注册时自动创建或关联公司逻辑
- 公司信息收集流程
- 默认项目自动创建机制

### 2.2 项目管理模块
- 项目创建时自动创建主线任务逻辑
- 项目状态管理
- 项目与公司的关联关系维护

### 2.3 任务管理模块
- 主线任务模板定义与管理
- 任务状态管理（pending, in_progress, completed, failed, cancelled）
- 任务与项目、用户的关联关系维护
- 任务优先级管理

### 2.4 工作流集成模块
- 与n8n工作流引擎的集成
- 任务完成状态更新机制
- 工作流信号监听与处理

## 3. API接口准备

### 3.1 公司管理接口
- GET /hsai/companies - 获取公司列表
- POST /hsai/companies - 创建公司
- GET /hsai/companies/{company_id} - 获取公司详情
- PUT /hsai/companies/{company_id} - 更新公司
- DELETE /hsai/companies/{company_id} - 删除公司

### 3.2 项目管理接口
- GET /hsai/projects - 获取项目列表
- POST /hsai/projects - 创建项目
- GET /hsai/projects/{project_id} - 获取项目详情
- PUT /hsai/projects/{project_id} - 更新项目
- DELETE /hsai/projects/{project_id} - 删除项目
- GET /hsai/projects/{project_id}/tasks - 获取项目任务列表

### 3.3 任务管理接口
- GET /hsai/tasks - 获取任务列表
- POST /hsai/tasks - 创建任务
- GET /hsai/tasks/{task_id} - 获取任务详情
- PUT /hsai/tasks/{task_id} - 更新任务
- DELETE /hsai/tasks/{task_id} - 删除任务

## 4. 前端准备

### 4.1 UI组件
- 公司管理界面
- 项目管理界面
- 任务管理界面
- 任务状态展示组件
- 任务进度可视化组件

### 4.2 状态管理
- 公司信息状态管理
- 项目信息状态管理
- 任务列表状态管理
- 任务详情状态管理

## 5. 配置准备

### 5.1 环境变量
- DATABASE_URL: 数据库连接字符串
- REDIS_URL: Redis连接字符串（用于工作流信号）
- JWT_SECRET: JWT密钥

### 5.2 系统配置
- 主线任务模板配置
- 工作流关联配置
- 默认项目配置

## 6. 测试准备

### 6.1 单元测试
- 用户与公司关联逻辑测试
- 项目创建与主线任务生成测试
- 任务状态更新测试
- 数据库查询性能测试

### 6.2 集成测试
- 完整的用户注册到任务创建流程测试
- 工作流集成测试
- 多用户并发操作测试

## 7. 部署准备

### 7.1 数据库迁移
- 确保所有表结构更新脚本已执行
- 验证数据完整性
- 备份现有数据

### 7.2 服务配置
- 确保所有依赖服务正常运行
- 配置负载均衡（如需要）
- 设置监控和日志收集

### 7.3 安全配置
- 验证API访问权限控制
- 确保数据传输加密
- 配置防火墙规则

## 8. 文档准备

### 8.1 技术文档
- API接口文档
- 数据库设计文档
- 系统架构文档

### 8.2 用户文档
- 用户操作手册
- 管理员指南
- 常见问题解答

## 9. 培训准备

### 9.1 开发团队培训
- 系统架构培训
- 代码规范培训
- 开发流程培训

### 9.2 用户培训
- 系统使用培训
- 管理员操作培训
- 故障处理培训

## 10. 维护准备

### 10.1 监控体系
- 系统性能监控
- 错误日志监控
- 用户行为监控

### 10.2 备份策略
- 数据库备份策略
- 配置文件备份策略
- 灾难恢复计划

---
*文档版本: 1.0*
*最后更新: 2025-10-07*