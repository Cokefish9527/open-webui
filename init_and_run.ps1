# Open-WebUI 初始化和运行脚本 (PowerShell)
# 该脚本将自动完成虚拟环境创建、依赖安装和服务器启动

Write-Host "=== Open-WebUI 初始化和运行脚本 ===" -ForegroundColor Green

# 检查 Python 版本
Write-Host "检查 Python 版本..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 未找到 Python。请先安装 Python 3.11。" -ForegroundColor Red
    exit 1
}

Write-Host "找到 Python 版本: $pythonVersion" -ForegroundColor Green

# 检查是否已存在虚拟环境
if (Test-Path ".\venv") {
    Write-Host "虚拟环境已存在，跳过创建..." -ForegroundColor Yellow
} else {
    Write-Host "创建虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: 虚拟环境创建失败。" -ForegroundColor Red
        exit 1
    }
    Write-Host "虚拟环境创建成功!" -ForegroundColor Green
}

# 激活虚拟环境
Write-Host "激活虚拟环境..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 虚拟环境激活失败。" -ForegroundColor Red
    exit 1
}
Write-Host "虚拟环境已激活!" -ForegroundColor Green

# 升级 pip
Write-Host "升级 pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: pip 升级失败。" -ForegroundColor Red
    exit 1
}
Write-Host "pip 升级成功!" -ForegroundColor Green

# 安装依赖
Write-Host "安装项目依赖..." -ForegroundColor Yellow
Set-Location backend
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 依赖安装失败。" -ForegroundColor Red
    exit 1
}
Write-Host "依赖安装成功!" -ForegroundColor Green

# 检查是否需要安装 Playwright 浏览器
if ($env:WEB_LOADER_ENGINE -eq "playwright") {
    if (-not $env:PLAYWRIGHT_WS_URL) {
        Write-Host "安装 Playwright 浏览器..." -ForegroundColor Yellow
        playwright install chromium
        playwright install-deps chromium
        Write-Host "Playwright 浏览器安装完成!" -ForegroundColor Green
    }
    
    # 下载 NLTK 数据
    Write-Host "下载 NLTK 数据..." -ForegroundColor Yellow
    python -c "import nltk; nltk.download('punkt_tab')"
    Write-Host "NLTK 数据下载完成!" -ForegroundColor Green
}

# 生成或加载密钥文件
$KEY_FILE = ".webui_secret_key"
if (-not $env:WEBUI_SECRET_KEY -and -not $env:WEBUI_JWT_SECRET_KEY) {
    Write-Host "检查密钥文件..." -ForegroundColor Yellow
    if (-not (Test-Path $KEY_FILE)) {
        Write-Host "生成 WEBUI_SECRET_KEY..." -ForegroundColor Yellow
        $randomKey = -join ((65..90) + (97..122) | Get-Random -Count 12 | % {[char]$_})
        $randomKey | Out-File -FilePath $KEY_FILE -Encoding ASCII
        Write-Host "密钥文件生成成功!" -ForegroundColor Green
    } else {
        Write-Host "密钥文件已存在，跳过生成。" -ForegroundColor Yellow
    }
}

# 创建必要的目录
Write-Host "创建必要的数据目录..." -ForegroundColor Yellow
if (-not (Test-Path ".\data")) {
    New-Item -ItemType Directory -Name "data" | Out-Null
}
if (-not (Test-Path ".\data\cache")) {
    New-Item -ItemType Directory -Path ".\data\cache" | Out-Null
}
if (-not (Test-Path ".\data\cache\whisper")) {
    New-Item -ItemType Directory -Path ".\data\cache\whisper" | Out-Null
}
if (-not (Test-Path ".\data\cache\embedding")) {
    New-Item -ItemType Directory -Path ".\data\cache\embedding" | Out-Null
}

Write-Host "数据目录创建完成!" -ForegroundColor Green

# 设置默认环境变量
$env:PORT = "8080"
$env:HOST = "0.0.0.0"

# 启动服务
Write-Host "启动 Open-WebUI 服务..." -ForegroundColor Yellow
Write-Host "服务将在 http://localhost:$($env:PORT) 上运行" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Cyan

python -m uvicorn open_webui.main:app --host $env:HOST --port $env:PORT --forwarded-allow-ips '*' --workers 1 --ws auto

Write-Host "=== 脚本执行完成 ===" -ForegroundColor Green