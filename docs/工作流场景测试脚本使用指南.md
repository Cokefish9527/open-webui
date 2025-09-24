# 工作流场景测试脚本使用指南

## 概述

本测试套件用于模拟前端在不同场景下通过服务端向n8n工作流发送消息的完整流程测试，覆盖企业信息收集、视频创作、视频分析等核心业务场景。

## 测试架构

```
前端模拟 → WebSocket → 工作流编排中心(WOC) → n8n工作流
                  ↓
               测试验证与报告
```

## 文件说明

### 核心测试脚本

1. **`test_workflow_scenarios.py`** - 基础版测试脚本
   - 支持多种测试模式
   - 基本的工作流场景测试
   - 命令行参数支持

2. **`enhanced_workflow_tester.py`** - 增强版测试脚本 ⭐推荐
   - 配置文件支持
   - 详细测试报告生成
   - 数据驱动测试
   - 重试机制
   - 性能监控

### 配置文件

3. **`test_config.json`** - 测试配置文件
   - 服务器连接配置
   - 测试场景定义
   - 测试数据
   - 期望结果验证

### 启动脚本

4. **`run_workflow_tests.bat`** - Windows批处理启动脚本
   - 自动检测Python环境
   - 交互式模式选择
   - 错误处理和调试信息

5. **`run_workflow_tests.ps1`** - PowerShell启动脚本
6. **`test_websocket_connection.py`** - WebSocket连接测试脚本 🔧
7. **`WORKFLOW_TESTING_GUIDE.md`** - 详细使用指南
   - 跨平台支持
   - 参数化执行
   - 更好的错误处理

## 快速开始

### 方式一：使用PowerShell脚本 (推荐)

```powershell
# 运行增强版综合测试
.\run_workflow_tests.ps1 -TestMode enhanced

# 运行快速测试
.\run_workflow_tests.ps1 -TestMode quick

# 运行完整测试
.\run_workflow_tests.ps1 -TestMode full

# 交互式选择模式
.\run_workflow_tests.ps1
```

### 方式二：使用批处理脚本

```batch
# 双击运行或命令行执行
run_workflow_tests.bat
```

### 方式三：直接运行Python脚本

```bash
# 基础版测试
python test_workflow_scenarios.py quick
python test_workflow_scenarios.py full

# 增强版测试
python enhanced_workflow_tester.py test_config.json
```

### 方式四：测试WebSocket连接（问题排查）

```bash
# 单独测试WebSocket连接是否正常
python test_websocket_connection.py
```

## 测试模式说明

### 1. 快速测试 (quick)
- **目的**: 基本功能验证
- **包含**: WOC健康检查、WOC状态查询、企业信息收集工作流
- **耗时**: ~1-2分钟
- **适用**: 快速验证系统是否正常

### 2. 完整测试 (full)
- **目的**: 全面功能验证
- **包含**: 所有快速测试项目 + 视频创作、视频分析、直接触发、用户执行列表
- **耗时**: ~3-5分钟
- **适用**: 全面测试所有功能

### 3. 专项测试
- **company_info**: 企业信息收集专项测试
- **video_creation**: 视频创作专项测试
- **video_analysis**: 视频分析专项测试
- **woc_management**: WOC管理功能专项测试

### 4. 增强版测试 (enhanced) ⭐推荐
- **目的**: 数据驱动的综合测试
- **特点**: 配置文件支持、详细报告、重试机制
- **包含**: 用户登录 + WOC健康检查 + 多场景随机测试
- **输出**: JSON格式详细测试报告

## 测试场景覆盖

### 1. 企业信息收集场景
```json
{
  "测试内容": "企业信息收集和竞品分析",
  "工作流": "company_info",
  "entry_type": "company",
  "验证点": ["工作流路由正确", "n8n调用成功", "响应格式正确"]
}
```

### 2. 视频创作场景
```json
{
  "测试内容": "B2B智能视频创作",
  "工作流": "main",
  "entry_type": "chat", 
  "验证点": ["脚本生成", "关键词优化", "发布建议"]
}
```

