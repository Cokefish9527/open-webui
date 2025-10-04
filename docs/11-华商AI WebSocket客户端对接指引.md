# 华商AI WebSocket客户端对接指引

## 概述
本文档为客户端开发人员提供华商AI WebSocket接口的对接指引，包括连接建立、消息发送、响应处理等关键环节。

## WebSocket连接

### 连接地址
```
# 使用OpenWebUI原生Socket.IO（官方推荐）
ws://localhost:8080/socket.io/?token={jwt_token}&user_id={user_id}

# 注意：前端通过OpenWebUI原生的Socket.IO与服务端通讯
# 这是OpenWebUI的标准通信协议，确保与现有系统的兼容性
```

### 认证方式
- 使用JWT令牌进行认证
- 令牌需包含用户ID信息
- 令牌有效期为1小时

### 连接示例

#### Socket.IO连接（推荐使用）
```javascript
// 需要引入socket.io-client库
const io = require('socket.io-client');

const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
const socket = io('ws://localhost:8080', {
    path: '/socket.io',
    auth: {
        token: token
    },
    query: {
        user_id: "user_123"
    }
});

socket.on('connect', function() {
    console.log("Socket.IO连接已建立");
});

// OpenWebUI原生事件监听
socket.on('message', function(data) {
    console.log("收到消息:", data);
});

socket.on('workflow_status', function(data) {
    console.log("工作流状态更新:", data);
});

socket.on('disconnect', function() {
    console.log("Socket.IO连接已断开");
});
```

## 消息格式

### 发送消息格式（原生WebSocket）
```javascript
{
  "type": "chat",              // 消息类型，固定为"chat"
  "content": "你好",           // 用户输入的对话文字
  "user_id": "user_123",       // 用户ID
  "session_id": "session_456", // 会话ID（可选）
  "entry_type": "chat"         // 入口类型（可选）
}
```

### Socket.IO事件发送
```javascript
// 发送聊天消息
socket.emit('message', {
    type: "chat",
    content: "你好",
    user_id: "user_123",
    session_id: "session_456",
    entry_type: "chat"
});

// 注意：使用OpenWebUI原生的'message'事件名称
// 服务端会根据entry_type选择对应的n8n工作流
```

### 入口类型说明
- `chat`: 普通聊天入口 -> 主对话工作流（https://webhook-n8n.hsai.cc/webhook/n8n_chat）
- `company`: 公司信息入口 -> 信息收集工作流（https://webhook-n8n.hsai.cc/webhook/business_information_get）
- `business`: 商业分析入口 -> 信息收集工作流（https://webhook-n8n.hsai.cc/webhook/business_information_get）
- `viral_learning`: 爆款学习入口 -> 爆款学习工作流（https://webhook-n8n.hsai.cc/webhook/keywords2video）

## 响应格式

### 标准响应结构
```javascript
{
  "success": true,             // 请求是否成功
  "messageType": "main",       // 消息类型标识
  "displayText": "响应内容",   // 用户可见的对话内容
  "data": {},                  // 结构化数据
  "status": "success",         // 当前流程状态
  "timestamp": "2023-01-01T00:00:00.000Z" // 时间戳
}
```

### 消息类型定义
- `main`: 主对话工作流响应
- `company_info`: 公司信息收集工作流响应
- `viral_learning`: 爆款学习工作流响应

### 服务端推送通知
```javascript
// 连接成功通知（通过OpenWebUI原生事件）
socket.on('connect', function() {
    // 连接已建立，可以开始通信
});

// 消息响应（n8n工作流处理结果）
socket.on('message', function(data) {
    console.log('收到n8n工作流响应:', data);
    // data的格式由服务端重新组织后返回，遵循约定的数据结构
});

// 工作流状态更新（长任务处理进度）
socket.on('workflow_status', function(data) {
    console.log('工作流状态更新:', data);
    // 通过redis信号触发的实时状态通知
});

// 错误通知
socket.on('error', function(error) {
    console.error('发生错误:', error);
});
```

## 错误处理

