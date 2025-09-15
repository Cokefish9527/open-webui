# Redis配置说明

本文档说明了项目中Redis配置的设置和使用方式。

## 配置项说明

### REDIS_URL
- **用途**: 用于常规Redis连接
- **格式**: `redis://<host>:<port>/<database>`
- **示例**: `redis://192.168.20.31:6379/0`

### WEBSOCKET_REDIS_URL
- **用途**: 专门用于WebSocket的Redis连接
- **格式**: `redis://<host>:<port>/<database>`
- **示例**: `redis://192.168.20.31:6379/0`

## 配置文件位置

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

## 配置使用方式

项目遵循OpenWebUI的标准做法进行配置管理：

1. 优先从环境变量读取配置
2. 如果环境变量未设置，则使用默认值
3. Redis连接支持Sentinel模式和普通模式
4. WebSocket和常规Redis连接可以使用不同的URL

## 当前配置详情

根据测试结果，Redis服务器部署在:
- **IP地址**: 192.168.20.31
- **端口**: 6379
- **密码**: 无（服务器未配置密码）
- **数据库**: 0

对应的配置为:
```
REDIS_URL=redis://192.168.20.31:6379/0
WEBSOCKET_REDIS_URL=redis://192.168.20.31:6379/0
```

## 注意事项

1. 确保Redis服务器在网络中可访问
2. 确保密码正确
3. 如果需要使用Redis Sentinel，请同时配置`REDIS_SENTINEL_HOSTS`和`REDIS_SENTINEL_PORT`环境变量
4. 在生产环境中，建议使用不同的Redis实例分别处理WebSocket和常规数据存储，以提高系统稳定性