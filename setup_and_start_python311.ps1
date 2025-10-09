
# Python 3.11.9 虚拟环境设置和启动脚本
# 该脚本将检查、创建（如果需要）Python 3.11.9 虚拟环境并启动 Open-WebUI 服务

Write-Host "=== Open-WebUI Python 3.11.9 虚拟环境设置和启动脚本 ===" -ForegroundColor Green

# 查找 Python 3.11 安装路径
Write-Host "查找 Python 3.11 安装路径..." -ForegroundColor Yellow
$pythonPaths = @(
    "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311",
    "C:\Program Files\Python311",
    "C:\Python311"
)

$python311Path = $null
foreach ($path in $pythonPaths) {
    if (Test-Path "$path\python.exe") {
        $python311Path = $path
        break
    }
}

if (-not $python311Path) {
    Write-Host "错误: 未找到 Python 3.11 安装路径" -ForegroundColor Red
    Write-Host "请手动安装 Python 3.11.9 或调整脚本中的路径" -ForegroundColor Yellow
    Write-Host "下载地址: https://www.python.org/downloads/release/python-3119/" -ForegroundColor Cyan
    exit 1
}

Write-Host "找到 Python 3.11: $python311Path" -ForegroundColor Green
$pythonExe = "$python311Path\python.exe"

# 检查 Python 版本
Write-Host "检查 Python 版本..." -ForegroundColor Yellow
$versionOutput = & $pythonExe --version
Write-Host $versionOutput -ForegroundColor Cyan

if ($versionOutput -notlike "*3.11.9*") {
    Write-Host "警告: 推荐使用 Python 3.11.9 版本以获得最佳兼容性" -ForegroundColor Yellow
}

# 检查虚拟环境
$venvPath = "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "未找到虚拟环境，正在创建..." -ForegroundColor Yellow
    & $pythonExe -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: 虚拟环境创建失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "虚拟环境创建成功!" -ForegroundColor Green
} else {
    Write-Host "发现现有虚拟环境: $venvPath" -ForegroundColor Green
}

# 激活虚拟环境
Write-Host "激活虚拟环境..." -ForegroundColor Yellow
$activateScript = "$venvPath\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Host "错误: 未找到激活脚本: $activateScript" -ForegroundColor Red
    exit 1
}

# 升级 pip
Write-Host "升级 pip..." -ForegroundColor Yellow
& $venvPath\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: pip 升级失败" -ForegroundColor Red
    exit 1
}
Write-Host "pip 升级成功!" -ForegroundColor Green

# 检查依赖是否已安装
Write-Host "检查项目依赖..." -ForegroundColor Yellow
$requirementsFile = "requirements.txt"
if (-not (Test-Path $requirementsFile)) {
    Write-Host "错误: 未找到依赖文件: $requirementsFile" -ForegroundColor Red
    exit 1
}

# 安装/更新依赖
Write-Host "安装/更新项目依赖..." -ForegroundColor Yellow
Set-Location backend
& ..\$venvPath\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 依赖安装失败" -ForegroundColor Red
    Set-Location ..
    exit 1
}
Set-Location ..

Write-Host "依赖安装成功!" -ForegroundColor Green

# 设置环境变量
Write-Host "设置环境变量..." -ForegroundColor Yellow
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"

Write-Host "环境变量设置完成!" -ForegroundColor Green

# 创建必要的目录
Write-Host "创建必要的数据目录..." -ForegroundColor Yellow
$directories = @("data", "data\uploads", "data\cache", "data\vector_db")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "创建目录: $dir" -ForegroundColor Cyan
    }
}

Write-Host "数据目录创建完成!" -ForegroundColor Green

# 启动服务
Write-Host "=== 启动 Open-WebUI 服务 ===" -ForegroundColor Green
Write-Host "使用虚拟环境中的 Python: $venvPath\Scripts\python.exe" -ForegroundColor Cyan
Write-Host "服务将在 http://localhost:8080 上运行" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 启动 uvicorn 服务器
& $venvPath\Scripts\python.exe -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --forwarded-allow-ips '*' --workers 1 --ws auto