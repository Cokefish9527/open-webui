# Open-WebUI 服务运行脚本 (PowerShell)
# 该脚本将激活虚拟环境并启动服务

Write-Host "=== Open-WebUI 服务运行脚本 ===" -ForegroundColor Green

# 检查虚拟环境是否存在
if (-not (Test-Path ".\venv")) {
    Write-Host "错误: 虚拟环境不存在。请先运行 init_basic.ps1 脚本。" -ForegroundColor Red
    exit 1
}

# 激活虚拟环境
Write-Host "激活虚拟环境..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 虚拟环境激活失败。" -ForegroundColor Red
    exit 1
}
Write-Host "虚拟环境已激活!" -ForegroundColor Green

# 进入后端目录
Write-Host "进入后端目录..." -ForegroundColor Yellow
Set-Location backend

# 设置默认端口和主机
if (-not $env:PORT) {
    $env:PORT = "8080"
}
if (-not $env:HOST) {
    $env:HOST = "0.0.0.0"
}

Write-Host "服务配置:" -ForegroundColor Yellow
Write-Host "  端口: $($env:PORT)" -ForegroundColor Yellow
Write-Host "  主机: $($env:HOST)" -ForegroundColor Yellow

# 启动服务
Write-Host "启动 Open-WebUI 服务..." -ForegroundColor Green
Write-Host "服务将在 http://localhost:$($env:PORT) 上运行" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Cyan

# 使用 start_windows.bat 启动服务
.\start_windows.bat