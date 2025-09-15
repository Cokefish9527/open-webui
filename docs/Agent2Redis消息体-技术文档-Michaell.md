## Agent -> 后端消息

Agent写入Redis，之后转到MQ

* 实例: xxx

* redisKey: xxxx

* DB

   * 灰度：xxx

   * 线上：xxx

* 写入方式：lpush

后端从redis中读取数据

* 读取方式：brpop

* 消息结构

```json
{
  "env": "gray",        // 环境 gray/prod
  "session_id": "", // 会话id
  "reply_id": "",      // 回复id
  "reply_seq": 1,      // 回复序号
  "reply_message_id": "", //  响应的message_id
  "operate_id": "",          // 该次请求中区分操作的id
  "status": "FINISHED",          // RUNNING-表示还未输出完/FINISHED
  "content_type": 1, // 内容类型 1-processing 2-pre_text 3-text 4-thinking 5-result 6-selection
  "content": {
    "text": "",    // 内容文本
    "data": {
      // 用户期望行为 view-查看 download-下载 export-导出 report-报告 images-图片
      "actions": ["view", "download", "export", "report", "images"], 
      "title": "",      // content_type=5时是任务名
      "markdown": "", // markdown文本
      "images": ["",""], // 图片结果
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
      "filters": [      // 推荐筛选
        {
          "name": "",     // 筛选名
          "filter_type": "",  // 筛选类型 age/style/coupon_cprice/gender
          "value" : ""      // 筛选值
        }
      ],
      "params": {
        "team_id": "",
        "user_id": "",
        "group_id_list": "",
        "category_id_list": ""
      }
    }      // json数据
  },
  "create_ts": 1272341234
}
```



