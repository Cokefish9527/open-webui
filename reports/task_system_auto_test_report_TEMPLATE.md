# 任务系统自动化测试报告模板

> 此模板由 `tool/orchestrate_task_system_auto_test.py` 自动生成具体报告时参考。

## 元信息
- 执行时间：`<START> - <END>`
- 状态：`<STATUS>`
- 触发方式：`自动化脚本`

## 账号信息
- 用户 ID：`<USER_ID>`
- 公司 ID：`<COMPANY_ID>`
- 邮箱：`<EMAIL>`
- 初始密码：`<PASSWORD>`

## 数据重置摘要
```json
<RESET_SUMMARY_JSON>
```

## 蓝图触发
- Redis 队列：`<QUEUE>`
- 消息 ID：`<MESSAGE_ID>`

## 数据校验结果
- 校验状态：`<VERIFY_STATUS>`
```json
<VERIFY_DETAILS_JSON>
```

## 日志扫描
- 命中条数：`<LOG_MATCH_COUNT>`
```text
<LOG_LINES>
```

## 警告
- `<WARNING 1>`
- `<WARNING 2>`

> 若测试失败或存在告警，请根据报告内容定位问题，并将调查结论同步至 PROJECTWIKI.md 的“任务系统自动化测试流程”章节。
