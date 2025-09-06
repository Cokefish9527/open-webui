# Python 3.11 安装脚本
# 该脚本将安装已下载的 Python 3.11

Write-Host "=== Python 3.11 安装脚本 ===" -ForegroundColor Green

# 查找已下载的 Python 3.11 安装程序
Write-Host "查找已下载的 Python 3.11 安装程序..." -ForegroundColor Yellow
$installerPath = Get-ChildItem "$env:TEMP\python-3.11*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName

if (-not $installerPath) {
    Write-Host "未找到已下载的 Python 3.11 安装程序" -ForegroundColor Red
    Write-Host "请先下载 Python 3.11 安装程序:" -ForegroundColor Yellow
    Write-Host "访问 https://www.python.org/downloads/release/python-3119/" -ForegroundColor Cyan
    exit 1
}

Write-Host "找到安装程序: $installerPath" -ForegroundColor Green

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
Write-Host "清理安装文件..." -ForegroundColor Yellow
Remove-Item $installerPath -Force
Write-Host "清理完成" -ForegroundColor Green

# 验证安装
Write-Host "验证新安装的 Python 版本..." -ForegroundColor Yellow
# 刷新环境变量
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 重新检查版本
$pythonVersion = python --version 2>&1
Write-Host "新版本: $pythonVersion" -ForegroundColor Cyan

Write-Host "=== Python 3.11 安装完成 ===" -ForegroundColor Green