### 3. 视频分析场景
```json
{
  "测试内容": "视频内容爬取和关键词分析",
  "工作流": "video_analysis",
  "entry_type": "chat",
  "验证点": ["数据爬取", "内容分析", "趋势识别"]
}
```

## 配置说明

### 基本配置 (test_config.json)

```json
{
  "test_config": {
    "base_url": "http://localhost:8080",
    "websocket_url": "ws://localhost:8080/hsai/ws", 
    "username": "admin@localhost",
    "password": "admin",
    "timeout": 30,
    "debug": true
  }
}
```

### 测试数据配置

```json
{
  "test_data": {
    "companies": ["阿里巴巴集团", "腾讯控股", "字节跳动"],
    "video_topics": ["人工智能发展趋势", "短视频营销策略"],
    "platforms": ["抖音", "快手", "小红书", "B站"]
  }
}
```

## 测试报告

### 增强版测试报告格式

```json
{
  "test_summary": {
    "timestamp": "2025-01-13T15:30:00",
    "total_tests": 5,
    "passed_tests": 4,
    "failed_tests": 1,
    "success_rate": 80.0,
    "total_duration": 45.67
  },
  "test_details": [
    {
      "test_name": "企业信息收集场景",
      "result": "PASSED",
      "duration": 12.34,
      "message": "测试通过"
    }
  ]
}
```

## 前置条件

### 1. 环境要求
- Python 3.11+ 虚拟环境已配置
- 服务器运行在 http://localhost:8080
- 用户 `admin@localhost` 已存在，密码为 `admin`

### 2. 服务状态要求
- ✅ 工作流编排中心(WOC)已启用
- ✅ n8n工作流服务可用
- ✅ WebSocket连接正常
- ✅ 相关API接口可访问

### 3. 权限要求
- 测试用户需要有工作流执行权限
- 测试用户需要有WOC管理接口访问权限

## 故障排除

### 常见问题

1. **WebSocket连接失败 - timeout参数错误**
   ```
   错误: BaseEventLoop.create_connection() got an unexpected keyword argument 'timeout'
   解决: 项目使用原生WebSocket，websockets.connect()不支持timeout参数
   修复: 移除timeout参数，使用默认连接设置
   ```

2. **WebSocket URL格式错误**
   ```
   正确格式: ws://localhost:8080/hsai/ws/{user_id}?token={token}
   错误格式: ws://localhost:8080/api/v1/ws/hsai/{user_id}
   ```

3. **认证失败**
   ```
   解决: 确认用户名密码正确，用户已存在
   检查: 配置文件中的username和password
   ```

4. **工作流超时**
   ```
   解决: 检查n8n服务状态，增加timeout配置
   检查: WOC工作流编排中心是否正常运行
   ```

5. **Python环境问题**
   ```
   解决: 确保虚拟环境已激活，依赖已安装
   检查: websockets库是否已安装 (pip install websockets)
   ```

### 调试方法

1. **启用详细日志**
   ```json
   {
     "test_config": {
       "debug": true
     }
   }
   ```

2. **查看测试日志**
   ```bash
   # 日志文件: workflow_test_YYYYMMDD_HHMMSS.log
   ```

3. **检查WOC健康状态**
   ```bash
   curl http://localhost:8080/api/v1/woc/health
   ```

## 扩展说明

### 添加新的测试场景

1. 在 `test_config.json` 中添加场景配置
2. 在测试脚本中实现对应的测试方法
3. 更新测试用例列表

### 自定义配置

```bash
# 使用自定义配置文件
python enhanced_workflow_tester.py custom_config.json
```

### 集成到CI/CD

```yaml
# GitHub Actions 示例
- name: 运行工作流测试
  run: |
    cd backend
    python enhanced_workflow_tester.py
```

## 联系支持

如有问题，请查看：
1. 测试日志文件
2. WOC健康检查接口
3. 服务器运行日志
4. n8n工作流状态