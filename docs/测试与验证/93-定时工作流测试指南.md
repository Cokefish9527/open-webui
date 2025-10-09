# 定时工作流测试指南

本文档说明如何正确测试定时工作流，确保它们按照预期的行为执行，而不影响主应用程序的启动流程。

## 问题背景

在之前的实现中，定时工作流调度器在应用程序启动时会立即执行工作流，这不符合设计要求。工作流应该只在实际需要时执行，而不是在程序启动时自动执行。

## 解决方案

我们修改了调度器的实现，使其在启动时不立即执行工作流，而是等待第一个调度周期。

## 配置说明

病毒学习工作流的定时调度可以通过环境变量进行配置：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| VIRAL_LEARNING_ENABLED | true | 是否启用定时调度器，设置为空值、"false"、"0"或"no"可禁用 |
| VIRAL_LEARNING_INTERVAL_MINUTES | 30 | 调度间隔（分钟） |
| VIRAL_LEARNING_MAX_DAILY_CALLS | 48 | 每日最大调用次数 |
| VIRAL_LEARNING_START_HOUR | 8 | 工作时间开始小时（24小时制） |
| VIRAL_LEARNING_END_HOUR | 22 | 工作时间结束小时（24小时制） |
| VIRAL_LEARNING_RETRY_ATTEMPTS | 3 | 失败重试次数 |
| VIRAL_LEARNING_RETRY_DELAY_MINUTES | 5 | 重试间隔（分钟） |

### 配置示例

禁用定时调度器：
```bash
export VIRAL_LEARNING_ENABLED=false
```

或者设置为空值：
```bash
export VIRAL_LEARNING_ENABLED=
```

自定义调度间隔：
```bash
export VIRAL_LEARNING_INTERVAL_MINUTES=60
export VIRAL_LEARNING_MAX_DAILY_CALLS=24
```

## 测试方法

### 1. 自动化测试

使用我们提供的测试脚本来验证调度器的行为：

```bash
# 运行定时工作流测试
cd backend
python test_scheduled_workflows.py
```

这个测试会：
1. 启动病毒学习调度器
2. 验证调度器已启动但未执行工作流
3. 运行5分钟观察调度器行为
4. 停止调度器并报告结果

### 2. 配置测试

测试不同配置值的处理：

```bash
# 运行配置测试
cd backend
python test_viral_learning_config.py
```

### 3. 手动测试

您也可以通过以下步骤手动验证：

1. 启动应用程序：
   ```bash
   python main.py
   ```

2. 观察启动日志，确认没有立即执行病毒学习工作流

3. 等待调度周期（默认30分钟）或修改配置以缩短时间间隔进行测试

### 4. 集成测试

在集成测试中，我们提供了专门的方法来测试病毒学习工作流：

```bash
# 运行n8n集成测试
cd backend
python test_n8n_integration.py
```

这个测试会通过正常的工作流触发机制来测试病毒学习工作流，而不是通过定时调度器。

## 验证点

测试时需要验证以下几点：

1. 应用程序启动时不应执行定时工作流
2. 当配置为禁用（enabled=false或空值）时，调度器不应启动
3. 当配置项为空值时，应使用默认值
4. 调度器应正确启动并等待第一个调度周期
5. 在工作时间内的调度周期应正确执行工作流
6. 超出工作时间或达到每日限制时应正确跳过执行
7. 调度器应能正确停止和清理资源

## 注意事项

1. 不要修改主应用程序的启动逻辑来适应测试需求
2. 测试脚本应独立于主应用程序运行
3. 确保定时工作流的测试不会影响生产环境
4. 使用测试配置而不是生产配置进行测试
5. 配置为空值时，调度器应正确处理并使用合理的默认值