# 使用Python 3.11作为基础镜像
FROM python:3.11-slim-bookworm

# 设置环境变量
ENV ENV=prod \
    PORT=8080 \
    HOST=0.0.0.0 \
    PYTHONPATH=/app/backend \
    SKIP_MIGRATIONS=true

# 设置工作目录
WORKDIR /app/backend

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential \
    pandoc \
    netcat-openbsd \
    curl \
    jq \
    gcc \
    python3-dev \
    ffmpeg \
    libsm6 \
    libxext6 && \
    rm -rf /var/lib/apt/lists/*

# 复制requirements文件（这一步在代码更改时通常不会变化）
COPY ./requirements.txt ./requirements.txt

# 安装uv包管理器并使用它来安装依赖
# 这一步只有在requirements.txt变化时才会重新执行
RUN pip install --no-cache-dir uv && \
    uv pip install --system -r requirements.txt --no-cache-dir

# 复制后端代码（这一步在代码更改时会变化，但不会影响之前的依赖层）
COPY . .

# 创建必要的目录
RUN mkdir -p data/uploads data/cache data/vector_db

# 设置端口
EXPOSE 8080

# 健康检查
HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

# 使用修改后的启动方式，跳过迁移检查
CMD ["python", "-m", "uvicorn", "open_webui.main:app", "--host", "0.0.0.0", "--port", "8080", "--forwarded-allow-ips", "*", "--workers", "1"]