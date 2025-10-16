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

## 添加新脚本的规范

1. 所有脚本应具有明确的功能描述和使用说明
2. 脚本应具有良好的错误处理机制
3. 脚本应包含必要的注释说明
4. 在本 README.md 中添加脚本的说明信息
5. 创建相应的文档说明文件（如redis_test_scripts.md）