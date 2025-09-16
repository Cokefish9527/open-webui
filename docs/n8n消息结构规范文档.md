# n8n消息结构规范文档

## 1. n8n与服务端交互的消息结构

### 1.1 服务端发送给n8n的请求结构

```json
{
  "session_id": "会话ID",
  "user_id": "用户ID",
  "message": "用户消息内容",
  "business_name": "业务名称（HSAI）",
  "timestamp": 1234567890123,
  "request_id": "请求ID"
}
```

字段说明：
- `session_id`: 会话ID
- `user_id`: 用户ID
- `message`: 用户消息内容
- `business_name`: 业务名称（HSAI）
- `timestamp`: 时间戳，毫秒级unixtime
- `request_id`: 请求ID，用于唯一标识一次请求

### 1.2 n8n通过Redis发送给服务端的消息结构

```json
{
  "env": "gray",
  "session_id": "会话ID",
  "reply_id": "回复ID",
  "reply_seq": 1,
  "reply_message_id": "响应的message_id",
  "operate_id": "操作ID",
  "status": "FINISHED",
  "content_type": 1,
  "content": {
    "text": "内容文本",
    "data": {
      "actions": ["view", "download", "export", "report", "images"],
      "title": "任务名",
      "markdown": "markdown文本",
      "images": ["", ""],
      "question": "问题文本",
      "selections": [
        "选项1文本",
        "选项2文本",
        "选项3文本"
      ],
      "multi_selections": [
        {
          "question": "是否使用监控数据",
          "options": ["使用", "不使用"]
        },
        {
          "question": "是否使用画像数据",
          "options": ["使用", "不使用"]
        }
      ],
      "period": "{{开始时间}},{{结束时间}}",
      "filters": [
        {
          "name": "筛选名",
          "filter_type": "筛选类型",
          "value": "筛选值"
        }
      ]
    }
  },
  "create_ts": 1272341234
}
```

字段说明：
- `env`: 环境，值为gray（灰度）或prod（生产）
- `session_id`: 会话ID
- `reply_id`: 回复ID
- `reply_seq`: 回复序号，用于容错机制
- `reply_message_id`: 响应的message_id
- `operate_id`: 该次请求中区分操作的ID
- `status`: 状态，值为RUNNING（表示还未输出完）或FINISHED（已完成）
- `content_type`: 内容类型，1-processing, 2-pre_text, 3-text, 4-thinking, 5-result, 6-selection
- `content`: 内容对象，包含text和data字段
  - `text`: 内容文本
  - `data`: 具体数据内容，包含以下字段：
    - `actions`: 用户期望行为，如view-查看, download-下载, export-导出, report-报告, images-图片
    - `title`: 任务名（content_type=5时使用）
    - `markdown`: markdown文本
    - `images`: 图片结果数组
    - `question`: 问题文本
    - `selections`: 选项数组
    - `multi_selections`: 多选题数组，每个元素包含question和options字段
    - `period`: 时间范围，格式为"{{开始时间}},{{结束时间}}"
    - `filters`: 推荐筛选数组，每个元素包含name、filter_type和value字段
- `create_ts`: 创建时间戳，使用unixtime格式

注意：
- 取消params字段
- create_ts字段使用unixtime格式

## 2. 容错机制

服务端需要实现基于message_id的容错机制：
- 在reply_message_id相同的情况下，使用reply_seq数字最大的消息
- 确保前端接收到的是最新的消息内容