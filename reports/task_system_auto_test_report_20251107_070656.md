# 任务系统自动化测试报告
- 执行时间（UTC）: 2025-11-07T07:06:46.554616 - 2025-11-07T07:06:56.675605
- 行为结果: **PASSED**

## 账号信息
- 用户 ID: `ff3a4421-f21f-4fba-820b-38b728d9a0d0`
- 公司 ID: `fa976d71-1d50-478e-a726-3b06ef09761d`
- 登录邮箱: `auto-task.puz8wg5r@example.com`
- 初始密码: `Aapj2pd3mpvefm!`

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
- 消息 ID: `841a4c3c-add5-4573-8788-e4974f5f0d12`

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
        "id": "e5bea918-2e38-4fc9-abcc-f6be1bc463f2",
        "title": "素材补充",
        "status": "pending",
        "project_id": "77dcb593-a45f-4ab0-9c8e-f4e3e5c22126",
        "created_at": 1762499212
      },
      {
        "id": "72ae0f76-dcaf-40de-af4b-24c349105786",
        "title": "视频学习",
        "status": "pending",
        "project_id": "77dcb593-a45f-4ab0-9c8e-f4e3e5c22126",
        "created_at": 1762499213
      },
      {
        "id": "04c4a702-b8f2-4e5c-b767-773421374d48",
        "title": "完善企业信息",
        "status": "pending",
        "project_id": "77dcb593-a45f-4ab0-9c8e-f4e3e5c22126",
        "created_at": 1762499209
      },
      {
        "id": "36723a32-f648-47aa-8927-a46b2f5f8ed1",
        "title": "完善项目信息",
        "status": "pending",
        "project_id": "77dcb593-a45f-4ab0-9c8e-f4e3e5c22126",
        "created_at": 1762499209
      },
      {
        "id": "c3628756-bb51-4c06-b1b8-8c46d0c22ee0",
        "title": "素材库初始化",
        "status": "pending",
        "project_id": "77dcb593-a45f-4ab0-9c8e-f4e3e5c22126",
        "created_at": 1762499209
      },
      {
        "id": "dd66741b-86fc-43ae-a5b1-850062c98717",
        "title": "社媒矩阵创建",
        "status": "pending",
        "project_id": "77dcb593-a45f-4ab0-9c8e-f4e3e5c22126",
        "created_at": 1762499211
      },
      {
        "id": "a33c7077-d487-4d21-8058-4d88ba61497b",
        "title": "每日视频发布循环",
        "status": "pending",
        "project_id": "77dcb593-a45f-4ab0-9c8e-f4e3e5c22126",
        "created_at": 1762499213
      }
    ]
  },
  "blueprint": {
    "projects": 1,
    "progress_records": 1,
    "progress_ids": [
      "7dcde555-fd40-4819-83d6-e56a0fb01747"
    ],
    "history_records": 1,
    "task_links": 4
  },
  "outbox": {
    "total": 1,
    "events": [
      {
        "id": "d8b19f35-0480-4985-8a65-d5d5041e9a03",
        "event_type": "onboarding.seed_summary",
        "status": "dispatched",
        "created_at": 1762499209
      }
    ]
  }
}
```

## 日志采集
- 匹配条数: 0

## 警告
- 无