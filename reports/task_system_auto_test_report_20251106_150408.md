# 任务系统自动化测试报告
- 执行时间（UTC）: 2025-11-06T15:02:32.061073 - 2025-11-06T15:04:08.443483
- 行为结果: **WARNING**

## 账号信息
- 用户 ID: `57c34b14-8221-4590-be81-6aa852132a1d`
- 公司 ID: `88c3b0cc-6948-48f4-a46d-96129f584deb`
- 登录邮箱: `auto-task.oft5ls1g@example.com`
- 初始密码: `Aanxtdu5jeidwr!`

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
- 消息 ID: `d27a7d1f-0376-46f6-a44f-f08c62c307a8`

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