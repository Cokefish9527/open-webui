# 消息结构规范文档

## 1. 前端-服务端交互消息体

### 1.1 前端发送给服务端的消息结构

```json
{
  "type": "chat", // 或 "workflow_trigger"
  "content": "用户输入的消息内容",
  "entry_type": "入口类型（可选，默认为chat）",
  "metadata": {
    // 其他元数据
  }
}
```

字段说明：
- `type`: 消息类型，固定为"chat"或"workflow_trigger"
- `content`: 用户输入的消息内容
- `entry_type`: 入口类型，用于服务端判断使用哪个工作流
- `metadata`: 其他元数据

注意：
- user_id、session_id、business_name由服务端从会话中直接获取
- workflow_type由服务端根据entry_type判断，前端不需要指定

### 1.2 服务端发送给前端的消息结构

```json
{
  "type": "hsai_response", // 或其他事件类型如"workflow_status"、"task_complete"等
  "success": true,
  "execution_id": "执行ID",
  "session_id": "会话ID",
  "user_id": "用户ID",
  "execution_time": "0.0s",
  "timestamp": 1234567890,
  "messageType": 3,
  "displayText": "显示文本",
  "data": {
    // 具体数据内容，参考Agent2Redis消息体的data字段
  },
  "status": "FINISHED"
}
```

字段说明：
- `type`: 消息类型
- `success`: 是否成功
- `execution_id`: 执行ID，用于唯一标识一次工作流调用
- `session_id`: 会话ID
- `user_id`: 用户ID
- `execution_time`: 执行时间，使用时间字符串格式，如"0.0s"
- `timestamp`: 时间戳，使用标准的unixtime
- `messageType`: 消息类型，参考Agent2Redis消息体的content_type字段
- `displayText`: 显示文本
- `data`: 数据内容，参考Agent2Redis消息体的data字段
- `status`: 状态，使用Agent2Redis的status字段

注意：
- 取消workflow_type、workflow_name字段
- 取消result、output、steps_completed字段

## 2. 服务端-n8n交互结构体

### 2.1 服务端发送给n8n的请求结构

```json
{
  "session_id": "会话ID",
  "user_id": "用户ID",
  "message": "用户消息内容",
  "timestamp": 1234567890123,
  "request_id": "请求ID",
  // additional_data中的其他字段
}
```

### 2.2 n8n通过Redis发送给服务端的消息结构

```json
{
  "env": "gray", // 环境 gray/prod
  "session_id": "", // 会话id
  "reply_id": "", // 回复id
  "reply_seq": 1, // 回复序号
  "reply_message_id": "", // 响应的message_id
  "operate_id": "", // 该次请求中区分操作的id
  "status": "FINISHED", // RUNNING-表示还未输出完/FINISHED
  "content_type": 1, // 内容类型 1-processing 2-pre_text 3-text 4-thinking 5-result 6-selection
  "content": {
    "text": "", // 内容文本
    "data": {
      // 用户期望行为 view-查看 download-下载 export-导出 report-报告 images-图片
      "actions": ["view", "download", "export", "report", "images"],
      "title": "", // content_type=5时是任务名
      "markdown": "", // markdown文本
      "images": ["", ""], // 图片结果
      "question": "",
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
      "filters": [ // 推荐筛选
        {
          "name": "", // 筛选名
          "filter_type": "", // 筛选类型 age/style/coupon_cprice/gender
          "value": "" // 筛选值
        }
      ]
    } // json数据
  },
  "create_ts": 1272341234 // unixtime格式
}
```

注意：
- 取消params字段
- create_ts字段使用unixtime格式

## 3. 容错机制

服务端需要实现基于message_id的容错机制：
- 在reply_message_id相同的情况下，使用reply_seq数字最大的消息
- 确保前端接收到的是最新的消息内容