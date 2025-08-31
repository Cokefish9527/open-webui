# n8n工作流集成的对话消息转发服务

## Core Features

- 智能工作流路由

- 异步消息处理

- 结构化数据处理

- 实时消息推送

- 工作流状态监控

## Tech Stack

{
  "language": "Python",
  "framework": "FastAPI",
  "websocket": "FastAPI WebSocket",
  "http_client": "aiohttp",
  "data_validation": "Pydantic",
  "async_processing": "asyncio"
}

## Design

基于现有hsai_websocket.py扩展，集成n8n工作流调度，实现消息转发和结构化处理

## Plan

Note: 

- [ ] is holding
- [/] is doing
- [X] is done

---

[X] 分析现有WebSocket处理器并扩展n8n集成功能

[X] 实现n8n工作流调度器，支持webhook调用和响应处理

[X] 开发消息结构化处理器，标准化n8n返回数据格式

[X] 集成工作流路由逻辑到WebSocket消息处理流程

[X] 添加错误处理和监控机制，确保系统稳定性

[X] 测试和优化整体消息转发性能
