#!/bin/bash

# Open-WebUI 后端服务更新脚本

set -e  # 遇到错误时退出

echo "=== Open-WebUI 后端服务更新脚本 ==="

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

# 切换回backend目录
cd "$SCRIPT_DIR"

# 停止当前服务
echo "停止当前服务..."
docker-compose -f docker-compose.backend.yaml down

# 重新构建镜像
echo "重新构建镜像..."
docker-compose -f docker-compose.backend.yaml build --no-cache

# 启动服务
echo "启动服务..."
docker-compose -f docker-compose.backend.yaml up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
if docker-compose -f docker-compose.backend.yaml ps | grep -q "Up"; then
    echo "后端服务已成功更新并启动！"
    echo "服务地址: http://localhost:8080"
    echo "健康检查: http://localhost:8080/health"
else
    echo "错误: 服务启动失败"
    echo "查看详细日志:"
    docker-compose -f docker-compose.backend.yaml logs
    exit 1
fi

echo "=== 更新完成 ==="