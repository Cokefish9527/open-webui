# Redis测试脚本使用说明

## 概述

本目录包含用于测试Redis队列消息发送和监听的脚本，主要用于验证系统消息处理流程。

## 脚本说明

### 1. send_test_blueprint_message.py
发送一个完整的蓝图消息到Redis队列，用于测试消息处理流程。

**功能：**
- 构造包含指定session_id、user_id和socket_id的蓝图消息
- 将消息发送到`ai-conversation-agent-message-queue`队列
- 验证消息是否成功发送

**使用方法：**
```bash
cd c:\work\open-webui
python tool/send_test_blueprint_message.py
```

### 2. send_quick_test_message.py
发送一个简单的测试消息到Redis队列，用于快速测试。

**功能：**
- 构造简单的测试消息
- 支持自定义session_id、user_id和socket_id
- 快速验证消息发送功能

**使用方法：**
```bash
cd c:\work\open-webui
python tool/send_quick_test_message.py [session_id] [user_id] [socket_id]
```

**示例：**
```bash
# 使用默认ID发送消息
python tool/send_quick_test_message.py

# 使用自定义ID发送消息
python tool/send_quick_test_message.py my-session-id my-user-id my-socket-id
```

### 3. listen_to_queue.py
监听Redis队列中的消息，用于验证消息是否正确到达队列。

**功能：**
- 监听`ai-conversation-agent-message-queue`队列
- 实时显示接收到的消息内容
- 验证消息中的ID和内容是否正确

**使用方法：**
```bash
cd c:\work\open-webui
python tool/listen_to_queue.py
```

## 使用场景

1. **测试消息处理流程**：验证系统能否正确接收、处理和转发Redis队列中的消息
2. **调试消息内容**：检查消息中的ID和内容是否按预期设置
3. **验证连接机制**：测试socket_id、session_id和user_id的连接查找逻辑
4. **系统集成测试**：在系统集成时验证各组件间的消息传递

## 注意事项

1. 确保Redis服务正在运行
2. 确保项目环境已正确配置
3. 脚本使用项目中的REDIS_URL配置连接Redis
4. 消息发送后，可通过监听脚本验证消息是否正确到达队列