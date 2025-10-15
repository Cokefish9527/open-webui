# 视频学习通知功能说明

## 功能概述

本功能实现了对Redis队列中视频学习通知的监听和处理。当视频学习任务完成后，系统会向Redis队列`video_learning_notification`发送通知消息，包含视频ID和学习结果状态。

## 消息格式

```json
{
  "video_id": 1,
  "status": "success/failed",
  "business_name": "HSAI"  // 可选，公司名称
}
```

## 处理逻辑

1. 当Redis队列`video_learning_notification`中有新消息时，系统会自动处理
2. 根据消息中的`status`字段处理视频学习状态：
   - `success` -> 学习状态设为"已学习"
   - `failed` -> 删除视频学习状态记录，重置为"待学习"
3. 所有状态变更都会记录日志到`hsai_video_learning_logs`表中
4. 所有操作都会记录日志便于追踪

## 测试方法

### 1. 使用测试脚本发送消息

```bash
# 发送成功状态的通知
python test_redis_queue.py send 1 success

# 发送失败状态的通知
python test_redis_queue.py send 2 failed
```

### 2. 手动向Redis队列发送消息

使用Redis命令行工具：

```bash
# 发送成功状态的通知
redis-cli LPUSH video_learning_notification '{"video_id": 1, "status": "success", "business_name": "HSAI"}'

# 发送失败状态的通知
redis-cli LPUSH video_learning_notification '{"video_id": 2, "status": "failed", "business_name": "HSAI"}'
```

## 验证处理结果

可以通过查询数据库表来验证处理结果：

```sql
-- 查询视频学习状态
SELECT * FROM hsai_video_learning_status WHERE video_id = '1';

-- 查询视频学习日志
SELECT * FROM hsai_video_learning_logs WHERE video_id = '1' ORDER BY created_at DESC;
```

## 日志查看

处理过程中的所有操作都会记录在应用日志中，可以查看相关日志来确认处理是否成功。

## 错误处理

- 如果消息格式不正确，系统会记录错误日志但不会中断处理流程
- 如果数据库操作失败，系统会记录错误日志并抛出异常
- 系统会自动重试失败的操作（根据Redis信号处理器的配置）