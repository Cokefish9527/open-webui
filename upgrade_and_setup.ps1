# Open-WebUI Python 升级和设置脚本
# 该脚本将升级 Python 到 3.11+ 并重新设置 Open-WebUI 环境

Write-Host "=== Open-WebUI Python 升级和设置脚本 ===" -ForegroundColor Green

# 检查当前 Python 版本
Write-Host "检查当前 Python 版本..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "当前版本: $pythonVersion" -ForegroundColor Cyan

# 提取版本号
$versionString = $pythonVersion -replace "Python ", ""
$versionParts = $versionString -split "\."
$majorVersion = [int]$versionParts[0]
$minorVersion = [int]$versionParts[1]

if ($majorVersion -gt 3 -or ($majorVersion -eq 3 -and $minorVersion -ge 11)) {
    Write-Host "您的 Python 版本已经满足要求 ($pythonVersion)" -ForegroundColor Green
} else {
    Write-Host "您的 Python 版本低于 3.11，需要升级" -ForegroundColor Yellow
    
    # 下载 Python 3.11
    Write-Host "准备下载 Python 3.11..." -ForegroundColor Yellow
    $downloadUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $installerPath = "$env:TEMP\python-3.11.9-amd64.exe"

    Write-Host "正在下载 Python 3.11 安装程序..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath
        Write-Host "下载完成: $installerPath" -ForegroundColor Green
    } catch {
        Write-Host "下载失败: $_" -ForegroundColor Red
        Write-Host "请手动下载并安装 Python 3.11:" -ForegroundColor Yellow
        Write-Host "访问 https://www.python.org/downloads/release/python-3119/" -ForegroundColor Cyan
        exit 1
    }

    # 安装 Python 3.11
    Write-Host "正在安装 Python 3.11..." -ForegroundColor Yellow
    Write-Host "安装过程中可能会出现用户账户控制(UAC)提示，请允许操作" -ForegroundColor Yellow

    try {
        Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait
        Write-Host "Python 3.11 安装完成!" -ForegroundColor Green
    } catch {
        Write-Host "安装失败: $_" -ForegroundColor Red
        exit 1
    }

    # 清理安装文件
    Remove-Item $installerPath -Force
    Write-Host "清理完成" -ForegroundColor Green

    # 验证安装
    Write-Host "验证新安装的 Python 版本..." -ForegroundColor Yellow
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # 重新检查版本
    $pythonVersion = python --version 2>&1
    Write-Host "新版本: $pythonVersion" -ForegroundColor Cyan
}

# 删除旧的虚拟环境（如果存在）
if (Test-Path ".\venv") {
    Write-Host "删除旧的虚拟环境..." -ForegroundColor Yellow
    Remove-Item ".\venv" -Recurse -Force
    Write-Host "旧虚拟环境已删除" -ForegroundColor Green
}

# 创建新的虚拟环境
Write-Host "创建新的虚拟环境..." -ForegroundColor Yellow
python -m venv venv
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
Write-Host "依赖安装成功!" -ForegroundColor Green

# 安装 Playwright 浏览器（如需要）
Write-Host "检查是否需要安装 Playwright 浏览器..." -ForegroundColor Yellow
$env:PLAYWRIGHT_WS_URL = ""
if ($env:WEB_LOADER_ENGINE -eq "playwright") {
    Write-Host "安装 Playwright 浏览器..." -ForegroundColor Yellow
    playwright install chromium
    if ($LASTEXITCODE -ne 0) {
        Write-Host "警告: Playwright 浏览器安装失败。" -ForegroundColor Yellow
    } else {
        Write-Host "Playwright 浏览器安装成功!" -ForegroundColor Green
    }
}

Write-Host "=== Python 升级和环境设置完成 ===" -ForegroundColor Green
Write-Host "要运行服务，请执行以下命令:" -ForegroundColor Cyan
Write-Host "1. .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "2. cd backend" -ForegroundColor Cyan
Write-Host "3. .\start_windows.bat" -ForegroundColor Cyan