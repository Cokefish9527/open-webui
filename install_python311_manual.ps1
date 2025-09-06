# Python 3.11 手动安装脚本
# 该脚本将安装 Python 3.11

Write-Host "=== Python 3.11 手动安装脚本 ===" -ForegroundColor Green

# 检查是否已经安装了 Python 3.11
Write-Host "检查是否已安装 Python 3.11..." -ForegroundColor Yellow
$python311Path = Get-ChildItem "C:\Program Files\Python311" -ErrorAction SilentlyContinue
if ($python311Path) {
    Write-Host "Python 3.11 已经安装在: $($python311Path.FullName)" -ForegroundColor Green
    # 更新 PATH 环境变量
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    if (-not ($currentPath -like "*Python311*")) {
        $newPath = "$currentPath;C:\Program Files\Python311;C:\Program Files\Python311\Scripts"
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "Machine")
        Write-Host "已更新系统 PATH 环境变量" -ForegroundColor Green
    }
    exit 0
}

# 查找安装程序
Write-Host "查找 Python 3.11 安装程序..." -ForegroundColor Yellow
$installerPath = "$env:TEMP\python311_installer.exe"
if (-not (Test-Path $installerPath)) {
    Write-Host "未找到安装程序，重新下载..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $installerPath
        Write-Host "下载完成: $installerPath" -ForegroundColor Green
    } catch {
        Write-Host "下载失败: $_" -ForegroundColor Red
        Write-Host "请手动下载并安装 Python 3.11:" -ForegroundColor Yellow
        Write-Host "访问 https://www.python.org/downloads/release/python-3119/" -ForegroundColor Cyan
        exit 1
    }
} else {
    Write-Host "找到安装程序: $installerPath" -ForegroundColor Green
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
Write-Host "清理安装文件..." -ForegroundColor Yellow
Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
Write-Host "清理完成" -ForegroundColor Green

# 验证安装
Write-Host "验证新安装的 Python 版本..." -ForegroundColor Yellow
# 刷新环境变量
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 检查版本
$pythonVersion = python --version 2>&1
Write-Host "新版本: $pythonVersion" -ForegroundColor Cyan

Write-Host "=== Python 3.11 安装完成 ===" -ForegroundColor Green