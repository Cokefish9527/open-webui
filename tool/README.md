# 工具脚本目录

本目录用于存放具有重复使用价值的脚本工具。

## 脚本列表

### 1. rename_sql_files.py
**功能**: 重命名 SQL 文件，将日期部分移到文件名开头
**用途**: 
- 将 SQL 脚本的命名格式从 "表名+操作+日期.sql" 改为 "日期+表名+操作.sql"
- 便于在脚本库中按日期排序查看和管理
**使用方法**:
```bash
cd backend
python ../tool/rename_sql_files.py
```
**注意事项**:
- 脚本会处理 `backend/sql/schema_updates` 和 `backend/sql/init_scripts` 目录中的所有 SQL 文件
- 只会重命名符合原始命名规则的文件（表名+操作+日期.sql）
- 不符合命名规则的文件会被跳过

### 2. send_test_blueprint_message.py
**功能**: 发送一个完整的蓝图消息到Redis队列
**用途**:
- 测试Redis消息处理流程
- 验证系统能否正确接收、处理和转发Redis队列中的消息
- 调试消息内容，检查消息中的ID和内容是否按预期设置
**使用方法**:
```bash
cd c:\work\open-webui
python tool/send_test_blueprint_message.py
```

### 3. send_quick_test_message.py
**功能**: 发送一个简单的测试消息到Redis队列
**用途**:
- 快速测试消息发送功能
- 支持自定义session_id、user_id和socket_id
- 系统集成测试时验证各组件间的消息传递
**使用方法**:
```bash
cd c:\work\open-webui
python tool/send_quick_test_message.py [session_id] [user_id] [socket_id]
```
**示例**:
```bash
# 使用默认ID发送消息
python tool/send_quick_test_message.py

# 使用自定义ID发送消息
python tool/send_quick_test_message.py my-session-id my-user-id my-socket-id
```

### 4. listen_to_queue.py
**功能**: 监听Redis队列中的消息
**用途**:
- 实时显示接收到的消息内容
- 验证消息是否正确到达队列
- 验证消息中的ID和内容是否正确
**使用方法**:
```bash
cd c:\work\open-webui
python tool/listen_to_queue.py
```

### 5. check_db_structure.py
**功能**: 检查数据库表结构
**用途**:
- 查看SQLite数据库中表的结构信息
- 显示各表的列名、数据类型和约束条件
**使用方法**:
```bash
cd c:\work\open-webui
python tool/check_db_structure.py
```

### 6. test_database_connection.py
**功能**: 测试PostgreSQL数据库连接
**用途**:
- 验证PostgreSQL数据库连接配置是否正确
- 显示数据库版本信息和关键表的记录数
**使用方法**:
```bash
cd c:\work\open-webui
python tool/test_database_connection.py
```

### 7. test_db_simple.py
**功能**: 简单测试PostgreSQL数据库连接
**用途**:
- 快速验证PostgreSQL数据库连接
- 显示连接成功或失败信息
**使用方法**:
```bash
cd c:\work\open-webui
python tool/test_db_simple.py
```

## 新增工具脚本

### 8. check_database.py
**功能**: 检查数据库中的文件夹数据
**用途**:
- 查看数据库中文件夹表的结构信息
- 显示最近创建的文件夹
- 统计根目录和子目录数量
- 检查孤儿文件夹（parent_id指向不存在的父目录）
**使用方法**:
```bash
cd c:\work\open-webui
python tool/check_database.py
```

### 9. debug_database.py
**功能**: 数据库调试工具
**用途**:
- 检查当前工作目录和数据目录
- 验证DATA_DIR环境变量
- 测试数据库URL连接配置
- 验证数据库文件路径和权限
**使用方法**:
```bash
cd c:\work\open-webui
python tool/debug_database.py
```

### 10. clean_folder_data.py
**功能**: 清理所有文件夹数据
**用途**:
- 删除所有HSAI素材文件夹数据
- 创建数据库备份
- 显示清理前后的统计数据
- 可选择性清理相关素材数据
**使用方法**:
```bash
cd c:\work\open-webui
python tool/clean_folder_data.py
```
**注意事项**:
- 此操作不可逆，会删除所有文件夹数据
- 执行前会创建数据库备份

### 11. clean_materials_data.py
**功能**: 清理所有素材数据
**用途**:
- 删除所有HSAI素材数据
- 清理文件操作日志
- 清理素材标签数据
- 显示清理前后的详细统计数据
**使用方法**:
```bash
cd c:\work\open-webui
python tool/clean_materials_data.py
```
**注意事项**:
- 此操作不可逆，会删除所有素材数据
- 执行前会创建数据库备份

