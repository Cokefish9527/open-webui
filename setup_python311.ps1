# 设置Python 3.11环境的脚本

Write-Host "=== Python 3.11 环境设置 ===" -ForegroundColor Green

# 检查Python 3.11是否存在
$python311Path = "C:\Users\bmkz\AppData\Local\Programs\Python\Python311\python.exe"
if (Test-Path $python311Path) {
    Write-Host "找到Python 3.11: $python311Path" -ForegroundColor Green
} else {
    Write-Host "未找到Python 3.11，请检查安装路径" -ForegroundColor Red
    exit 1
}

# 删除旧的虚拟环境
if (Test-Path ".\venv") {
    Write-Host "删除旧的虚拟环境..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .\venv
}

# 创建新的虚拟环境
Write-Host "创建新的Python 3.11虚拟环境..." -ForegroundColor Yellow
& $python311Path -m venv venv

# 激活虚拟环境
Write-Host "激活虚拟环境..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# 升级pip
Write-Host "升级pip..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -m pip install --upgrade pip

Write-Host "环境设置完成！" -ForegroundColor Green