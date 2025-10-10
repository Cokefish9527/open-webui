# Open-WebUI 后端服务 Docker 镜像

这个目录包含了用于构建Open-WebUI后端服务Docker镜像的文件。

## 目录结构

```
backend/
├── Dockerfile              # 后端服务Docker镜像构建文件
├── Dockerfile.optimized    # 优化版Dockerfile（多阶段构建）
├── requirements.txt        # Python依赖包列表
├── start.sh                # 启动脚本
├── start-docker.sh         # Docker专用启动脚本
├── deploy.sh               # 部署脚本
├── update.sh               # 完整更新脚本
├── incremental-update.sh   # 增量更新脚本
├── dev-docker.sh           # 开发环境热更新脚本
└── open_webui/             # 后端服务源代码
```

## 构建Docker镜像

要构建后端服务的Docker镜像，请在项目根目录执行以下命令：

```bash
# 构建镜像
docker build -t open-webui-backend -f backend/Dockerfile .

# 或者使用docker-compose构建
docker-compose -f docker-compose.backend.yaml build
```

## 运行Docker容器

### 使用Docker命令运行

```bash
# 运行容器
docker run -d \
  --name open-webui-backend \
  -p 8080:8080 \
  -v ./backend/data:/app/backend/data \
  open-webui-backend

# 查看运行状态
docker ps

# 查看日志
docker logs open-webui-backend
```

### 使用Docker Compose运行

```bash
# 启动服务
docker-compose -f docker-compose.backend.yaml up -d

# 查看运行状态
docker-compose -f docker-compose.backend.yaml ps

# 查看日志
docker-compose -f docker-compose.backend.yaml logs
```

### 使用部署脚本运行

```bash
# 设置脚本执行权限
chmod +x backend/deploy.sh

# 运行部署脚本（需要在项目根目录执行）
./backend/deploy.sh
```

注意：请使用`./backend/deploy.sh`而不是`sh ./backend/deploy.sh`来执行脚本，因为脚本使用了bash特定的语法。

## 更新Docker镜像

当代码更新后，您需要更新Docker镜像以包含最新的代码更改：

### 完整更新流程（重新安装依赖）

```bash
# 在项目根目录执行完整更新脚本
chmod +x backend/update.sh
./backend/update.sh
```

### 增量更新流程（仅更新代码，利用缓存）

```bash
# 使用增量更新脚本（推荐用于频繁代码更新）
chmod +x backend/incremental-update.sh
./backend/incremental-update.sh
```

### 开发环境热更新

```bash
# 使用开发环境脚本（支持代码更改自动重启）
chmod +x backend/dev-docker.sh
./backend/dev-docker.sh
```

## 优化构建性能

### Docker缓存机制

Dockerfile已优化以充分利用层缓存：
1. 依赖安装步骤在代码复制之前
2. 只有当requirements.txt变化时才会重新安装依赖
3. 代码更改不会影响依赖层缓存

### 多阶段构建

使用`Dockerfile.optimized`可以获得更小的镜像体积：
```bash
docker build -t open-webui-backend -f backend/Dockerfile.optimized .
```

### .dockerignore优化

通过.dockerignore文件排除不必要的文件，减少构建上下文大小。

## 脚本使用说明

所有脚本都需要在项目根目录（open-webui目录）下执行，因为：
1. Git仓库根目录在项目根目录
2. 脚本会自动处理目录切换

### 脚本目录处理
所有脚本都已更新以正确处理目录结构：
- 自动检测项目根目录（git仓库根目录）
- 在正确的位置执行git操作
- 切换回backend目录进行Docker操作

### 执行方式
请使用以下方式执行脚本：
```bash
# 正确的执行方式
chmod +x backend/script-name.sh
./backend/script-name.sh

# 错误的执行方式（会导致Bad substitution错误）
sh backend/script-name.sh
```

## 环境变量

后端服务支持以下环境变量：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PORT` | `8080` | 服务监听端口 |
| `HOST` | `0.0.0.0` | 服务绑定地址 |
| `WEBUI_SECRET_KEY` | 自动生成 | WebUI密钥 |
| `DATABASE_URL` | `sqlite:///./data/webui.db` | 数据库连接URL |

## 数据持久化

容器内的以下目录应该挂载到宿主机以实现数据持久化：

- `/app/backend/data`: 包含数据库文件、上传文件、缓存等

## 健康检查

镜像包含健康检查，通过访问 `/health` 端点来检查服务状态。

## 生产环境部署建议

1. **使用外部数据库**：在生产环境中，建议使用PostgreSQL或MySQL等外部数据库而不是SQLite。

2. **配置环境变量**：根据生产环境需求设置适当的环境变量。

3. **数据备份**：定期备份挂载的数据卷。

4. **安全配置**：
   - 设置强密钥
   - 配置适当的网络访问控制
   - 使用HTTPS

5. **资源限制**：根据服务器性能设置适当的内存和CPU限制。

6. **版本管理**：使用标签管理镜像版本，便于回滚和部署。

## 故障排除

### 查看日志

```bash
# 查看容器日志
docker logs open-webui-backend

# 实时查看日志
docker logs -f open-webui-backend
```

### 进入容器调试

```bash
# 进入运行中的容器
docker exec -it open-webui-backend /bin/bash
```

### 重新构建镜像

如果遇到问题，可以尝试清理并重新构建镜像：

```bash
# 删除现有镜像
docker rmi open-webui-backend

# 清理构建缓存
docker builder prune

# 重新构建
docker build -t open-webui-backend -f backend/Dockerfile .
```