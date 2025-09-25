# AI驱动的n8n智能工作流协作系统

## Core Features

- 基于现有工作流的渐进式升级
- 三个核心n8n工作流集成
- Socket.IO实时通信
- Redis信号机制优化
- 统一消息结构处理
- 长任务状态同步
- 智能任务路由
- 可视化工作流监控

## Tech Stack

{
  "Frontend": {
    "communication": "OpenWebUI原生Socket.IO",
    "framework": "基于现有OpenWebUI架构"
  },
  "Backend": "FastAPI + Socket.IO服务端，WebHook与n8n通信",
  "Workflow": "n8n工作流引擎，三个核心工作流",
  "Database": "扩展现有数据库schema，Redis信号机制",
  "Communication": "前端Socket.IO + 服务端WebHook + Redis信号"
}

## Design

保持现有系统架构，通过Socket.IO实现前后端实时通信，服务端通过WebHook与n8n工作流通信，采用Redis信号机制优化长任务处理体验，对n8n返回的字符串进行重新组织以符合前端数据结构要求。

## 三个核心工作流

### 1. 信息收集工作流
- **URL**: https://webhook-n8n.hsai.cc/webhook/business_information_get
- **功能**: 用户首次使用时触发，收集用户信息并创建初始项目
- **流程**: 信息收集 → KPI计算 → 任务拆解 → Redis信号通知

### 2. 主对话工作流
- **URL**: https://webhook-n8n.hsai.cc/webhook/n8n_chat
- **功能**: 协助用户完成视频合成发布任务
- **流程**: 任务沟通 → 脚本推荐 → 视频合成 → 预览确认 → 发布

### 3. 爆款学习工作流
- **URL**: https://webhook-n8n.hsai.cc/webhook/keywords2video
- **功能**: 抓取和学习热门视频，更新脚本库
- **流程**: 视频抓取 → 用户确认 → 内容分析 → 脚本入库

## 通信架构

```
前端(Socket.IO) ←→ 服务端 ←→ n8n(WebHook) ←→ Redis信号
                     ↓
                数据重组处理
                     ↓
                Socket.IO推送
```

## 系统优化特性

### 智能路由机制
- 根据消息内容和场景规则匹配合适的工作流
- 基于对话入口点进行工作流选择
- 支持手动指定工作流类型
- 实现循环调用策略和定时控制

### 消息处理流程
1. 接收前端WebSocket消息
2. 智能选择对应的n8n工作流
3. 转发消息并等待响应
4. 对响应进行结构化处理
5. 通过WebSocket推送给前端
6. 异步处理长任务状态同步

### 长任务优化
- Redis信号机制实现实时状态通知
- 爆款学习工作流的循环调用策略
- 定时策略控制系统
- 视频分析工作流的内部调用限制

## 统一工作流编排中心

### 工作流注册表
```javascript
const WorkflowRegistry = {
  "main-workflow": {
    id: "hROwwd7UTCzQeFxj",
    name: "主工作流",
    type: "orchestrator",
    dependencies: ["keywords2videotext", "videotext2videojson", "videojson2video", "videototk"],
    status: "active",
    version: "v1.0"
  },
  "company-info-collection": {
    id: "cXeGsB422GErqFvi", 
    name: "公司信息收集及作战地图梳理",
    type: "data-processor",
    dependencies: ["keywords_agent"],
    status: "active",
    version: "v1.0"
  },
  "viral-learning": {
    id: "VuLYqKoSILQRHJ1r",
    name: "被动触发爆款学习", 
    type: "scheduler",
    dependencies: ["video-scraping"],
    status: "active",
    version: "v1.0"
  }
}
```

### 依赖关系管理
```javascript
const DependencyGraph = {
  "main-workflow": {
    upstream: ["company-info-collection"],
    downstream: ["keywords2videotext", "videotext2videojson", "videojson2video", "videototk"],
    dataFlow: ["session_context", "business_info", "user_preferences"]
  },
  "company-info-collection": {
    upstream: [],
    downstream: ["main-workflow", "viral-learning"],
    dataFlow: ["enterprise_info", "keywords", "strategy_map"]
  },
  "viral-learning": {
    upstream: ["company-info-collection"],
    downstream: ["video-scraping"],
    dataFlow: ["keywords_list", "business_context"]
  }
}
```

### 状态管理机制
- 全局状态跟踪：activeWorkflows、executionQueue、resourceUsage
- 跨工作流状态同步
- 依赖通知机制
- 异步消息处理
- 工作流状态监控

## 系统监控和健康检查

### 监控指标
- 工作流执行状态和进度
- 消息转发成功率
- Redis信号响应时间
- 系统资源使用情况

### 健康检查机制
- 定期检查n8n工作流可用性
- WebSocket连接状态监控
- Redis信号机制健康检查
- 数据库连接状态验证


