#!/bin/bash

# Open-WebUI 后端服务增量更新脚本
# 只更新代码，不重新安装依赖

set -e  # 遇到错误时退出

echo "=== Open-WebUI 后端服务增量更新脚本 ==="

# 获取脚本所在目录（兼容更多shell环境）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录（git仓库根目录）
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "项目根目录: $PROJECT_DIR"
cd "$PROJECT_DIR"

# 检查是否为git仓库
if [ ! -d ".git" ]; then
    echo "错误: 当前目录不是git仓库根目录"
    echo "请确保在open-webui项目根目录下运行此脚本"
    echo "当前目录: $(pwd)"
    echo "脚本目录: $SCRIPT_DIR"
    exit 1
fi

# 拉取最新代码
echo "拉取最新代码..."
git pull origin main

# 切换回backend目录进行构建
cd "$SCRIPT_DIR"

# 构建新的镜像（利用Docker缓存）
echo "构建新镜像（利用缓存）..."
docker build -t open-webui-backend:new -f Dockerfile .

# 停止并删除旧容器
echo "停止并删除旧容器..."
docker stop open-webui-backend || true
docker rm open-webui-backend || true

# 删除旧镜像标签
docker rmi open-webui-backend:latest || true

# 为新镜像打标签
docker tag open-webui-backend:new open-webui-backend:latest

# 删除临时标签
docker rmi open-webui-backend:new

# 启动新容器
echo "启动新容器..."
docker run -d \
  --name open-webui-backend \
  -p 8080:8080 \
  -v "$SCRIPT_DIR/data:/app/backend/data" \
  --restart unless-stopped \
  open-webui-backend:latest

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
if docker ps --format '{{.Names}}' | grep -q 'open-webui-backend'; then
    echo "后端服务已成功更新并启动！"
    echo "服务地址: http://localhost:8080"
    echo "健康检查: http://localhost:8080/health"
else
    echo "错误: 服务启动失败"
    echo "查看详细日志:"
    docker logs open-webui-backend
    exit 1
fi

echo "=== 增量更新完成 ==="