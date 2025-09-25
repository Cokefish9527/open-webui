# 智能对话消息转发与n8n工作流集成系统

## Core Features

- 智能工作流选择
- 基于对话入口的智能工作流路由
- 动态Webhook调度
- 结果结构化处理
- 实时消息推送
- 工作流管理
- 异步消息处理
- 工作流状态监控
- 爆款学习工作流的循环调用策略
- 定时策略控制系统
- 视频分析工作流的内部调用限制
- 系统监控和健康检查

## Tech Stack

{
  "Backend": "Python FastAPI + WebSocket",
  "HTTP Client": "aiohttp",
  "Async Processing": "asyncio",
  "Config Management": "Pydantic",
  "Logging": "Python logging",
  "Framework": "FastAPI",
  "WebSocket": "FastAPI WebSocket",
  "Data Validation": "Pydantic"
}

## Design

事件驱动的异步架构，支持智能路由、实时推送和完善的错误处理机制。基于现有hsai_websocket.py扩展，集成n8n工作流调度，实现消息转发和结构化处理。实现了基于对话入口点的智能工作流协同系统，根据不同的对话场景自动选择合适的n8n工作流（主工作流或信息收集工作流），同时为爆款学习工作流实现了独立的循环调用策略和定时控制，确保视频分析工作流仅限于n8n内部调用。

**注意**: n8n工作流的具体实现由n8n开发者自行设计实现，本文档仅说明系统中与n8n工作流集成的相关部分。

## 工作流集成架构

### 三个核心n8n工作流
1. **信息收集工作流**：https://webhook-n8n.hsai.cc/webhook/business_information_get01
2. **主对话工作流**：https://webhook-n8n.hsai.cc/webhook/n8n_chat
3. **爆款学习工作流**：https://webhook-n8n.hsai.cc/webhook/keywords2video

### 智能路由机制
- 根据消息内容和场景规则匹配合适的工作流
- 基于对话入口点进行工作流选择
- 支持手动指定工作流类型
- 实现循环调用策略和定时控制

### 消息处理流程
1. 接收前端WebSocket消息
2. 智能选择对应的n8n工作流
3. 异步调用n8n webhook
4. 结构化处理返回结果
5. 通过WebSocket实时推送给前端
6. 完善的错误处理和日志监控

## 系统优化特性

### 异步处理优化
- 支持高并发消息处理
- 异步HTTP客户端调用
- 非阻塞式工作流执行

### 状态监控机制
- 工作流执行状态跟踪
- 实时进度反馈
- 系统健康检查
- 详细的执行日志记录

### 错误处理策略
- 完整的异常捕获机制
- 自动重试逻辑
- 降级处理方案
- 用户友好的错误提示