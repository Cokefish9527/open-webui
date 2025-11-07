# 任务系统自动化测试报告
- 执行时间（UTC）: 2025-11-06T17:52:29.311099 - 2025-11-06T17:52:55.004799
- 行为结果: **WARNING**

## 账号信息
- 用户 ID: `5dcfc70f-cc36-4fd3-8b3c-f26b149bb933`
- 公司 ID: `c21c47d0-6a40-470d-bc94-c0eb3e273468`
- 登录邮箱: `auto-task.cvqx35yv@example.com`
- 初始密码: `Aa8osjjfkeihln!`

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
- 消息 ID: `7ed69600-0811-44c0-b116-c902d5bc5532`

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
    "events": []
  }
}
```

## 日志采集
- 匹配条数: 0

## 警告
- 未找到任何任务记录
- 未找到蓝图进度记录
- 未找到 Outbox 事件，检查是否运行了蓝图同步