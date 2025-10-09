# Python 3.11 虚拟环境设置脚本
# 该脚本将创建并设置 Python 3.11 虚拟环境

Write-Host "=== Python 3.11 虚拟环境设置脚本 ===" -ForegroundColor Green

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
    Write-Host "请手动安装 Python 3.11 或调整脚本中的路径" -ForegroundColor Yellow
    exit 1
}

Write-Host "找到 Python 3.11: $python311Path" -ForegroundColor Green
$pythonExe = "$python311Path\python.exe"

# 检查 Python 版本
Write-Host "检查 Python 版本..." -ForegroundColor Yellow
& $pythonExe --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 无法运行 Python 3.11" -ForegroundColor Red
    exit 1
}

# 删除旧的虚拟环境（如果存在）
$venvPath = "venv"
if (Test-Path $venvPath) {
    Write-Host "删除旧的虚拟环境..." -ForegroundColor Yellow
    Remove-Item $venvPath -Recurse -Force
}

# 创建虚拟环境
Write-Host "创建虚拟环境..." -ForegroundColor Yellow
& $pythonExe -m venv $venvPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 虚拟环境创建失败" -ForegroundColor Red
    exit 1
}
Write-Host "虚拟环境创建成功!" -ForegroundColor Green

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

# 安装依赖
Write-Host "安装项目依赖..." -ForegroundColor Yellow
Set-Location backend
& ..\$venvPath\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 依赖安装失败" -ForegroundColor Red
    Set-Location ..
    exit 1
}
Set-Location ..

Write-Host "依赖安装成功!" -ForegroundColor Green

Write-Host "=== 虚拟环境设置完成 ===" -ForegroundColor Green
Write-Host "要激活虚拟环境，请运行以下命令:" -ForegroundColor Cyan
Write-Host ".\venv\Scripts\Activate.ps1" -ForegroundColor Cyan