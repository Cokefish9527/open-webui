#!/usr/bin/env bash

# Open-WebUI Backend 启动脚本 (Linux版本)
# 仅启动后端服务，不包含前端和Ollama服务

echo "=== Open-WebUI 后端服务启动脚本 (Linux) ==="
echo

# 获取脚本所在目录
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "切换到脚本目录: $SCRIPT_DIR"
cd "$SCRIPT_DIR" || exit

# 设置环境变量
echo "配置环境变量..."
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"
export DATA_DIR="${SCRIPT_DIR}/data"

# 确保数据目录存在
echo "确保数据目录存在..."
mkdir -p "${DATA_DIR}"
mkdir -p "${DATA_DIR}/uploads"
mkdir -p "${DATA_DIR}/cache"
mkdir -p "${DATA_DIR}/vector_db"

# 设置默认端口和主机
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

echo "PYTHONPATH: ${PYTHONPATH}"
echo "DATA_DIR: ${DATA_DIR}"
echo "HOST: ${HOST}"
echo "PORT: ${PORT}"
echo

# 检查Python环境
echo "检查Python环境..."
PYTHON_CMD=$(command -v python3 || command -v python)

if [ -z "$PYTHON_CMD" ]; then
    echo "错误: 未找到Python命令"
    exit 1
fi

echo "使用Python: $PYTHON_CMD"
$PYTHON_CMD --version
echo

# 检查必要的依赖
echo "检查必要的依赖..."
if ! $PYTHON_CMD -c "import uvicorn" &> /dev/null; then
    echo "错误: 未找到uvicorn，请安装依赖"
    echo "运行: pip install -r requirements.txt"
    exit 1
fi

# 生成密钥文件（如果不存在）
KEY_FILE=".webui_secret_key"
if [ ! -e "$KEY_FILE" ]; then
    echo "生成WEBUI_SECRET_KEY"
    # 生成随机值作为WEBUI_SECRET_KEY
    echo $(head -c 12 /dev/random | base64) > "$KEY_FILE"
fi

WEBUI_SECRET_KEY=$(cat "$KEY_FILE")
export WEBUI_SECRET_KEY

echo "加载WEBUI_SECRET_KEY从 $KEY_FILE"
echo

# 启动服务
echo "=== 启动后端服务 ==="
echo "服务将在 http://$HOST:$PORT 上运行"
echo "按 Ctrl+C 停止服务"
echo

# 启动uvicorn服务器
exec "$PYTHON_CMD" -m uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' --workers 1