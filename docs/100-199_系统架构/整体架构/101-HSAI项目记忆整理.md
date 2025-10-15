# HSAI项目记忆整理

## 项目概述

HSAI系统是基于OpenWebUI构建的增强型AI工作流管理系统，集成了n8n工作流引擎，提供统一的WebSocket通信机制和模块化功能设计。

## 核心组件

1. **OpenWebUI后端服务** - 提供基础AI服务和用户管理
2. **HSAI扩展模块** - 增强功能模块（素材管理、任务管理、工作流集成等）
3. **n8n工作流引擎** - 自动化任务执行引擎
4. **WebSocket通信层** - 统一实时通信机制

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    前端客户端 (Web/Mobile)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ WebSocket连接 (JWT认证)
┌─────────────────────▼───────────────────────────────────────┐
│                   OpenWebUI Socket.IO                       │
│                    (/ws/socket.io)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              HSAI事件处理器 (hsai_events.py)                │
│              - 消息路由                                     │
│              - 工作流编排                                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│         工作流编排中心 (workflow_orchestration_center.py)   │
│         - 智能路由                                          │
│         - 状态管理                                          │
│         - n8n通信                                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  n8n工作流引擎                              │
│              (Webhook触发机制)                              │
└─────────────────────────────────────────────────────────────┘
```

## 工作流类型

1. **主工作流** (`main`) - 处理通用对话和任务分发
2. **公司信息收集工作流** (`company_info`) - 收集公司信息并生成作战地图
3. **视频抓取工作流** (`video_crawl`) - 触发视频内容抓取任务
4. **爆款学习工作流** (`viral_learning`) - 分析爆款内容并学习模式

## 入口类型映射

| 入口类型 | 对应工作流 | 说明 |
|---------|-----------|------|
| `chat` | `main` | 普通聊天入口 |
| `company` | `company_info` | 公司信息入口 |
| `video_crawl` | `video_crawl` | 视频抓取入口 |
| `viral_learning` | `viral_learning` | 爆款学习入口 |

## 核心模块接口

### 1. 素材管理模块

#### 文件夹管理
- `GET /hsai/materials/folders` - 获取素材文件夹树
- `POST /hsai/materials/folders` - 创建素材文件夹

#### 素材上传
- `POST /hsai/materials/upload` - 上传素材到OSS

#### 素材管理
- `GET /hsai/materials/` - 获取素材列表
- `GET /hsai/materials/search` - 搜索素材
- `GET /hsai/materials/stats` - 素材统计

### 2. 任务管理模块

#### 任务查询
- `GET /hsai/tasks/` - 获取任务列表（分页）
- `GET /hsai/tasks/{task_id}` - 获取任务详情

#### 任务操作
- `POST /hsai/tasks/` - 创建任务
- `PUT /hsai/tasks/{task_id}` - 更新任务
- `POST /hsai/tasks/{task_id}/assign` - 指派任务
- `POST /hsai/tasks/{task_id}/start` - 启动任务
- `POST /hsai/tasks/{task_id}/cancel` - 取消任务

#### 任务统计
- `GET /hsai/tasks/statistics` - 获取任务统计

### 3. 工作流集成模块

#### 工作流触发
- `POST /hsai/workflows/trigger` - 触发工作流

#### 状态查询
- `GET /hsai/workflows/status/{execution_id}` - 查询执行状态

#### 模板管理
- `GET /hsai/workflows/templates` - 获取工作流模板

## WebSocket通信规范

### 连接建立
```javascript
const socket = io('http://localhost:8080', {
    path: '/ws/socket.io',
    auth: { token: 'your-jwt-token' },
    transports: ['websocket', 'polling']
});
```

### 核心事件类型

#### 发送消息
```javascript
// 发送聊天消息
socket.emit('message', {
    type: 'chat',
    content: '你好，这是一个测试消息',
    user_id: 'user123',
    session_id: 'session_456',
    entry_type: 'chat', // 可选: chat, company_info, video_crawl, viral_learning
    metadata: {}
});

// 发送欢迎消息
socket.emit('message', {
    type: 'welcome',
    user_id: 'user123'
});

// 发送工作流触发消息
socket.emit('message', {
    type: 'workflow_trigger',
    content: '触发工作流',
    user_id: 'user123',
    entry_type: 'video_crawl'
});
```

#### 接收消息
```javascript
// 成功响应
socket.on('hsai_response', (data) => {
    console.log('收到HSAI响应:', data);
    // data.displayText - 显示文本
    // data.messageType - 消息类型 (user/assistant)
    // data.status - 状态 (FINISHED/PROCESSING)
});

// 错误响应
socket.on('hsai_error', (data) => {
    console.error('HSAI错误:', data);
});

// 工作流状态事件
socket.on('hsai_workflow_started', (data) => {
    console.log('工作流开始:', data);
});

socket.on('hsai_workflow_progress', (data) => {
    console.log('工作流进度:', data.progress);
});

