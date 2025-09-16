# Redis配置与切换指南

本文档详细说明了项目中Redis配置的设置、使用方式以及如何在内网Redis和公网Redis之间切换配置。

## 1. 配置项说明

### 1.1 REDIS_MODE
- **用途**: 控制使用内网还是公网Redis
- **可选值**: 
  - `internal` (默认) - 使用内网Redis
  - `external` - 使用公网Redis
- **示例**: `REDIS_MODE=internal`

### 1.2 内网Redis配置
- **INTERNAL_REDIS_URL**: 内网Redis连接URL
- **INTERNAL_WEBSOCKET_REDIS_URL**: 内网WebSocket Redis连接URL

### 1.3 公网Redis配置
- **EXTERNAL_REDIS_HOST**: 公网Redis主机地址
- **EXTERNAL_REDIS_PORT**: 公网Redis端口
- **EXTERNAL_REDIS_DB**: 公网Redis数据库编号
- **EXTERNAL_REDIS_USERNAME**: 公网Redis用户名
- **EXTERNAL_REDIS_PASSWORD**: 公网Redis密码
- **EXTERNAL_WEBSOCKET_REDIS_HOST**: 公网WebSocket Redis主机地址
- **EXTERNAL_WEBSOCKET_REDIS_PORT**: 公网WebSocket Redis端口
- **EXTERNAL_WEBSOCKET_REDIS_DB**: 公网WebSocket Redis数据库编号
- **EXTERNAL_WEBSOCKET_REDIS_USERNAME**: 公网WebSocket Redis用户名
- **EXTERNAL_WEBSOCKET_REDIS_PASSWORD**: 公网WebSocket Redis密码

## 2. 配置文件位置

