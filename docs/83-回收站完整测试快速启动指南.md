# 🚀 回收站完整测试 - 快速启动指南

## 📖 总览

整合后的测试脚本现在支持完整的回收站测试流程，包括从登录认证到彻底删除的9个步骤。

## ⚡ 快速启动

### 1. 启动脚本
```bash
cd c:\work\open-webui\backend
run_folder_tests.bat
```

### 2. 选择测试类型
```
[3] 回收站完整测试 (完整的9步回收站测试流程) ⭐️ 推荐
```

## 🔧 配置步骤

### 第一次使用前，请配置认证信息：

#### 方式1: 编辑配置文件（推荐）
```bash
# 1. 复制配置模板
copy test_config_template.py test_config.py

# 2. 编辑 test_config.py，填入实际的token或用户名密码
```

#### 方式2: 直接编辑测试脚本
在 `test_recovery_complete_workflow.py` 第57行：
```python
preset_token = "你的实际token"
```

## 🎯 测试流程

选择选项3后，将自动执行以下9步测试：

```
🚀 此测试将执行完整的9步回收站测试流程：
   1. 登录认证 → 2. 获取目录 → 3. 创建目录 → 4. 上传素材 → 5. 移入回收站
   6. 验证在回收站 → 7. 还原素材 → 8. 永久删除 → 9. 验证彻底删除
```

## ✅ 预期结果

测试成功时，你会看到：
```
🎉 所有测试步骤执行成功！
📊 测试结果: 9/9 步骤成功
```

## 🛠️ 故障排除

如果遇到问题：

1. **检查服务器** - 确保后端运行在 http://localhost:8080
2. **检查认证** - 确保token有效或用户名密码正确  
3. **查看日志** - 检查 `recovery_workflow_test.log` 文件
4. **阅读文档** - 查看 `README_RECOVERY_TESTS.md` 详细说明

## 📁 相关文件

- `run_folder_tests.bat` - 主启动脚本
- `test_recovery_complete_workflow.py` - 回收站完整测试
- `test_recovery_fixes.py` - 回收站修复验证  
- `test_config_template.py` - 配置文件模板
- `README_RECOVERY_TESTS.md` - 详细使用说明

---
**开始测试** → 运行 `run_folder_tests.bat` → 选择选项 `[3]` → 等待完成 🎉