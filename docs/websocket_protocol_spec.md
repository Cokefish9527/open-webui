# HSAI WebSocket交互协议说明书

**版本**: v1.0.0  
**更新日期**: 2025-09-03  
**适用范围**: 前端 ↔ 后端 ↔ n8n工作流  

## 1. WebSocket连接

### 1.1 连接建立

**连接URL**: `ws://<host>:<port>/hsai/ws/{user_id}?token=<auth_token>[&session_id=<session_id>]`

**参数说明**:
- `user_id`: 用户唯一标识符
- `token`: 认证令牌
- `session_id`: (可选) 会话ID

**连接流程**:
1. 前端通过WebSocket连接到指定URL
2. 后端验证token和user_id
3. 验证通过后建立连接并发送连接确认消息

### 1.2 连接确认消息

```json
{
  "type": "status",
  "content": "连接成功",
  "timestamp": 1640995200.0,
  "available_workflows": [
    {
      "type": "main",
      "name": "主工作流",
      "description": "主工作流 - 处理通用对话和任务分发"
    },
    {
      "type": "company_info",
      "name": "公司信息收集及作战地图梳理",
      "description": "公司信息收集及作战地图梳理 - 收集公司信息并生成作战地图"
    }
  ]
}
```

## 2. 消息格式

### 2.1 客户端发送消息格式

```json
{
  "type": "消息类型",
  "content": "消息内容",
  "user_id": "用户ID",
  "session_id": "会话ID(可选)",
  "workflow_type": "工作流类型(可选)",
  "entry_type": "对话入口类型(可选)",
  "metadata": {
    "额外元数据": "值"
  }
}
```

**消息类型**:
- `chat`: 聊天消息
- `workflow_trigger`: 工作流触发消息

### 2.2 服务端响应消息格式

```json
{
  "type": "消息类型",
  "content": "消息内容",
  "timestamp": 1640995200.0,
  "session_id": "会话ID",
  "user_id": "用户ID",
  "execution_id": "执行ID",
  "data": {
    "响应数据": "值"
  }
}
```

**消息类型**:
- `status`: 状态消息
- `workflow_response`: 工作流响应消息
- `error`: 错误消息

## 3. 工作流交互

### 3.1 主要工作流

1. **主工作流** (`main`)
   - URL: `https://webhook-n8n.hsai.cc/webhook/main-workflow`
   - 用途: 处理通用对话和任务分发

2. **公司信息收集工作流** (`company_info`)
   - URL: `https://webhook-n8n.hsai.cc/webhook/company-info`
   - 用途: 收集公司信息并生成作战地图

### 3.2 工作流触发方式

1. **聊天消息触发**:
   - 发送 `type` 为 `chat` 的消息
   - 系统根据入口类型或关键词自动选择工作流

2. **直接工作流触发**:
   - 发送 `type` 为 `workflow_trigger` 的消息
   - 明确指定 `workflow_type`

## 4. 错误处理

### 4.1 错误消息格式

```json
{
  "type": "error",
  "content": "错误描述",
  "timestamp": 1640995200.0
}
```

### 4.2 常见错误类型

- 认证失败
- 消息格式错误
- 工作流执行失败
- 网络超时

## 5. 会话管理

### 5.1 会话创建
- 系统自动为每个用户创建会话
- 会话ID在首次交互时生成并返回

### 5.2 会话维持
- WebSocket连接保持期间会话有效
- 连接断开后会话信息保留一段时间