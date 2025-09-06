# Open-WebUI 基础初始化脚本 (PowerShell)
# 该脚本将创建虚拟环境并安装依赖

Write-Host "=== Open-WebUI 基础初始化脚本 ===" -ForegroundColor Green

# 检查 Python 版本
Write-Host "检查 Python 版本..." -ForegroundColor Yellow
# 优先使用 Python 3.11
$pythonExe = "python"
$python311Paths = @(
    "C:\Users\bmkz\AppData\Local\Programs\Python\Python311\python.exe",
    "C:\Program Files\Python311\python.exe",
    "C:\Python311\python.exe"
)

foreach ($path in $python311Paths) {
    if (Test-Path $path) {
        $pythonExe = $path
        break
    }
}

& $pythonExe --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 未找到 Python。请先安装 Python 3.11。" -ForegroundColor Red
    exit 1
}

# 创建虚拟环境
Write-Host "创建虚拟环境..." -ForegroundColor Yellow
& $pythonExe -m venv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 虚拟环境创建失败。" -ForegroundColor Red
    exit 1
}
Write-Host "虚拟环境创建成功!" -ForegroundColor Green

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
Set-Location ..

Write-Host "依赖安装成功!" -ForegroundColor Green

Write-Host "=== 基础初始化完成 ===" -ForegroundColor Green
Write-Host "要运行服务，请执行以下命令:" -ForegroundColor Cyan
Write-Host "1. .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "2. cd backend" -ForegroundColor Cyan
Write-Host "3. .\start_windows.bat" -ForegroundColor Cyan