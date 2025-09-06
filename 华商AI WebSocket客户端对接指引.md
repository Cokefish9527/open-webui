# 华商AI WebSocket客户端对接指引

## 概述
本文档为客户端开发人员提供华商AI WebSocket接口的对接指引，包括连接建立、消息发送、响应处理等关键环节。

## WebSocket连接

### 连接地址
```
# 方式一：使用OpenWebUI原生WebSocket（推荐）
ws://localhost:8080/api/v1/ws/hsai/{user_id}?token={jwt_token}

# 方式二：使用Socket.IO（兼容OpenWebUI原有系统）
ws://localhost:8080/ws/socket.io/?token={jwt_token}&user_id={user_id}
```

### 认证方式
- 使用JWT令牌进行认证
- 令牌需包含用户ID信息
- 令牌有效期为1小时

### 连接示例

#### 方式一：原生WebSocket连接
```javascript
const userId = "user_123";
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."; // JWT令牌
const websocket = new WebSocket(`ws://localhost:8080/api/v1/ws/hsai/${userId}?token=${token}`);

websocket.onopen = function(event) {
    console.log("WebSocket连接已建立");
};

websocket.onmessage = function(event) {
    const response = JSON.parse(event.data);
    console.log("收到服务器响应:", response);
};

websocket.onclose = function(event) {
    console.log("WebSocket连接已关闭");
};

websocket.onerror = function(error) {
    console.error("WebSocket错误:", error);
};
```

#### 方式二：Socket.IO连接（兼容原系统）
```javascript
// 需要引入socket.io-client库
const io = require('socket.io-client');

const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
const socket = io('ws://localhost:8080', {
    path: '/ws/socket.io',
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

socket.on('chat-events', function(data) {
    console.log("收到聊天事件:", data);
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
socket.emit('send_message', {
    type: "chat",
    content: "你好",
    user_id: "user_123",
    session_id: "session_456",
    entry_type: "chat"
});
```

### 入口类型说明
- `chat`: 普通聊天入口 -> 主工作流
- `company`: 公司信息入口 -> 信息收集工作流
- `business`: 商业分析入口 -> 信息收集工作流

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
// 连接成功通知
{
  "type": "status",
  "content": "连接成功",
  "timestamp": 1640995200,
  "available_workflows": [
    {"type": "MAIN", "name": "主工作流", "description": "处理通用对话和任务分发"},
    {"type": "COMPANY_INFO", "name": "公司信息收集", "description": "收集公司信息并生成作战地图"}
  ]
}

// 工作流处理状态通知
{
  "type": "workflow_status",
  "status": "processing",
  "message": "正在处理您的请求...",
  "progress": 50,
  "timestamp": 1640995200
}

// 工作流完成通知
{
  "type": "workflow_complete",
  "status": "completed",
  "data": {
    "content": "处理结果",
    "type": "text"
  },
  "timestamp": 1640995200
}
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

### 1. 连接管理
```javascript
class HSAIWebSocketClient {
    constructor(userId, token) {
        this.userId = userId;
        this.token = token;
        this.websocket = null;
        this.isConnected = false;
    }
    
    connect() {
        this.websocket = new WebSocket(
            `ws://localhost:8080/api/v1/ws/hsai/${this.userId}?token=${this.token}`
        );
        
        this.websocket.onopen = () => {
            this.isConnected = true;
            console.log("WebSocket连接已建立");
        };
        
        this.websocket.onclose = () => {
            this.isConnected = false;
            console.log("WebSocket连接已关闭");
        };
        
        this.websocket.onerror = (error) => {
            console.error("WebSocket错误:", error);
        };
    }
    
    sendMessage(message) {
        if (this.isConnected) {
            this.websocket.send(JSON.stringify(message));
        } else {
            console.error("WebSocket未连接");
        }
    }
    
    onMessage(callback) {
        this.websocket.onmessage = (event) => {
            const response = JSON.parse(event.data);
            callback(response);
        };
    }
}
```

### 2. 消息处理
```javascript
const client = new HSAIWebSocketClient("user_123", "jwt_token");
client.connect();

client.onMessage((response) => {
    switch(response.type) {
        case 'status':
            // 处理连接状态消息
            console.log("连接状态:", response.content);
            break;
        case 'workflow_status':
            // 处理工作流状态更新
            console.log("处理进度:", response.progress + "%");
            break;
        case 'workflow_complete':
            // 处理工作流完成
            displayMessage(response.data.content);
            break;
        case 'error':
            // 处理错误响应
            displayError(response.content);
            break;
        default:
            // 处理其他响应
            if (response.success) {
                displayMessage(response.displayText);
                handleData(response.data);
            }
    }
});

// 发送消息
client.sendMessage({
    type: "chat",
    content: "你好",
    user_id: "user_123",
    entry_type: "chat"
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
- `status`: 连接状态和可用工作流信息
- `workflow_status`: 工作流处理进度通知
- `workflow_complete`: 工作流处理完成通知
- `error`: 错误通知

## 注意事项
1. 确保JWT令牌有效且未过期
2. 正确处理连接异常和重连机制
3. 遵循响应格式规范进行数据解析
4. 合理管理会话ID以维持对话上下文
5. 推荐使用方式一（原生WebSocket）以获得更好的性能