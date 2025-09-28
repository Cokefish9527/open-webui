#!/bin/bash

# Open-WebUI 后端服务开发环境脚本
# 支持热更新功能

set -e  # 遇到错误时退出

echo "=== Open-WebUI 后端服务开发环境 ==="

# 获取脚本所在目录
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# 获取项目根目录（git仓库根目录）
PROJECT_DIR=$(dirname "$(dirname "$SCRIPT_DIR")")

echo "项目根目录: $PROJECT_DIR"
cd "$PROJECT_DIR"

# 检查是否为git仓库
if [ ! -d ".git" ]; then
    echo "错误: 当前目录不是git仓库根目录"
    echo "请确保在open-webui项目根目录下运行此脚本"
    exit 1
fi

# 拉取最新代码
echo "拉取最新代码..."
git pull origin main

# 切换回backend目录
cd "$SCRIPT_DIR"

# 检查是否已经运行着开发容器
if docker ps --format '{{.Names}}' | grep -q 'open-webui-backend-dev'; then
    echo "发现正在运行的开发容器，停止并删除..."
    docker stop open-webui-backend-dev
    docker rm open-webui-backend-dev
fi

# 启动开发环境容器（带热更新）
echo "启动开发环境容器..."
docker run -d \
  --name open-webui-backend-dev \
  -p 8080:8080 \
  -v "$SCRIPT_DIR:/app/backend" \
  -e PORT=8080 \
  -e HOST=0.0.0.0 \
  open-webui-backend:latest \
  python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --reload --reload-dir /app/backend

echo "开发环境已启动！"
echo "服务地址: http://localhost:8080"
echo "代码更改将自动触发重启"
echo "按 Ctrl+C 停止服务"

# 显示实时日志
docker logs -f open-webui-backend-dev