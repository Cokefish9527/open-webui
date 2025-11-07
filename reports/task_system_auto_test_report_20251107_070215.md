# 任务系统自动化测试报告
- 执行时间（UTC）: 2025-11-07T07:02:05.389232 - 2025-11-07T07:02:15.626812
- 行为结果: **PASSED**

## 账号信息
- 用户 ID: `92fa735d-fa03-4d4d-913b-a97898c2e4e9`
- 公司 ID: `fbd59e12-f1cb-4230-8e37-697aae75da7f`
- 登录邮箱: `auto-task.qu5dp4w8@example.com`
- 初始密码: `Aazg8e5e9i181l!`

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
- 消息 ID: `03466d72-30e7-4358-9ed2-76885e1ff767`

## 数据校验结果
- 校验状态: **passed**
```json
{
  "tasks": {
    "total": 7,
    "by_status": {
      "pending": 7
    },
    "tasks": [
      {
        "id": "2380a7a2-c4b6-4b83-a389-f9b42d72062c",
        "title": "完善企业信息",
        "status": "pending",
        "project_id": "6bd4964e-2295-4917-91fd-9aad57d76b3b",
        "created_at": 1762498928
      },
      {
        "id": "07892b51-2495-46d4-8152-fff42a059522",
        "title": "完善项目信息",
        "status": "pending",
        "project_id": "6bd4964e-2295-4917-91fd-9aad57d76b3b",
        "created_at": 1762498928
      },
      {
        "id": "567e9f70-196e-4ae7-9048-de0e32ac8a0e",
        "title": "素材库初始化",
        "status": "pending",
        "project_id": "6bd4964e-2295-4917-91fd-9aad57d76b3b",
        "created_at": 1762498928
      },
      {
        "id": "21ce03d0-3916-4d21-8ac3-5c0d6f56ee52",
        "title": "社媒矩阵创建",
        "status": "pending",
        "project_id": "6bd4964e-2295-4917-91fd-9aad57d76b3b",
        "created_at": 1762498930
      },
      {
        "id": "846a0a48-1d78-4ee4-abd5-0391d211bd24",
        "title": "素材补充",
        "status": "pending",
        "project_id": "6bd4964e-2295-4917-91fd-9aad57d76b3b",
        "created_at": 1762498931
      },
      {
        "id": "4ca31156-fe72-4b89-8227-ee0a90da2bb2",
        "title": "视频学习",
        "status": "pending",
        "project_id": "6bd4964e-2295-4917-91fd-9aad57d76b3b",
        "created_at": 1762498932
      },
      {
        "id": "fd004638-6bc6-4109-83f6-fcb64336813d",
        "title": "每日视频发布循环",
        "status": "pending",
        "project_id": "6bd4964e-2295-4917-91fd-9aad57d76b3b",
        "created_at": 1762498932
      }
    ]
  },
  "blueprint": {
    "projects": 1,
    "progress_records": 1,
    "progress_ids": [
      "77103422-3c4e-4ed4-9eb9-bb9f08dab47b"
    ],
    "history_records": 1,
    "task_links": 4
  },
  "outbox": {
    "total": 1,
    "events": [
      {
        "id": "553bf40d-cba7-45d3-8fbd-757ab6713aa6",
        "event_type": "onboarding.seed_summary",
        "status": "dispatched",
        "created_at": 1762498928
      }
    ]
  }
}
```

## 日志采集
- 匹配条数: 0

## 警告
- 无