### 12. update_missing_columns.py
**功能**: 更新数据库表结构，添加缺失的列
**用途**:
- 自动检测并添加缺失的数据库列
- 支持user表、hsai_projects表和hsai_tasks表
- 验证列是否已成功添加
**使用方法**:
```bash
cd c:\work\open-webui
python tool/update_missing_columns.py
```

### 13. compare_schema.py
**功能**: 比较数据库表结构与模型定义
**用途**:
- 对比数据库实际表结构与代码模型定义
- 显示缺失的字段
- 显示类型不匹配的字段
- 显示数据库中多余的字段
**使用方法**:
```bash
cd c:\work\open-webui
python tool/compare_schema.py
```

### 14. direct_db_test.py
**功能**: 直接测试数据库功能，绕过服务器
**用途**:
- 测试用户、公司、项目和任务的创建
- 验证数据库模型和ORM功能
- 绕过Web服务器直接测试数据库操作
**使用方法**:
```bash
cd c:\work\open-webui
python tool/direct_db_test.py
```

### 15. clean_test_folders.py
**功能**: 快速清理测试文件夹数据
**用途**:
- 仅清理测试和调试相关的文件夹
- 修复空字符串的parent_id问题
- 保留正常的业务数据
**使用方法**:
```bash
cd c:\work\open-webui
python tool/clean_test_folders.py
```

### 16. check_db_structure.py
**功能**: 检查数据库表结构
**用途**:
- 查看用户表、公司表、项目表和任务表的结构信息
- 检查特定字段是否存在（如company_id、project_id等）
- 显示表的列名、数据类型和约束条件
**使用方法**:
```bash
cd c:\work\open-webui
python tool/check_db_structure.py
```

### 17. debug_folder_tree.py
**功能**: 文件夹树构建问题诊断工具
**用途**:
- 诊断文件夹树构建逻辑问题
- 测试文件夹创建和父子关系
- 验证目录树API的正确性
**使用方法**:
```bash
cd c:\work\open-webui
python tool/debug_folder_tree.py
```

### 18. diagnose_folder_issue.py
**功能**: 文件夹创建问题诊断工具
**用途**:
- 检查数据库表结构和现有数据
- 直接测试文件夹创建逻辑
- 验证父子文件夹关系和重复名称处理
**使用方法**:
```bash
cd c:\work\open-webui
python tool/diagnose_folder_issue.py
```

### 19. simple_db_test.py
**功能**: 简单数据库测试工具
**用途**:
- 直接使用SQL查询验证数据库功能
- 测试用户、公司、项目和任务的创建
- 验证数据库表结构和数据一致性
- 自动清理测试数据
**使用方法**:
```bash
cd c:\work\open-webui
python tool/simple_db_test.py
```

### 20. check_db.py
**功能**: 数据库连接和表结构检查工具
**用途**:
- 检查数据库连接状态
- 显示hsai_materials表的结构信息
- 验证数据库是否可访问
**使用方法**:
```bash
cd c:\work\open-webui
python tool/check_db.py
```

### 21. check_environment.py
**功能**: 环境检查工具
**用途**:
- 检查Python版本和路径
- 验证是否在虚拟环境中
- 检查关键包是否安装（FastAPI、Uvicorn、Pydantic）
**使用方法**:
```bash
cd c:\work\open-webui
python tool/check_environment.py
```

### 22. check_tables.py
**功能**: 数据库表检查工具
**用途**:
- 显示数据库中所有表的列表
- 查找与material相关的表
- 显示表结构信息
**使用方法**:
```bash
cd c:\work\open-webui
python tool/check_tables.py
```

### 23. decode_jwt.py
**功能**: JWT令牌解码工具
**用途**:
- 解码JWT令牌内容
- 显示令牌中的用户ID等信息
- 调试认证相关问题
**使用方法**:
```bash
cd c:\work\open-webui
python tool/decode_jwt.py
```

### 24. query_users.py
**功能**: 用户查询工具
**用途**:
- 查询数据库中的所有用户
- 验证特定用户是否存在
- 显示用户ID和邮箱信息
**使用方法**:
```bash
cd c:\work\open-webui
python tool/query_users.py
```

### 25. test_db.py
**功能**: 数据库测试工具
**用途**:
- 测试数据库连接
- 检查hsai_material表是否存在
- 验证表结构
- 测试素材记录创建
**使用方法**:
```bash
cd c:\work\open-webui
python tool/test_db.py
```

