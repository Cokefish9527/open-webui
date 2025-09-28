# Open-WebUI 后端服务 Docker 镜像

这个目录包含了用于构建Open-WebUI后端服务Docker镜像的文件。

## 目录结构

```
backend/
├── Dockerfile              # 后端服务Docker镜像构建文件
├── requirements.txt        # Python依赖包列表
├── start.sh                # 启动脚本
├── deploy.sh               # 部署脚本
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

### 使用部署脚本运行（Linux/macOS）

```bash
# 设置脚本执行权限（Linux/macOS）
chmod +x backend/deploy.sh

# 运行部署脚本
./backend/deploy.sh
```

在Windows环境下，可以使用PowerShell执行脚本：
```powershell
# Windows环境下执行脚本
powershell -ExecutionPolicy Bypass -File backend\deploy.sh
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