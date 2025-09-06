# Python 3.11+ 升级脚本
# 该脚本将帮助您下载并安装 Python 3.11

Write-Host "=== Python 3.11+ 升级脚本 ===" -ForegroundColor Green

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
    exit 0
} else {
    Write-Host "您的 Python 版本低于 3.11，需要升级" -ForegroundColor Yellow
}

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
python --version
if ($LASTEXITCODE -eq 0) {
    Write-Host "Python 3.11+ 已成功安装并可用!" -ForegroundColor Green
} else {
    Write-Host "验证失败，请重新启动 PowerShell 窗口后再试" -ForegroundColor Red
}

Write-Host "=== 升级完成 ===" -ForegroundColor Green