socket.on('hsai_workflow_completed', (data) => {
    console.log('工作流完成:', data);
});
```

## n8n消息结构规范

### 服务端发送给n8n的请求结构
```json
{
  "session_id": "会话ID",
  "user_id": "用户ID",
  "message": "用户消息内容",
  "business_name": "业务名称（HSAI）",
  "timestamp": 1234567890123,
  "request_id": "请求ID"
}
```

### n8n通过Redis发送给服务端的消息结构
```json
{
  "env": "gray",
  "session_id": "会话ID",
  "reply_id": "回复ID",
  "reply_seq": 1,
  "reply_message_id": "响应的message_id",
  "operate_id": "操作ID",
  "status": "FINISHED",
  "content_type": 1,
  "content": {
    "text": "内容文本",
    "data": {
      "actions": ["view", "download", "export", "report", "images"],
      "title": "任务名",
      "markdown": "```

``",
      "images": ["", ""],
      "question": "问题文本",
      "selections": [
        "选项1文本",
        "选项2文本",
        "选项3文本"
      ],
      "multi_selections": [
        {
          "question": "是否使用监控数据",
          "options": ["使用", "不使用"]
        },
        {
          "question": "是否使用画像数据",
          "options": ["使用", "不使用"]
        }
      ],
      "period": "{{开始时间}},{{结束时间}}",
      "filters": [
        {
          "name": "筛选名",
          "filter_type": "筛选类型",
          "value": "筛选值"
        }
      ]
    }
  },
  "create_ts": 1272341234
}
```

## Redis队列消息表设计

### redis_queue_messages 表结构

| 字段名 | 类型 | 允许空 | 描述 |
|--------|------|--------|------|
| id | TEXT | 否 | 消息唯一标识符（主键） |
| queue_name | TEXT | 否 | Redis队列名称 |
| raw_data | TEXT | 否 | 获取到的原始数据 |
| fetched_at | BIGINT | 否 | 获取时间（时间戳） |
| execution_result | TEXT | 是 | 执行结果 |
| error_message | TEXT | 是 | 异常信息 |
| last_executed_at | BIGINT | 是 | 最后一次执行时间（时间戳） |
| status | TEXT | 否 | 消息处理状态（默认：pending） |
| retry_count | BIGINT | 是 | 重试次数（默认：0） |
| created_at | BIGINT | 否 | 创建时间（时间戳） |
| updated_at | BIGINT | 否 | 更新时间（时间戳） |

### 状态枚举
- `pending`: 待处理
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 处理失败

## 环境变量配置

```bash
# n8n工作流URL配置
N8N_MAIN_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/n8n_chat
N8N_COMPANY_INFO_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/business_information_get
N8N_VIDEO_CRAWL_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/video_crawl
N8N_VIRAL_LEARNING_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/viral_learning

# 爆款学习调度配置
VIRAL_LEARNING_ENABLED=true
VIRAL_LEARNING_INTERVAL_MINUTES=30
VIRAL_LEARNING_MAX_DAILY_CALLS=48

# Redis配置
REDIS_MODE=internal
REDIS_URL=redis://localhost:6379/0
```

## 部署与运维

### 启动服务
```bash
# 启动后端服务
cd backend
python main.py

# 或使用Docker
docker-compose up -d
```

## 文档管理规范

### 文档编号规范
- 格式：`NN-文档主题.md`
- NN：两位数字编号，从01开始递增
- 文档主题：简洁明确的中文主题名称

### 编号分配
| 编号范围 | 文档类型 | 说明 |
|---------|---------|------|
| 01-19 | 核心架构设计 | 系统架构、接口设计、核心规范 |
| 20-39 | 功能模块文档 | 各功能模块详细说明 |
| 40-59 | 工作流与集成 | 工作流设计、集成方案 |
| 60-79 | 前后端开发 | 前端界面、后端服务文档 |
| 80-89 | 测试与验证 | 测试计划、测试报告 |
| 90-99 | 项目管理 | 项目规范、管理文档 |

## 工具脚本管理

### 工具脚本目录
项目在 `tool/` 目录下存放具有重复使用价值的脚本工具。

### 脚本列表
1. **rename_sql_files.py** - 重命名 SQL 文件，将日期部分移到文件名开头

### 添加新脚本的规范
1. 所有脚本应具有明确的功能描述和使用说明
2. 脚本应具有良好的错误处理机制
3. 脚本应包含必要的注释说明
4. 在 `tool/README.md` 中添加脚本的说明信息

## 数据库表结构

### HSAI任务表 (hsai_tasks)
- id: 任务唯一标识符
- title: 任务标题
- description: 任务描述
- task_type: 任务类型
- status: 任务状态
- user_id: 用户ID
- assignee_id: 指派人ID
- project_id: 项目ID
- progress: 进度百分比(0-100)
- priority: 优先级
- created_at: 创建时间戳
- updated_at: 更新时间戳

### HSAI素材表 (hsai_materials)
- id: 素材唯一标识符
- name: 素材名称
- description: 素材描述
- material_type: 素材类型
- folder_id: 所属文件夹
- user_id: 用户ID
- file_path: 文件路径
- file_size: 文件大小
- mime_type: MIME类型
- tags: 标签数组
- usage_count: 使用次数
- status: 状态
- created_at: 创建时间戳
- updated_at: 更新时间戳

## 项目特色功能

### 用户公司名称字段 (business_name)
系统支持为每个用户设置公司名称，该信息将用于WebSocket通信和视频学习等场景中。

### HSAI计费系统
系统集成了基于资源消耗的计费系统，解决大模型集成在n8n中无法有效获取token消耗、多种第三方服务计费方式不同以及Redis连接不稳定导致计费风险等问题。

主要特性：
- 基于资源消耗的计费模式（存储空间、API调用等）
- 数据库持久化存储确保计费数据可靠性
- 动态计费配置管理
- API使用记录跟踪
- 公司积分余额管理

## 新增功能

### 战略关键词路由功能
- 当用户通过Socket发送的消息中包含"战略"字眼时，系统会自动路由到信息收集工作流（COMPANY_INFO工作流）
- 该功能优先于entry_type设置，确保涉及战略的讨论都能正确路由到相应的工作流

## 安全与认证

### 认证机制
- 使用OpenWebUI原生JWT认证
- 所有WebSocket连接都需要有效的JWT令牌

### 权限控制
- 基于用户ID的会话隔离
- 防止跨用户数据泄露