### 错误响应格式
```javascript
{
  "type": "error",
  "content": "错误信息",
  "timestamp": 1640995200
}
```

### 常见错误码
- 4001: 缺少认证令牌
- 4003: 认证失败
- 404: WebSocket端点不存在

## 最佳实践

### 1. Socket.IO连接管理
```javascript
class HSAISocketIOClient {
    constructor(userId, token) {
        this.userId = userId;
        this.token = token;
        this.socket = null;
        this.isConnected = false;
    }
    
    connect() {
        // 使用OpenWebUI原生Socket.IO连接
        this.socket = io('ws://localhost:8080', {
            path: '/socket.io',
            auth: {
                token: this.token
            },
            query: {
                user_id: this.userId
            }
        });
        
        this.socket.on('connect', () => {
            this.isConnected = true;
            console.log("Socket.IO连接已建立");
        });
        
        this.socket.on('disconnect', () => {
            this.isConnected = false;
            console.log("Socket.IO连接已关闭");
        });
        
        this.socket.on('error', (error) => {
            console.error("Socket.IO错误:", error);
        });
    }
    
    sendMessage(message) {
        if (this.isConnected) {
            // 使用OpenWebUI原生的message事件
            this.socket.emit('message', message);
        } else {
            console.error("Socket.IO未连接");
        }
    }
    
    onMessage(callback) {
        // 监听OpenWebUI原生消息事件
        this.socket.on('message', callback);
    }
    
    onWorkflowStatus(callback) {
        // 监听工作流状态更新
        this.socket.on('workflow_status', callback);
    }
}
```

### 2. 消息处理
```javascript
const client = new HSAISocketIOClient("user_123", "jwt_token");
client.connect();

// 监听主要响应消息
client.onMessage((response) => {
    // 服务端已经对n8n返回的字符串进行了重新组织
    // 按照约定的数据结构填充后返回给前端
    console.log('收到响应:', response);
    displayMessage(response.content);
    
    // 如果有特殊数据结构，由服务端处理后传递
    if (response.structured_data) {
        handleStructuredData(response.structured_data);
    }
});

// 监听工作流状态（通过redis信号触发）
client.onWorkflowStatus((status) => {
    console.log('工作流状态更新:', status);
    updateProgressIndicator(status.progress);
});

// 发送消息（将自动转发给相应的n8n工作流）
client.sendMessage({
    type: "chat",
    content: "你好",
    user_id: "user_123",
    entry_type: "chat"  // 服务端根据此字段选择相应的n8n工作流
});
```

## 服务端WebSocket接口说明

### 1. 连接接口
- **路径**: `/api/v1/ws/hsai/{user_id}`
- **方法**: WebSocket GET
- **参数**: 
  - `user_id` (路径参数): 用户ID
  - `token` (查询参数): JWT认证令牌

### 2. 消息发送接口
- **格式**: JSON文本帧
- **必填字段**: `type`, `content`, `user_id`
- **可选字段**: `session_id`, `entry_type`, `metadata`

### 3. 服务端推送事件
- `message`: n8n工作流处理结果响应
- `workflow_status`: 工作流处理进度通知（通过redis信号实时触发）
- `error`: 错误通知

## 注意事项
1. **使用Socket.IO**: 前端必须使用OpenWebUI原生的Socket.IO进行通信，保证与现有系统的兼容性
2. **消息结构**: 服务端会对n8n返回的字符串进行重新组织，按照约定的数据结构填充后返回前端
3. **工作流路由**: 服务端根据entry_type字段自动选择相应的n8n工作流URL
4. **长任务处理**: 对于需要长时间处理的任务，服务端通过redis信号进行实时通知
5. **JWT令牌**: 确保JWT令牌有效且未过期
6. **错误处理**: 正确处理连接异常和重连机制
7. **会话管理**: 合理管理会话ID以维持对话上下文

## 注意事项
1. 确保JWT令牌有效且未过期
2. 正确处理连接异常和重连机制
3. 遵循响应格式规范进行数据解析
4. 合理管理会话ID以维持对话上下文
5. 推荐使用方式一（原生WebSocket）以获得更好的性能