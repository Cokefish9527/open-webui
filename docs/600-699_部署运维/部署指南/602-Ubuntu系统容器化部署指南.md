# 在Ubuntu系统上容器化运行Open-WebUI项目

## 1. 环境准备

首先在Ubuntu系统上安装必要的工具：

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装Docker
sudo apt install docker.io -y

# 启动并启用Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到docker组（避免每次使用sudo）
sudo usermod -aG docker $USER

# 安装docker-compose
sudo apt install docker-compose -y

# 验证安装
docker --version
docker-compose --version
```

安装完成后，建议注销并重新登录以使用户组更改生效。

## 2. 获取项目代码

```bash
# 克隆项目代码（假设您已将代码推送到Git仓库）
git clone <your-repository-url>
cd open-webui
```

## 3. 配置环境变量

```bash
# 复制示例环境配置文件
cp .env.example .env

# 编辑环境变量配置（根据需要调整）
nano .env
```

主要需要配置的选项包括：
- OLLAMA_BASE_URL: Ollama服务的URL
- WEBUI_SECRET_KEY: WebUI的密钥（可自动生成）
- 其他根据需要配置的选项

## 4. 构建和运行容器

项目提供了多种运行方式：

### 基本运行（推荐）

```bash
# 使用run-compose.sh脚本运行（最简单方式）
./run-compose.sh
```

### 自定义配置运行

```bash
# 启用GPU支持（如果系统有GPU）
./run-compose.sh --enable-gpu[count=1]

# 指定WebUI端口
./run-compose.sh --webui[port=3000]

# 启用API端口
./run-compose.sh --enable-api[port=11434]

# 组合多个选项
./run-compose.sh --enable-gpu[count=1] --webui[port=3000] --enable-api[port=11434]
```

### 手动使用docker-compose运行

```bash
# 基本运行
docker-compose up -d

# 启用GPU支持（需要先安装NVIDIA Container Toolkit）
docker-compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d

# 启用外部API访问
docker-compose -f docker-compose.yaml -f docker-compose.api.yaml up -d

# 组合多个配置文件
docker-compose -f docker-compose.yaml -f docker-compose.gpu.yaml -f docker-compose.api.yaml up -d
```

### 仅运行后端服务

如果您只需要运行后端服务（不使用Docker容器），可以使用以下方法：

```bash
# 进入后端目录
cd backend

# 确保start_linux.sh脚本具有执行权限
chmod +x start_linux.sh

# 运行后端服务
./start_linux.sh
```

这将仅启动后端服务，监听8080端口，不包含前端和Ollama服务。

### 构建和运行后端Docker镜像

如果您希望将后端服务容器化部署到生产环境，可以使用以下方法：

```bash
# 构建后端Docker镜像
docker build -t open-webui-backend -f backend/Dockerfile .

# 或者使用docker-compose构建和运行
docker-compose -f docker-compose.backend.yaml up -d

# 查看运行状态
docker ps

# 查看日志
docker logs open-webui-backend
```

## 5. 验证服务运行状态

```bash
# 查看运行中的容器
docker ps

# 查看容器日志
docker logs open-webui
docker logs ollama

# 检查服务健康状态
curl http://localhost:3000/health

# 检查后端服务健康状态（仅后端运行时）
curl http://localhost:8080/health
```

## 6. 访问Web界面

服务启动后，可以通过以下URL访问Web界面：
- **WebUI地址**: http://localhost:3000
- **Ollama API地址**: http://localhost:11434（如果启用了API）
- **后端API地址**: http://localhost:8080（仅后端运行时）

## 7. 常见问题处理

### 如果遇到权限问题：

```bash
# 确保当前用户在docker组中
sudo usermod -aG docker $USER
# 然后注销并重新登录
```

### 如果需要重新构建镜像：

```bash
# 使用run-compose.sh脚本
./run-compose.sh --build

# 或者手动构建
docker-compose build

# 或者仅构建后端镜像
docker build -t open-webui-backend -f backend/Dockerfile .
```

### 停止和清理服务：

```bash
# 使用run-compose.sh脚本
./run-compose.sh --drop

# 或者手动停止
docker-compose down

# 或者停止后端服务
docker-compose -f docker-compose.backend.yaml down
```

## 8. 高级配置

### GPU支持配置

如果您的Ubuntu系统配备了NVIDIA GPU：

```bash
# 安装NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install nvidia-container-toolkit -y
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 数据持久化

默认情况下，项目使用Docker卷来持久化数据。如果需要将数据存储在特定目录：

```bash
./run-compose.sh --data[folder=./ollama-data]
```