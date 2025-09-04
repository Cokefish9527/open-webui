# HSAI接口模块功能描述文档

## 📋 模块概览

本文档详细描述了HSAI项目中新增和修正的接口模块功能，包括接口设计、参数说明、返回格式和业务逻辑。

---

## 🗂️ 1. 素材管理模块 (hsai_materials.py)

### 模块定位
**核心功能**: 基于阿里云OSS的文件存储和管理系统  
**设计目标**: 为用户提供高效、安全的素材存储和管理服务  
**技术特点**: OSS直传、CDN加速、AI智能分析

### 1.1 文件夹管理接口

#### GET `/hsai/materials/folders` - 获取素材文件夹
**功能描述**: 获取用户的文件夹树形结构，支持层级展示
```json
// 返回格式
[
  {
    "id": "folder_123",
    "name": "我的图片",
    "parent_id": null,
    "children": [
      {
        "id": "folder_456", 
        "name": "产品图片",
        "parent_id": "folder_123",
        "children": [],
        "material_count": 15
      }
    ],
    "material_count": 25,
    "created_at": 1693478400,
    "updated_at": 1693478400
  }
]
```

#### POST `/hsai/materials/folders` - 创建素材文件夹
**功能描述**: 创建新的文件夹，支持层级结构
```json
// 请求参数
{
  "name": "新文件夹",
  "parent_id": "folder_123",  // 可选，父文件夹ID
  "description": "文件夹描述"
}
```

### 1.2 素材上传接口 (核心功能)

#### POST `/hsai/materials/upload` - 上传素材到OSS
**功能描述**: 直接上传文件到阿里云OSS，支持多种文件格式
**核心特性**:
- ✅ **OSS直传** - 文件直接上传到阿里云OSS
- ✅ **智能分类** - 根据MIME类型自动分类
- ✅ **AI分析** - 可选的智能内容分析
- ✅ **标签管理** - OSS级别的文件标签
- ✅ **安全校验** - 文件类型、大小、完整性检查

```json
// 请求参数 (multipart/form-data)
{
  "file": "文件对象",
  "name": "素材名称",           // 可选，默认使用文件名
  "description": "素材描述",    // 可选
  "folder_id": "folder_123",   // 可选，目标文件夹
  "tags": "[\"标签1\", \"标签2\"]", // 可选，JSON字符串
  "auto_analyze": true         // 可选，是否AI分析，默认true
}

// 返回格式
{
  "id": "material_789",
  "name": "产品图片.jpg",
  "material_type": "image",
  "file_path": "s3://bucket/hsai/materials/user123/abc123.jpg",
  "file_size": 1024000,
  "mime_type": "image/jpeg",
  "upload_url": "https://bucket.oss-cn-hangzhou.aliyuncs.com/hsai/materials/user123/abc123.jpg",
  "download_url": "https://bucket.oss-cn-hangzhou.aliyuncs.com/hsai/materials/user123/abc123.jpg",
  "thumbnail_url": "/hsai/materials/material_789/thumbnail",
  "created_at": 1693478400,
  "material_metadata": {
    "original_filename": "产品图片.jpg",
    "oss_url": "https://...",
    "storage_provider": "oss"
  }
}
```

### 1.3 素材下载接口

#### GET `/hsai/materials/{material_id}/download` - 获取下载链接
**功能描述**: 返回OSS直链，支持CDN加速访问
```json
// 返回格式
{
  "download_url": "https://bucket.oss-cn-hangzhou.aliyuncs.com/path/file.jpg",
  "filename": "产品图片.jpg",
  "file_size": 1024000,
  "mime_type": "image/jpeg"
}
```

### 1.4 素材管理接口

#### GET `/hsai/materials/` - 获取素材列表
**功能描述**: 分页获取用户素材，支持文件夹和类型过滤
```json
// 查询参数
{
  "folder_id": "folder_123",    // 可选，文件夹过滤
  "material_type": "image",     // 可选，类型过滤
  "limit": 20,                  // 分页大小
  "offset": 0                   // 偏移量
}
```