1. **环境变量文件**: [.env](file:///c:/work/open-webui/.env)
   - 这是主要的配置文件，所有环境变量都在这里设置
   - 项目启动时会自动加载此文件中的配置

2. **环境配置模块**: [backend/open_webui/env.py](file:///c:/work/open-webui/backend/open_webui/env.py)
   - 定义了Redis相关的环境变量和默认值
   - 从环境变量中读取配置，如果没有设置则使用默认值

3. **主应用文件**: [backend/open_webui/main.py](file:///c:/work/open-webui/backend/open_webui/main.py)
   - 使用Redis配置初始化Redis连接
   - 创建Redis连接池用于应用的各种功能

4. **WebSocket模块**: [backend/open_webui/socket/main.py](file:///c:/work/open-webui/backend/open_webui/socket/main.py)
   - 使用Redis配置初始化WebSocket管理器
   - 支持WebSocket的分布式部署

5. **Redis信号处理器**: [backend/open_webui/utils/redis_signal_handler.py](file:///c:/work/open-webui/backend/open_webui/utils/redis_signal_handler.py)
   - 使用Redis配置处理n8n工作流的实时状态更新
   - 监听Redis中的信号变化并转发给前端

## 3. 配置使用方式

项目遵循OpenWebUI的标准做法进行配置管理：

1. 优先从环境变量读取配置
2. 如果环境变量未设置，则使用默认值
3. Redis连接支持Sentinel模式和普通模式
4. WebSocket和常规Redis连接可以使用不同的URL

## 4. 切换内网/公网Redis配置

### 4.1 使用内网Redis (默认)
```
REDIS_MODE=internal
INTERNAL_REDIS_URL=redis://192.168.20.31:6379/0
INTERNAL_WEBSOCKET_REDIS_URL=redis://192.168.20.31:6379/0
```

### 4.2 使用公网Redis
```
REDIS_MODE=external
EXTERNAL_REDIS_HOST=r-bp16h5hix81xr15svxpd.redis.rds.aliyuncs.com
EXTERNAL_REDIS_PORT=6379
EXTERNAL_REDIS_DB=7
EXTERNAL_REDIS_USERNAME=r-bp16h5hix81xr15svx
EXTERNAL_REDIS_PASSWORD=hdtFOXRwdFA1EZzaypqv7PE6j1XuVT
EXTERNAL_WEBSOCKET_REDIS_HOST=r-bp16h5hix81xr15svxpd.redis.rds.aliyuncs.com
EXTERNAL_WEBSOCKET_REDIS_PORT=6379
EXTERNAL_WEBSOCKET_REDIS_DB=7
EXTERNAL_WEBSOCKET_REDIS_USERNAME=r-bp16h5hix81xr15svx
EXTERNAL_WEBSOCKET_REDIS_PASSWORD=hdtFOXRwdFA1EZzaypqv7PE6j1XuVT
```

### 4.3 切换步骤

#### 4.3.1 切换到公网Redis
1. 打开 [.env](file:///c:/work/open-webui/.env) 文件
2. 修改 `REDIS_MODE=external`
3. 确保公网Redis配置已正确填写
4. 重启应用服务

#### 4.3.2 切换到内网Redis
1. 打开 [.env](file:///c:/work/open-webui/.env) 文件
2. 修改 `REDIS_MODE=internal`
3. 确保内网Redis配置已正确填写
4. 重启应用服务

## 5. 验证配置

### 5.1 使用测试脚本验证
```bash
# 验证当前配置
cd c:\work\open-webui
python test/env_logic_test.py
```

### 5.2 临时切换模式测试
```bash
# 临时切换到公网模式测试
cd c:\work\open-webui
$env:REDIS_MODE="external"
python test/env_logic_test.py
```

## 6. 当前配置详情

根据测试结果，Redis服务器部署在:
- **内网IP地址**: 192.168.20.31
- **公网地址**: r-bp16h5hix81xr15svxpd.redis.rds.aliyuncs.com
- **端口**: 6379
- **密码**: 无（内网服务器未配置密码）
- **数据库**: 0 (内网), 7 (公网)

对应的配置为:
```
# 内网配置
INTERNAL_REDIS_URL=redis://192.168.20.31:6379/0
INTERNAL_WEBSOCKET_REDIS_URL=redis://192.168.20.31:6379/0

# 公网配置
EXTERNAL_REDIS_HOST=r-bp16h5hix81xr15svxpd.redis.rds.aliyuncs.com
EXTERNAL_REDIS_PORT=6379
EXTERNAL_REDIS_DB=7
EXTERNAL_REDIS_USERNAME=r-bp16h5hix81xr15svx
EXTERNAL_REDIS_PASSWORD=hdtFOXRwdFA1EZzaypqv7PE6j1XuVT
EXTERNAL_WEBSOCKET_REDIS_HOST=r-bp16h5hix81xr15svxpd.redis.rds.aliyuncs.com
EXTERNAL_WEBSOCKET_REDIS_PORT=6379
EXTERNAL_WEBSOCKET_REDIS_DB=7
EXTERNAL_WEBSOCKET_REDIS_USERNAME=r-bp16h5hix81xr15svx
EXTERNAL_WEBSOCKET_REDIS_PASSWORD=hdtFOXRwdFA1EZzaypqv7PE6j1XuVT
```

## 7. 注意事项

1. **重启服务**：切换配置后必须重启应用服务才能生效
2. **网络连通性**：确保目标Redis服务器在网络中可访问
3. **凭据正确性**：确保用户名和密码正确无误
4. **防火墙设置**：公网Redis可能需要配置安全组规则允许访问
5. **性能考虑**：公网Redis访问延迟可能比内网Redis高
6. 确保密码正确
7. 如果需要使用Redis Sentinel，请同时配置`REDIS_SENTINEL_HOSTS`和`REDIS_SENTINEL_PORT`环境变量
8. 在生产环境中，建议使用不同的Redis实例分别处理WebSocket和常规数据存储，以提高系统稳定性

## 8. 故障排除

### 8.1 连接失败
- 检查网络连通性
- 验证Redis服务器地址和端口
- 确认用户名和密码正确
- 检查防火墙和安全组设置

### 8.2 配置不生效
- 确认已重启应用服务
- 检查环境变量是否正确设置
- 验证 [.env](file:///c:/work/open-webui/.env) 文件格式是否正确

### 8.3 性能问题
- 公网Redis访问可能有延迟，考虑使用内网Redis
- 检查网络带宽和延迟
- 考虑使用Redis连接池优化