# 扩展更新日志

## 2025-09-29

### 新增功能
- 在用户模型中添加了 `business_name` 字段，用于存储用户所属的公司名称
- 创建了数据库迁移脚本 `019_add_user_business_name.py` 用于添加字段
- 添加了 `update_user_business_name_by_id` 方法用于更新用户公司名称
- 创建了 `/users/user/business_name/update` API 端点用于更新当前用户的公司名称
- 在 WebSocket 事件处理器中实现了从用户实体获取 `business_name` 的逻辑
- 在视频学习路由中实现了从用户实体获取 `business_name` 的逻辑

### 技术实现
- 数据库字段: `business_name` (TEXT, NULLABLE)
- 用户模型字段: `business_name` (Optional[str])
- 默认值: 新用户默认为 None，系统中使用 "HSAI" 作为默认值
- 兼容性: 保留了从 `info` 字段获取 `business_name` 的向后兼容逻辑

### 文件变更
1. `backend/open_webui/models/users.py` - 添加字段定义和相关方法
2. `backend/open_webui/internal/migrations/019_add_user_business_name.py` - 数据库迁移脚本
3. `backend/open_webui/socket/hsai_events.py` - 更新WebSocket事件处理逻辑
4. `backend/open_webui/routers/hsai_video_learning.py` - 更新视频学习路由逻辑
5. `backend/open_webui/routers/users.py` - 添加更新business_name的API端点
6. `src/lib/apis/users/index.ts` - 添加前端API调用方法
7. `sql/add_user_business_name_column.sql` - 手动SQL更新脚本

### 使用说明
1. 运行数据库迁移以添加 `business_name` 字段
2. 通过 API 端点 `/users/user/business_name/update` 更新用户公司名称
3. 系统将自动在 WebSocket 通信和视频学习功能中使用用户的 `business_name`