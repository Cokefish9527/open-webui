#!/bin/bash

# Open-WebUI 后端服务部署脚本

set -e  # 遇到错误时退出

echo "=== Open-WebUI 后端服务部署脚本 ==="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: 未找到Docker，请先安装Docker"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "错误: 未找到docker-compose，请先安装docker-compose"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR=$(dirname "$SCRIPT_DIR")

echo "项目目录: $PROJECT_DIR"
cd "$PROJECT_DIR"

# 创建数据目录
echo "创建数据目录..."
mkdir -p backend/data
mkdir -p backend/data/uploads
mkdir -p backend/data/cache
mkdir -p backend/data/vector_db

# 构建Docker镜像
echo "构建后端服务Docker镜像..."
docker build -t open-webui-backend -f backend/Dockerfile .

# 检查是否需要重新创建容器
if docker ps -a --format '{{.Names}}' | grep -q 'open-webui-backend'; then
    echo "停止并删除现有容器..."
    docker stop open-webui-backend || true
    docker rm open-webui-backend || true
fi

# 运行容器
echo "启动后端服务容器..."
docker run -d \
  --name open-webui-backend \
  -p 8080:8080 \
  -v "$PROJECT_DIR/backend/data:/app/backend/data" \
  --restart unless-stopped \
  open-webui-backend

echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
if docker ps --format '{{.Names}}' | grep -q 'open-webui-backend'; then
    echo "后端服务已成功启动！"
    echo "服务地址: http://localhost:8080"
    echo "健康检查: http://localhost:8080/health"
    
    # 显示容器日志的前几行
    echo "最近的日志:"
    docker logs open-webui-backend --tail 20
else
    echo "错误: 服务启动失败"
    echo "查看详细日志:"
    docker logs open-webui-backend
    exit 1
fi

echo "=== 部署完成 ==="