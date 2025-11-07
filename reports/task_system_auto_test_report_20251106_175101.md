# 任务系统自动化测试报告
- 执行时间（UTC）: 2025-11-06T17:49:22.801053 - 2025-11-06T17:51:01.506391
- 行为结果: **WARNING**

## 账号信息
- 用户 ID: `0d4f4305-119c-4e34-8a0d-84699fb3ede0`
- 公司 ID: `31695eb7-b133-4e0b-9f95-000a58176122`
- 登录邮箱: `auto-task.i99w40ps@example.com`
- 初始密码: `Aar110uhqu1zrm!`

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
- 消息 ID: `3bb316d8-5034-4816-a7b8-ed0ff35fa28b`

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