#### GET `/hsai/materials/search` - 搜索素材
**功能描述**: 全文搜索素材，支持名称、描述、标签匹配
```json
// 查询参数
{
  "query": "产品图片",          // 搜索关键词
  "material_type": "image",     // 可选，类型过滤
  "limit": 20
}
```

#### GET `/hsai/materials/stats` - 素材统计
**功能描述**: 获取用户素材统计信息
```json
// 返回格式
{
  "total_materials": 150,
  "folders_count": 12,
  "type_distribution": {
    "image": 80,
    "video": 20,
    "document": 30,
    "audio": 20
  },
  "total_size_mb": 2048,
  "recent_uploads": 15
}
```

---

## 🏠 2. 个人工作台模块 (hsai_dashboard.py)

### 模块定位
**核心功能**: 用户个人数据中心和快速操作入口  
**设计目标**: 提供直观的数据概览和高效的操作体验  
**技术特点**: 实时数据、可视化图表、快速操作

### 2.1 数据概览接口

#### GET `/hsai/dashboard/overview` - 工作台概览
**功能描述**: 获取用户工作台核心数据概览
```json
// 返回格式
{
  "user_info": {
    "name": "张三",
    "avatar": "https://...",
    "level": "高级用户"
  },
  "quick_stats": {
    "total_tasks": 45,
    "pending_tasks": 8,
    "completed_tasks": 37,
    "total_materials": 120,
    "total_conversations": 25
  },
  "recent_activity": [
    {
      "type": "task_completed",
      "title": "完成了任务：数据分析报告",
      "time": 1693478400
    }
  ],
  "system_notifications": [
    {
      "type": "info",
      "message": "系统将于今晚进行维护",
      "time": 1693478400
    }
  ]
}
```

### 2.2 KPI监控接口

#### GET `/hsai/dashboard/kpi` - KPI指标
**功能描述**: 获取用户关键绩效指标
```json
// 查询参数
{
  "period": "week",  // week/month/quarter
  "metrics": ["efficiency", "completion_rate", "activity"]
}

// 返回格式
{
  "period": "week",
  "metrics": {
    "task_completion_rate": {
      "value": 85.5,
      "trend": "up",
      "change": 5.2
    },
    "average_response_time": {
      "value": 2.3,
      "unit": "hours",
      "trend": "down",
      "change": -0.5
    },
    "productivity_score": {
      "value": 92,
      "trend": "up",
      "change": 8
    }
  }
}
```

### 2.3 活动记录接口

#### GET `/hsai/dashboard/activities` - 最近活动
**功能描述**: 获取用户最近的操作活动记录
```json
// 查询参数
{
  "limit": 20,
  "activity_type": "all",  // all/task/material/chat
  "date_range": "7d"       // 1d/7d/30d
}

// 返回格式
[
  {
    "id": "activity_123",
    "type": "task_created",
    "title": "创建了新任务",
    "description": "AI图像识别优化",
    "timestamp": 1693478400,
    "metadata": {
      "task_id": "task_456",
      "priority": "high"
    }
  }
]
```

### 2.4 趋势分析接口

#### GET `/hsai/dashboard/trends` - 趋势分析
**功能描述**: 获取用户行为和绩效趋势数据
```json
// 查询参数
{
  "metric": "task_completion",  // task_completion/material_usage/chat_activity
  "period": "30d",
  "granularity": "daily"        // daily/weekly/monthly
}

// 返回格式
{
  "metric": "task_completion",
  "period": "30d",
  "data_points": [
    {
      "date": "2023-08-01",
      "value": 12,
      "label": "已完成任务"
    },
    {
      "date": "2023-08-02", 
      "value": 8,
      "label": "已完成任务"
    }
  ],
  "summary": {
    "total": 245,
    "average": 8.2,
    "trend": "increasing"
  }
}
```

