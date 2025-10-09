# 文件夹接口测试脚本使用说明

## 概述

本套测试脚本用于测试文件夹创建和获取接口的完整工作流，包含以下测试步骤：

1. **获取根目录** - 调用获取文件夹接口，获取根级目录列表
2. **查找父目录ID** - 从根目录的子元素中找到第一个目录的ID，如果没有则使用根目录ID
3. **创建子目录** - 在确定的父目录下创建新的子目录
4. **验证创建结果** - 再次调用获取目录接口，确认新目录已成功创建
5. **获取目录详情** - 使用新建目录的ID获取详细信息

## 文件说明

### 主要测试脚本

1. **`test_folder_workflow.py`** - 完整的工作流测试脚本
   - 包含详细的5步测试流程
   - 提供丰富的调试信息和错误处理
   - 支持配置文件
   - 适合深度测试和问题诊断

2. **`simple_folder_test.py`** - 简化的快速测试脚本
   - 基础功能验证
   - 快速执行
   - 适合日常回归测试

3. **`diagnose_folder_issue.py`** - 问题诊断脚本
   - 检查数据库状态
   - 直接测试业务逻辑
   - 适合问题排查

### 配置和启动

4. **`test_config.py`** - 测试配置文件
   - 集中管理测试参数
   - API服务器地址配置
   - 认证TOKEN配置

5. **`run_folder_tests.bat`** - Windows启动脚本
   - 自动检测Python环境
   - 智能激活虚拟环境
   - 提供交互式测试选择

## 使用步骤

### 方法1: 使用批处理脚本（推荐）

1. **运行启动脚本**
   ```cmd
   cd backend
   run_folder_tests.bat
   ```

2. **选择测试类型**
   - 选择 `1` 运行完整工作流测试
   - 选择 `2` 运行简单快速测试
   - 选择 `3` 退出

### 方法2: 直接运行Python脚本

1. **配置认证信息**
   
   编辑 `test_config.py` 文件，选择以下任一方式：
   
   **方式A: 使用用户名密码登录（推荐）**
   ```python
   USE_LOGIN = True
   LOGIN_EMAIL = "your_email@example.com"  # 您的登录邮箱
   LOGIN_PASSWORD = "your_password"         # 您的登录密码
   ```
   
   **方式B: 使用现有TOKEN**
   ```python
   USE_LOGIN = False
   TOKEN = "Bearer your_actual_token_here"  # 您的有效TOKEN
   ```

2. **运行完整测试**
   ```bash
   python test_folder_workflow.py
   ```

3. **运行简单测试**
   ```bash
   python simple_folder_test.py
   ```

## 配置说明

### 必需配置

在 `test_config.py` 中配置以下参数：

```python
# API服务器配置
BASE_URL = "http://localhost:8080"  # 后端服务器地址
API_PREFIX = "/api/v1"              # API路径前缀

# 认证配置 - 选择以下任一种方式：

# 方式1: 使用用户名密码登录（推荐）
USE_LOGIN = True
LOGIN_EMAIL = "your_email@example.com"  # 替换为您的登录邮箱
LOGIN_PASSWORD = "your_password"         # 替换为您的登录密码

# 方式2: 使用现有TOKEN
USE_LOGIN = False
TOKEN = "Bearer your_actual_token_here"  # 替换为您的有效TOKEN
```

### 可选配置

```python
# 测试配置
TEST_TIMEOUT = 30                   # 请求超时时间（秒）
FOLDER_NAME_PREFIX = "test_folder"  # 测试文件夹名称前缀

# 调试配置
DEBUG_MODE = True                   # 是否启用详细调试输出
```

## 测试结果解读

### 成功输出示例

现在测试脚本包含了登录功能，完整的测试流程如下：

```
🚀 开始执行文件夹接口完整工作流测试
=== 步骤0: 用户登录 ===
尝试登录用户: admin@localhost
✅ 登录成功
   用户ID: 496e0f43-8bfa-464a-b333-7738d4b3b76d
   用户名: Admin User
   邮箱: admin@localhost
   角色: admin
   Token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

=== 步骤1: 获取根目录 ===
✅ 成功获取根目录，共2 个根级文件夹
   [1] 个人文件夹 (ID: folder_123) - 子目录: 3个
        └── [1] 图片素材 (ID: folder_456)
        └── [2] 视频素材 (ID: folder_789)
        └── [3] 文档资料 (ID: folder_abc)

=== 步骤2: 查找目标父目录ID ===
✅ 找到第一个子目录: 图片素材 (ID: folder_456)

=== 步骤3: 在父目录 folder_456 下创建子目录 ===
✅ 成功创建子目录: test_folder_1640995200 (ID: folder_new123)

=== 步骤4: 验证目录创建是否成功 ===
✅ 重新获取根目录成功，现有 2 个根级文件夹
📊 目录统计: 总共 7 个文件夹

=== 步骤5: 获取目录详细信息 (ID: folder_new123) ===
✅ 成功获取目录详细信息:
   名称: test_folder_1640995200
   ID: folder_new123
   描述: 测试子目录 - 创建于 2024-01-01 12:00:00
   父目录ID: folder_456
   ✅ label字段与name字段值相同（符合规范）

🎉 文件夹接口测试工作流完成！

📋 测试总结:
   ✅ 成功登录用户: admin@localhost
   ✅ 成功获取根目录信息
   ✅ 成功确定父目录ID: folder_456
   ✅ 成功创建子目录: test_folder_1640995200 (ID: folder_new123)
   ✅ 成功验证目录创建结果
   ✅ 成功获取新建目录详细信息
```

### 错误处理

脚本包含详细的错误处理和提示：

- **认证失败**: `❌ 认证失败，请检查TOKEN配置`
- **连接失败**: `❌ 无法连接到服务器，请确保服务器正在运行`
- **权限错误**: `❌ 创建子目录失败: 400 - Invalid parent folder ID`
- **重复名称**: `❌ 创建子目录失败: 400 - A folder with the same name already exists`

## 故障排除

### 常见问题

1. **TOKEN配置错误**
   - 检查 `test_config.py` 中的TOKEN是否正确
   - 确认TOKEN没有过期

2. **服务器连接失败**
   - 确认后端服务器正在运行
   - 检查BASE_URL配置是否正确
   - 验证网络连接

3. **Python环境问题**
   - 确保安装了requests模块: `pip install requests`
   - 检查Python版本兼容性

4. **权限问题**
   - 确认TOKEN对应的用户有创建文件夹的权限
   - 检查父目录是否属于当前用户

### 调试建议

1. **启用详细调试**
   ```python
   DEBUG_MODE = True
   PRINT_RESPONSE_DETAILS = True
   ```

2. **检查API响应**
   - 观察HTTP状态码
   - 查看详细错误信息
   - 分析响应体内容

3. **使用诊断脚本**
   ```bash
   python diagnose_folder_issue.py
   ```

## 技术规范

脚本严格遵循以下开发规范：

- **文件夹验证规范**: 验证父文件夹存在性和权限
- **同名检查规范**: 防止创建重名文件夹
- **错误信息规范**: 提供详细和用户友好的错误提示
- **Label字段规范**: 确保label字段与name字段值相同
- **事务回滚规范**: 在验证失败时正确回滚事务

## 扩展功能

可以根据需要扩展以下功能：

1. **批量测试**: 创建多个文件夹进行压力测试
2. **清理功能**: 自动删除测试创建的文件夹
3. **性能测试**: 测量API响应时间
4. **并发测试**: 模拟多用户同时操作
5. **边界测试**: 测试极长文件名、特殊字符等边界情况