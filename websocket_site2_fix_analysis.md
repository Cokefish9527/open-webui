# 站点2 WebSocket 消息接收问题分析与修复方案

## 问题描述
- 站点1 (http://192.168.20.62:5173) 可以正常连接WebSocket并接收消息
- 站点2 (http://192.168.20.62:5174) 可以连接WebSocket并完成认证，但无法接收服务器返回的消息

## 问题分析

### 1. 连接流程分析
通过查看测试脚本 [test_websocket_sites.py](file://c:/work/open-webui/test_websocket_sites.py) 和 [test_websocket_sites.js](file://c:/work/open-webui/test_websocket_sites.js)，我们发现两个站点都能成功：
1. 连接到WebSocket服务器: `ws://localhost:8080/ws/socket.io/?EIO=4&transport=websocket`
2. 收到初始消息: `0{"sid":"...","upgrades":[],"pingTimeout":20000,"pingInterval":25000,"maxPayload":1000000}`
3. 发送认证消息: `40{"token":"test_token"}`
4. 收到认证响应: `40{"sid":"..."}`

这表明两个站点的基础WebSocket连接和认证流程都是正常的。

### 2. 可能的问题原因

#### 2.1 会话注册问题
在 [main.py](file://c:/work/open-webui/backend/open_webui/socket/main.py) 中，系统使用以下结构管理会话：
- [SESSION_POOL](file://c:/work/open-webui/backend/open_webui/socket/main.py#L77-L77): 存储SID到用户数据的映射
- [USER_POOL](file://c:/work/open-webui/backend/open_webui/socket/main.py#L78-L78): 存储用户ID到SID列表的映射
- [SESSION_ID_TO_SID](file://c:/work/open-webui/backend/open_webui/socket/main.py#L80-L80): 存储session_id到SID的映射

可能存在站点2的会话没有正确注册到这些池中，导致服务器无法找到正确的连接来发送消息。

#### 2.2 Session ID 生成问题
在 [main.py](file://c:/work/open-webui/backend/open_webui/socket/main.py) 的 connect 和 user_join 事件处理器中，系统会为每个连接生成一个 session_id：
```python
import uuid
session_id = f"session_{user.id}_{uuid.uuid4().hex[:8]}"
```

如果站点2在生成或传递 session_id 时出现问题，可能导致消息无法正确路由。

#### 2.3 事件监听配置问题
在前端 [ws-tester.js](file://c:/work/open-webui/static/ws-tester.js) 中，正确设置了事件监听器：
```javascript
this.socket.on("hsai_response", (data) => this.handleResponse(payload));
this.socket.on("hsai_error", (data) => this.handleError(payload));
```

站点2可能没有正确设置这些事件监听器。

#### 2.4 用户池管理问题
在 [main.py](file://c:/work/open-webui/backend/open_webui/socket/main.py) 中，当用户断开连接时，系统会从 USER_POOL 中移除对应的SID。如果站点2在连接管理上存在问题，可能导致用户会话被错误地移除。

## 修复方案

### 方案1: 检查前端事件监听配置
确保站点2正确设置了事件监听器：

1. 在站点2的前端代码中，检查是否正确初始化了Socket.IO连接：
```javascript
const socket = io(baseUrl, {
  path: "/ws/socket.io",
  auth: { token: this.token },
  transports: ["websocket", "polling"],
  query: { user_id: this.userId || "" },
});
```

2. 确保正确绑定了事件处理器：
```javascript
socket.on("hsai_response", (data) => {
  console.log("收到hsai_response:", data);
  // 处理响应数据
});

socket.on("hsai_error", (data) => {
  console.log("收到hsai_error:", data);
  // 处理错误数据
});
```

### 方案2: 检查Session ID传递
确保站点2在发送消息时正确传递了session_id：

```javascript
const testMessage = {
  type: "chat",
  content: "测试消息",
  user_id: userId,
  entry_type: "chat",
  session_id: sessionId,  // 确保这个sessionId在连接时生成并保存
  timestamp: Date.now()
};

socket.emit("message", testMessage);
```

### 方案3: 后端会话管理增强
在 [main.py](file://c:/work/open-webui/backend/open_webui/socket/main.py) 中增强会话管理的日志记录，便于调试：

```python
# 在connect事件处理器中添加更多日志
log.info(f"📥 CONNECT事件 - SID: {sid}")
log.info(f"用户 {user.name} ({user.email}) 认证成功")
log.info(f"会话ID生成: {session_id}")
log.info(f"SESSION_POOL更新: {sid} -> {user_data}")
log.info(f"USER_POOL更新: {user.id} -> {USER_POOL[user.id]}")
log.info(f"SESSION_ID_TO_SID更新: {session_id} -> {sid}")
```

### 方案4: 添加连接状态检查接口
在后端添加一个API端点，用于检查特定用户的连接状态：

```python
# 在适当的路由文件中添加
@app.get("/api/v1/websocket/status/{user_id}")
async def get_websocket_status(user_id: str):
    """获取用户WebSocket连接状态"""
    from open_webui.socket.main import USER_POOL, SESSION_POOL
    
    if user_id in USER_POOL:
        sids = USER_POOL[user_id]
        sessions = []
        for sid in sids:
            if sid in SESSION_POOL:
                session_data = SESSION_POOL[sid]
                sessions.append({
                    "sid": sid,
                    "session_id": session_data.get("session_id"),
                    "connected_at": session_data.get("connected_at")
                })
        
        return {
            "user_id": user_id,
            "connected": True,
            "connections": sessions
        }
    else:
        return {
            "user_id": user_id,
            "connected": False,
            "connections": []
        }
```

## 验证步骤

1. 在站点2中添加详细的控制台日志，记录WebSocket连接和事件监听的每个步骤
2. 使用浏览器开发者工具检查网络选项卡，确认WebSocket连接和消息传输
3. 在后端添加更多日志记录，跟踪用户会话的创建和销毁过程
4. 使用上面提到的状态检查接口验证用户连接状态

## 预防措施

1. 在前端添加连接状态监控，及时发现和报告连接问题
2. 在后端添加会话超时清理机制，防止无效会话占用资源
3. 增强错误处理和重连机制，提高系统的健壮性