### 2.5 快速操作接口

#### POST `/hsai/dashboard/quick-action` - 快速操作
**功能描述**: 执行常用的快速操作
```json
// 请求参数
{
  "action": "create_task",  // create_task/upload_material/start_chat
  "params": {
    "title": "新任务",
    "priority": "medium"
  }
}

// 返回格式
{
  "success": true,
  "action": "create_task",
  "result": {
    "id": "task_789",
    "redirect_url": "/tasks/task_789"
  }
}
```

---

## 💬 3. 对话管理模块 (hsai_chat.py)

### 模块定位
**核心功能**: AI对话会话管理和消息处理系统  
**设计目标**: 提供流畅的对话体验和完整的会话管理  
**技术特点**: 实时通信、会话持久化、智能搜索

### 3.1 会话管理接口

#### POST `/hsai/chat/sessions` - 创建对话会话
**功能描述**: 创建新的AI对话会话
```json
// 请求参数
{
  "title": "产品策划讨论",
  "ai_model": "gpt-4",
  "system_prompt": "你是一个产品策划专家",
  "context": {
    "task_id": "task_123",  // 可选，关联任务
    "project_id": "proj_456"
  }
}

// 返回格式
{
  "id": "session_789",
  "title": "产品策划讨论",
  "ai_model": "gpt-4",
  "status": "active",
  "created_at": 1693478400,
  "message_count": 0,
  "context": {
    "task_id": "task_123"
  }
}
```

#### GET `/hsai/chat/sessions` - 获取会话列表
**功能描述**: 分页获取用户的对话会话
```json
// 查询参数
{
  "status": "active",  // active/archived/all
  "limit": 20,
  "offset": 0,
  "search": "产品"     // 可选，搜索关键词
}
```

### 3.2 消息处理接口

#### GET `/hsai/chat/sessions/{session_id}/messages` - 获取消息历史
**功能描述**: 获取指定会话的消息历史
```json
// 返回格式
[
  {
    "id": "msg_123",
    "session_id": "session_789",
    "role": "user",
    "content": "请帮我分析一下这个产品的市场前景",
    "timestamp": 1693478400,
    "metadata": {
      "attachments": ["file_123"],
      "tokens": 25
    }
  },
  {
    "id": "msg_124",
    "session_id": "session_789", 
    "role": "assistant",
    "content": "根据您提供的信息，我来分析一下...",
    "timestamp": 1693478410,
    "metadata": {
      "model": "gpt-4",
      "tokens": 150,
      "processing_time": 2.3
    }
  }
]
```

#### POST `/hsai/chat/sessions/{session_id}/messages` - 发送消息
**功能描述**: 向指定会话发送消息并获取AI回复
```json
// 请求参数
{
  "content": "请帮我分析一下这个产品的市场前景",
  "attachments": ["file_123"],  // 可选，附件ID列表
  "stream": false,              // 可选，是否流式返回
  "context": {
    "reference_message": "msg_120"  // 可选，引用消息
  }
}

// 返回格式
{
  "user_message": {
    "id": "msg_125",
    "content": "请帮我分析一下这个产品的市场前景",
    "timestamp": 1693478500
  },
  "ai_response": {
    "id": "msg_126", 
    "content": "根据您提供的信息...",
    "timestamp": 1693478510,
    "metadata": {
      "model": "gpt-4",
      "tokens": 180,
      "processing_time": 3.2
    }
  }
}
```

### 3.3 搜索和统计接口

#### GET `/hsai/chat/search` - 搜索对话内容
**功能描述**: 全文搜索对话内容
```json
// 查询参数
{
  "query": "产品分析",
  "session_id": "session_789",  // 可选，限定会话
  "date_range": "30d",
  "limit": 20
}

// 返回格式
[
  {
    "message_id": "msg_123",
    "session_id": "session_789",
    "session_title": "产品策划讨论",
    "content": "请帮我分析一下这个产品的市场前景",
    "role": "user",
    "timestamp": 1693478400,
    "highlight": "...分析一下这个<em>产品</em>的市场..."
  }
]
```

