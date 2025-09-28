#!/bin/bash

# 简化版Docker启动脚本

# 设置默认环境变量
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

# 创建数据目录
mkdir -p data/uploads data/cache data/vector_db

# 生成密钥文件（如果不存在）
KEY_FILE=".webui_secret_key"
if [ ! -e "$KEY_FILE" ]; then
    echo "Generating WEBUI_SECRET_KEY"
    echo $(head -c 12 /dev/random | base64) > "$KEY_FILE"
fi

# 读取密钥
WEBUI_SECRET_KEY=$(cat "$KEY_FILE")

# 启动服务
echo "Starting Open-WebUI backend on $HOST:$PORT"
exec python -m uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' --workers 1