# 任务系统自动化测试报告
- 执行时间（UTC）: 2025-11-07T06:57:13.206128 - 2025-11-07T06:57:20.506227
- 行为结果: **PASSED**

## 账号信息
- 用户 ID: `a8da58f6-227f-446b-9f46-3946b37215b7`
- 公司 ID: `3d04e0a8-1897-43fd-8a0c-03152f1d475c`
- 登录邮箱: `auto-task.hjwa40hd@example.com`
- 初始密码: `Aa7xovvhuaygiw!`

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
- 消息 ID: `0ba60d42-575f-4f60-ae33-79e6c624eaae`

## 数据校验结果
- 校验状态: **passed**
```json
{
  "tasks": {
    "total": 4,
    "by_status": {
      "pending": 4
    },
    "tasks": [
      {
        "id": "447aba65-3e9e-4c07-b400-ba6f011f0739",
        "title": "完善企业信息",
        "status": "pending",
        "project_id": "49986a76-9afb-4688-8188-57936849d4bd",
        "created_at": 1762498636
      },
      {
        "id": "4c120e90-7ea5-4dfc-9f04-5ad14029645c",
        "title": "完善项目信息",
        "status": "pending",
        "project_id": "49986a76-9afb-4688-8188-57936849d4bd",
        "created_at": 1762498636
      },
      {
        "id": "741876f7-7964-4d99-8c5f-2e6a17bd87d2",
        "title": "素材库初始化",
        "status": "pending",
        "project_id": "49986a76-9afb-4688-8188-57936849d4bd",
        "created_at": 1762498636
      },
      {
        "id": "b1f4a940-3ef0-45ba-9823-9e0867eb2f85",
        "title": "社媒矩阵创建",
        "status": "pending",
        "project_id": "49986a76-9afb-4688-8188-57936849d4bd",
        "created_at": 1762498638
      }
    ]
  },
  "blueprint": {
    "projects": 1,
    "progress_records": 1,
    "progress_ids": [
      "7826f32d-78d9-4657-945c-48229763c233"
    ],
    "history_records": 1,
    "task_links": 1
  },
  "outbox": {
    "total": 1,
    "events": [
      {
        "id": "f38bcd44-ea74-44b7-b5b8-1ad68fb80870",
        "event_type": "onboarding.seed_summary",
        "status": "dispatched",
        "created_at": 1762498636
      }
    ]
  }
}
```

## 日志采集
- 匹配条数: 0

## 警告
- 无