#### GET `/hsai/chat/stats` - 对话统计
**功能描述**: 获取用户对话统计信息
```json
// 返回格式
{
  "total_sessions": 25,
  "active_sessions": 8,
  "total_messages": 1250,
  "total_tokens": 125000,
  "models_usage": {
    "gpt-4": 800,
    "gpt-3.5": 450
  },
  "daily_activity": [
    {
      "date": "2023-08-01",
      "messages": 45,
      "sessions": 3
    }
  ]
}
```

---

## 🔄 4. 工作流集成模块 (hsai_workflows.py)

### 模块定位
**核心功能**: n8n工作流引擎集成和自动化任务执行  
**设计目标**: 提供强大的自动化能力和流程编排  
**技术特点**: 异步执行、状态跟踪、模板管理

### 4.1 工作流触发接口

#### POST `/hsai/workflows/trigger` - 触发工作流
**功能描述**: 触发指定的n8n工作流执行
```json
// 请求参数
{
  "workflow_id": "workflow_123",
  "input_data": {
    "task_id": "task_456",
    "parameters": {
      "source_url": "https://example.com",
      "output_format": "json"
    }
  },
  "priority": "normal",  // low/normal/high
  "callback_url": "https://api.example.com/webhook"  // 可选
}

// 返回格式
{
  "execution_id": "exec_789",
  "workflow_id": "workflow_123",
  "status": "running",
  "started_at": 1693478400,
  "estimated_duration": 300,
  "progress_url": "/hsai/workflows/status/exec_789"
}
```

### 4.2 状态查询接口

#### GET `/hsai/workflows/status/{execution_id}` - 查询执行状态
**功能描述**: 查询工作流执行状态和进度
```json
// 返回格式
{
  "execution_id": "exec_789",
  "workflow_id": "workflow_123",
  "status": "running",  // pending/running/completed/failed/cancelled
  "progress": 65,
  "started_at": 1693478400,
  "updated_at": 1693478500,
  "steps": [
    {
      "step_id": "step_1",
      "name": "数据获取",
      "status": "completed",
      "duration": 30
    },
    {
      "step_id": "step_2", 
      "name": "数据处理",
      "status": "running",
      "progress": 80
    }
  ],
  "output_data": null,  // 完成后包含结果
  "error_message": null
}
```

### 4.3 模板管理接口

#### GET `/hsai/workflows/templates` - 获取工作流模板
**功能描述**: 获取可用的工作流模板列表
```json
// 查询参数
{
  "category": "data_processing",  // 可选，分类过滤
  "tags": ["ai", "automation"],   // 可选，标签过滤
  "limit": 20
}

// 返回格式
[
  {
    "id": "template_123",
    "name": "AI内容分析流程",
    "description": "自动分析文档内容并生成摘要",
    "category": "ai_processing",
    "tags": ["ai", "nlp", "analysis"],
    "input_schema": {
      "type": "object",
      "properties": {
        "document_url": {"type": "string"},
        "analysis_type": {"type": "string", "enum": ["summary", "keywords", "sentiment"]}
      }
    },
    "estimated_duration": 180,
    "usage_count": 45
  }
]
```

---

## 🤖 5. AI服务集成模块 (hsai_ai.py)

### 模块定位
**核心功能**: AI服务调用和任务系统集成  
**设计目标**: 统一AI服务接口，自动任务管理  
**技术特点**: 异步处理、任务集成、状态通知

### 5.1 AI服务调用接口