### 26. test_websocket_connection.py
**功能**: WebSocket连接测试工具
**用途**:
- 测试WebSocket端点连接
- 验证用户登录和认证
- 发送测试消息并接收响应
- 调试WebSocket通信问题
**使用方法**:
```bash
cd c:\work\open-webui
python tool/test_websocket_connection.py
```

### 27. check_syntax.py
**功能**: 语法检查工具
**用途**:
- 检查Python文件的语法正确性
- 验证代码是否存在语法错误
- 显示语法错误的详细信息（行号、列号等）
**使用方法**:
```bash
cd c:\work\open-webui
python tool/check_syntax.py
```

### 28. complete_task_system_test.py
**功能**: 完整任务系统测试工具
**用途**:
- 模拟项目创建时自动创建主线任务的过程
- 测试用户、公司、项目和任务的完整创建流程
- 验证任务状态更新功能
- 自动清理测试数据
**使用方法**:
```bash
cd c:\work\open-webui
python tool/complete_task_system_test.py
```

### 29. curl_recovery_test.py
**功能**: 回收站功能验证测试工具
**用途**:
- 使用curl命令测试回收站功能
- 验证回收站虚拟目录是否存在
- 测试登录和目录获取接口
**使用方法**:
```bash
cd c:\work\open-webui
python tool/curl_recovery_test.py
```

### 30. debug_move_to_recovery.py
**功能**: 调试移入回收站接口工具
**用途**:
- 调试移入回收站接口的500错误
- 获取素材详情并测试移入回收站功能
- 显示详细的响应信息用于问题排查
**使用方法**:
```bash
cd c:\work\open-webui
python tool/debug_move_to_recovery.py
```

### 31. debug_recovery_state.py
**功能**: 回收站状态调试检查工具
**用途**:
- 检查数据库中素材的实际状态
- 验证回收站API功能
- 调试回收站相关问题
**使用方法**:
```bash
cd c:\work\open-webui
python tool/debug_recovery_state.py
```

### 32. enhanced_workflow_tester.py
**功能**: 增强版工作流场景测试工具
**用途**:
- 支持配置文件的综合工作流测试
- 生成详细的测试报告
- 测试多种工作流场景（企业信息收集、视频创作、视频分析等）
- 支持重试机制和性能监控
**使用方法**:
```bash
cd c:\work\open-webui
python tool/enhanced_workflow_tester.py
```

### 33. fix_websocket_issues.py
**功能**: 工作流测试脚本快速修复工具
**用途**:
- 解决WebSocket连接timeout参数问题
- 修正WebSocket URL格式问题
- 修复配置文件JSON格式问题
- 检查依赖包完整性
**使用方法**:
```bash
cd c:\work\open-webui
python tool/fix_websocket_issues.py
```

### 34. add_correlation_id_column.py
**功能**: 为Redis队列消息表添加correlation_id列
**用途**:
- 修复数据库表结构缺失correlation_id列的问题
- 使数据库表结构与模型定义保持一致
- 解决因列缺失导致的插入错误
**使用方法**:
```bash
cd c:\work\open-webui\backend
python ../tool/add_correlation_id_column.py
```

### 35. verify_redis_queue_structure.py
**功能**: 验证Redis队列消息表结构完整性
**用途**:
- 检查数据库表结构与模型定义是否一致
- 显示表中所有字段信息
- 验证是否存在缺失字段
- 显示表中数据示例
**使用方法**:
```bash
cd c:\work\open-webui\backend
python ../tool/verify_redis_queue_structure.py
```

### 36. add_correlation_id_column_postgres.py
**功能**: 为PostgreSQL数据库中的Redis队列消息表添加correlation_id列
**用途**:
- 修复PostgreSQL数据库表结构缺失correlation_id列的问题
- 使数据库表结构与模型定义保持一致
- 解决因列缺失导致的插入错误
**使用方法**:
```bash
cd c:\work\open-webui
python tool/add_correlation_id_column_postgres.py
```

### 37. fix_redis_queue_table.py
**功能**: 通用Redis队列消息表修复工具
**用途**:
- 自动检测数据库类型（SQLite或PostgreSQL）
- 为Redis队列消息表添加缺失的correlation_id列
- 支持多种数据库环境下的表结构修复
**使用方法**:
```bash
cd c:\work\open-webui
python tool/fix_redis_queue_table.py
```

## 添加新脚本的规范

1. 所有脚本应具有明确的功能描述和使用说明
2. 脚本应具有良好的错误处理机制
3. 脚本应包含必要的注释说明
4. 在本 README.md 中添加脚本的说明信息
5. 创建相应的文档说明文件（如redis_test_scripts.md）