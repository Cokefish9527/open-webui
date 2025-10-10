# HSAI系统架构与接口设计规范

## 📋 系统概述

HSAI系统是基于OpenWebUI构建的增强型AI工作流管理系统，集成了n8n工作流引擎，提供统一的WebSocket通信机制和模块化功能设计。

## 🏗️ 系统架构

### 核心组件
1. **OpenWebUI后端服务** - 提供基础AI服务和用户管理
2. **HSAI扩展模块** - 增强功能模块（素材管理、任务管理、工作流集成等）
3. **n8n工作流引擎** - 自动化任务执行引擎
4. **WebSocket通信层** - 统一实时通信机制

### 技术架构图
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

## 🔌 WebSocket通信规范

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

## 🔄 工作流集成规范

### 工作流类型
1. **主工作流** (`main`) - 处理通用对话和任务分发
2. **公司信息收集工作流** (`company_info`) - 收集公司信息并生成作战地图
3. **视频抓取工作流** (`video_crawl`) - 触发视频内容抓取任务
4. **爆款学习工作流** (`viral_learning`) - 分析爆款内容并学习模式

### 入口类型映射
| 入口类型 | 对应工作流 | 说明 |
|---------|-----------|------|
| `chat` | `main` | 普通聊天入口 |
| `company` | `company_info` | 公司信息入口 |
| `video_crawl` | `video_crawl` | 视频抓取入口 |
| `viral_learning` | `viral_learning` | 爆款学习入口 |

## 📁 目录结构

```
backend/open_webui/
├── routers/                    # API路由
│   ├── hsai_materials.py       # 素材管理接口
│   ├── hsai_tasks.py           # 任务管理接口
│   ├── hsai_chat.py            # 对话管理接口
│   └── hsai_workflows.py       # 工作流接口
├── models/                     # 数据模型
│   ├── hsai_materials.py       # 素材数据模型
│   ├── hsai_tasks.py           # 任务数据模型
│   └── hsai_chats.py           # 对话数据模型
├── socket/                     # WebSocket处理
│   ├── hsai_events.py          # HSAI事件处理器
│   └── main.py                 # Socket.IO主文件
├── services/                   # 业务服务
│   └── workflow_orchestration_center.py  # 工作流编排中心
└── utils/                      # 工具函数
    ├── n8n_client.py           # n8n客户端
    ├── n8n_workflow_manager.py # 工作流管理器
    └── n8n_response_processor.py # 响应处理器
```

## 🛠️ 核心模块接口

### 1. 素材管理模块 (hsai_materials.py)

#### 文件夹管理
- `GET /hsai/materials/folders` - 获取素材文件夹树
- `POST /hsai/materials/folders` - 创建素材文件夹

#### 素材上传
- `POST /hsai/materials/upload` - 上传素材到OSS

#### 素材管理
- `GET /hsai/materials/` - 获取素材列表
- `GET /hsai/materials/search` - 搜索素材
- `GET /hsai/materials/stats` - 素材统计

### 2. 任务管理模块 (hsai_tasks.py)

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

### 3. 工作流集成模块 (hsai_workflows.py)

#### 工作流触发
- `POST /hsai/workflows/trigger` - 触发工作流

#### 状态查询
- `GET /hsai/workflows/status/{execution_id}` - 查询执行状态

#### 模板管理
- `GET /hsai/workflows/templates` - 获取工作流模板

## 🔐 安全与认证

### 认证机制
- 使用OpenWebUI原生JWT认证
- 所有WebSocket连接都需要有效的JWT令牌

### 权限控制
- 基于用户ID的会话隔离
- 防止跨用户数据泄露

## 📊 监控与日志

### 执行监控
- 工作流编排中心提供详细的执行监控
- 支持实时状态查询和历史记录

### 错误日志
- 统一的错误日志记录
- 便于问题排查和性能优化

## 🚀 部署与运维

### 环境变量配置
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
```

### 启动服务
```bash
# 启动后端服务
cd backend
python main.py

# 或使用Docker
docker-compose up -d
```

## 🧪 测试工具

### WebSocket测试页面
- 文件: `websocket-test.html`
- 功能: 提供完整的WebSocket连接和消息测试界面

### Python测试脚本
- 文件: `test_updated_websocket.py`
- 功能: 自动化测试WebSocket连接和消息处理

## 📝 文档维护

### 版本控制
- 所有文档保存在`docs/`目录下
- 过时文档移至`docs/archive/`目录
- 新增文档按编号和主题命名

### 更新规范
- 文档编号格式: `NN-文档主题.md`
- 索引文件: `README.md` (文档目录索引)