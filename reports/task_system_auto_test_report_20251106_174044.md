# 任务系统自动化测试报告
- 执行时间（UTC）: 2025-11-06T17:39:09.134742 - 2025-11-06T17:40:44.999935
- 行为结果: **WARNING**

## 账号信息
- 用户 ID: `ca6df8f0-c722-42dd-bb13-5ea4e36a83d1`
- 公司 ID: `fc22488c-8fa1-4d60-b1cd-ed502beb55da`
- 登录邮箱: `auto-task.aaquak07@example.com`
- 初始密码: `Aae7d5894hl10g!`

## 数据重置摘要
```json
{
  "tasks": 0,
  "task_logs": 0,
  "task_links": 0,
  "blueprint_progress": 0,
  "blueprint_history": 0,
  "projects": 0,
  "companies": 1
}
```

## 蓝图触发结果
- Redis 队列: `ai-conversation-agent-message-queue`
- 消息 ID: `48f0a5db-1d3d-4064-9c24-686a80a8a08c`

## 数据校验结果
- 校验状态: **failed**
```json
{
  "tasks": {
    "total": 0,
    "by_status": {},
    "tasks": []
  },
  "blueprint": {
    "projects": 0,
    "progress_records": 0,
    "progress_ids": [],
    "history_records": 0,
    "task_links": 0
  },
  "outbox": {
    "total": 0,
    "events": [],
    "warning": "hsai_outbox_events table missing"
  }
}
```

## 日志采集
- 匹配条数: 0

## 警告
- 未找到任何任务记录
- 未找到蓝图进度记录
- 未找到 Outbox 事件，检查是否运行了蓝图同步