#### POST `/hsai/ai/text/generate` - 文本生成
**功能描述**: 调用AI进行文本生成，自动创建任务记录
```json
// 请求参数
{
  "prompt": "请写一篇关于人工智能发展的文章",
  "model": "gpt-4",
  "max_tokens": 2000,
  "temperature": 0.7,
  "task_config": {
    "title": "AI文章生成",
    "priority": "medium",
    "auto_save": true
  }
}

// 返回格式 (AITaskResponse)
{
  "task_id": "task_789",
  "ai_response": {
    "content": "人工智能的发展历程...",
    "model": "gpt-4",
    "tokens_used": 1850,
    "processing_time": 5.2
  },
  "task_status": "completed",
  "created_at": 1693478400,
  "metadata": {
    "service_type": "text_generation",
    "auto_created": true
  }
}
```

#### POST `/hsai/ai/image/analyze` - 图像分析
**功能描述**: AI图像分析服务
```json
// 请求参数
{
  "image_url": "https://example.com/image.jpg",
  "analysis_type": ["objects", "text", "sentiment"],
  "task_config": {
    "title": "图像内容分析",
    "description": "分析产品图片内容"
  }
}
```

#### POST `/hsai/ai/audio/transcribe` - 音频转录
**功能描述**: 音频转文字服务
```json
// 请求参数
{
  "audio_url": "https://example.com/audio.mp3",
  "language": "zh-CN",
  "format": "srt",  // text/srt/vtt
  "task_config": {
    "title": "会议录音转录"
  }
}
```

### 5.2 批量处理接口

#### POST `/hsai/ai/batch/process` - 批量AI处理
**功能描述**: 批量提交AI处理任务
```json
// 请求参数
{
  "tasks": [
    {
      "type": "text_generate",
      "params": {"prompt": "..."},
      "task_config": {"title": "任务1"}
    },
    {
      "type": "image_analyze", 
      "params": {"image_url": "..."},
      "task_config": {"title": "任务2"}
    }
  ],
  "batch_config": {
    "priority": "low",
    "max_concurrent": 3
  }
}

// 返回格式
{
  "batch_id": "batch_123",
  "task_ids": ["task_789", "task_790"],
  "status": "processing",
  "progress_url": "/hsai/ai/batch/batch_123/status"
}
```

---

## 🔔 6. WebSocket事件处理 (hsai_events.py)

### 模块定位
**核心功能**: 实时通信和事件通知系统  
**设计目标**: 提供实时的状态更新和消息推送  
**技术特点**: 房间管理、事件分发、连接管理

### 6.1 WebSocket连接管理
```
# 连接建立
ws://localhost:8080/hsai/ws/{user_id}

# 房间加入
{
  "type": "join_room",
  "room": "task_123"
}

# 事件订阅
{
  "type": "subscribe",
  "events": ["chat_message", "system_notification"]
}
```

### 6.2 事件类型定义
``json
// 聊天消息
{
  "type": "chat_message",
  "data": {
    "session_id": "session_789",
    "message": {...}
  }
}

// 系统通知
{
  "type": "system_notification",
  "data": {
    "level": "info",
    "message": "系统维护通知",
    "timestamp": 1693478400
  }
}
```

---

## 📊 接口设计总结

### 设计原则
1. **RESTful规范** - 遵循REST API设计原则
2. **统一响应格式** - 标准化的成功/错误响应
3. **分页支持** - 列表接口支持分页查询
4. **权限控制** - 所有接口都有用户权限验证
5. **错误处理** - 完善的异常处理和错误信息

### 技术特点
1. **异步处理** - 大部分操作支持异步执行
2. **实时通信** - WebSocket支持实时状态更新
3. **OSS集成** - 文件存储完全基于阿里云OSS
4. **AI集成** - 深度集成各种AI服务
5. **任务驱动** - 以任务为中心的业务流程

### 扩展性考虑
1. **模块化设计** - 各模块独立，便于扩展
2. **配置化** - 支持灵活的配置管理
3. **插件化** - 预留插件扩展接口
4. **多租户** - 支持多用户隔离
5. **监控友好** - 完善的日志和监控支持

---

**请确认以上接口设计是否符合您的设计意图，如有需要调整的地方，请告知具体要求。**