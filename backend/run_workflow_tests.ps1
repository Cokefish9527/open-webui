# 工作流场景测试 PowerShell 启动脚本
# 提供跨平台支持和更好的错误处理

param(
    [Parameter(Position=0)]
    [ValidateSet("quick", "full", "company_info", "video_creation", "video_analysis", "woc_management", "enhanced")]
    [string]$TestMode = "",
    
    [Parameter()]
    [string]$ConfigFile = "test_config.json",
    
    [Parameter()]
    [switch]$Help
)

# 设置控制台编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 显示帮助信息
function Show-Help {
    Write-Host @"

🔧 工作流场景测试脚本 PowerShell 版本
==========================================

参数说明：
  -TestMode <模式>     测试模式 (quick, full, company_info, video_creation, video_analysis, woc_management, enhanced)
  -ConfigFile <文件>   配置文件路径 (默认: test_config.json)
  -Help               显示此帮助信息

测试模式：
  quick               快速测试 - 基本功能验证
  full                完整测试 - 所有功能验证
  company_info        企业信息收集专项测试
  video_creation      视频创作专项测试
  video_analysis      视频分析专项测试
  woc_management      WOC管理功能专项测试
  enhanced            增强版综合测试 (推荐)

使用示例：
  .\run_workflow_tests.ps1 -TestMode enhanced
  .\run_workflow_tests.ps1 -TestMode quick
  .\run_workflow_tests.ps1 -TestMode full -ConfigFile custom_config.json

注意事项：
  1. 确保服务器正在运行 (默认 http://localhost:8080)
  2. 确保WOC工作流编排中心已启用
  3. 确保n8n工作流服务可用
  4. 测试用户需要有相应权限

"@
}

# 检测Python环境
function Find-PythonEnvironment {
    Write-Host "🔍 检测Python环境..." -ForegroundColor Cyan
    
    $pythonPaths = @(
        "venv\Scripts\python.exe",
        "..\venv\Scripts\python.exe", 
        "..\.venv\Scripts\python.exe",
        "C:\work\open-webui\.venv\Scripts\python.exe"
    )
    
    foreach ($path in $pythonPaths) {
        if (Test-Path $path) {
            Write-Host "✅ 找到Python环境: $path" -ForegroundColor Green
            return $path
        }
    }
    
    Write-Host "❌ 找不到Python虚拟环境！" -ForegroundColor Red
    Write-Host "请确保已创建并安装了依赖的虚拟环境" -ForegroundColor Yellow
    return $null
}

# 设置环境变量
function Set-Environment {
    $env:PYTHONPATH = "C:\work\open-webui\backend"
    Write-Host "📝 设置环境变量 PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Cyan
}

# 运行测试
function Start-Test {
    param(
        [string]$PythonPath,
        [string]$Mode,
        [string]$Config
    )
    
    Write-Host ""
    Write-Host "=====================================================" -ForegroundColor Yellow
    Write-Host "           开始运行工作流场景测试" -ForegroundColor Yellow
    Write-Host "=====================================================" -ForegroundColor Yellow
    Write-Host "测试模式: $Mode" -ForegroundColor Cyan
    Write-Host "配置文件: $Config" -ForegroundColor Cyan
    Write-Host "Python路径: $PythonPath" -ForegroundColor Cyan
    Write-Host ""
    
    try {
        if ($Mode -eq "enhanced") {
            # 运行增强版测试
            Write-Host "🚀 启动增强版综合测试..." -ForegroundColor Green
            & $PythonPath "enhanced_workflow_tester.py" $Config
        } else {
            # 运行基础版测试
            Write-Host "🚀 启动基础版测试..." -ForegroundColor Green
            & $PythonPath "test_workflow_scenarios.py" $Mode
        }
        
        $exitCode = $LASTEXITCODE
        
        Write-Host ""
        if ($exitCode -eq 0) {
            Write-Host "=====================================================" -ForegroundColor Green
            Write-Host "            测试执行完成 - 成功" -ForegroundColor Green
            Write-Host "=====================================================" -ForegroundColor Green
        } else {
            Write-Host "=====================================================" -ForegroundColor Red
            Write-Host "            测试执行完成 - 发现问题" -ForegroundColor Red
            Write-Host "=====================================================" -ForegroundColor Red
            Write-Host "错误代码: $exitCode" -ForegroundColor Red
        }
        
        return $exitCode
        
    } catch {
        Write-Host "❌ 测试执行异常: $($_.Exception.Message)" -ForegroundColor Red
        return 1
    }
}

# 交互式模式选择
function Select-TestMode {
    Write-Host ""
    Write-Host "请选择测试模式：" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. 快速测试 (quick) - 基本功能验证"
    Write-Host "2. 完整测试 (full) - 所有功能验证"
    Write-Host "3. 企业信息收集测试 (company_info)"
    Write-Host "4. 视频创作测试 (video_creation)"
    Write-Host "5. 视频分析测试 (video_analysis)"
    Write-Host "6. WOC管理功能测试 (woc_management)"
    Write-Host "7. 增强版综合测试 (enhanced) - 推荐"
    Write-Host "8. 显示帮助信息"
    Write-Host "9. 退出"
    Write-Host ""
    
    do {
        $choice = Read-Host "请输入选择 (1-9)"
        
        switch ($choice) {
            "1" { return "quick" }
            "2" { return "full" }
            "3" { return "company_info" }
            "4" { return "video_creation" }
            "5" { return "video_analysis" }
            "6" { return "woc_management" }
            "7" { return "enhanced" }
            "8" { Show-Help; continue }
            "9" { return $null }
            default { 
                Write-Host "❌ 无效选择，请重新输入" -ForegroundColor Red
                continue 
            }
        }
    } while ($true)
}

# 主程序
function Main {
    # 显示帮助
    if ($Help) {
        Show-Help
        return
    }
    
    Write-Host ""
    Write-Host "=====================================================" -ForegroundColor Cyan
    Write-Host "           工作流场景测试脚本启动器" -ForegroundColor Cyan
    Write-Host "=====================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # 检测Python环境
    $pythonPath = Find-PythonEnvironment
    if (-not $pythonPath) {
        Read-Host "按任意键退出..."
        return
    }
    
    # 设置环境变量
    Set-Environment
    
    # 检查配置文件
    if (-not (Test-Path $ConfigFile)) {
        Write-Host "⚠️ 配置文件 $ConfigFile 不存在，将使用默认配置" -ForegroundColor Yellow
    }
    
    # 选择测试模式
    if (-not $TestMode) {
        $TestMode = Select-TestMode
        if (-not $TestMode) {
            Write-Host "退出测试" -ForegroundColor Yellow
            return
        }
    }
    
    # 运行测试
    $exitCode = Start-Test -PythonPath $pythonPath -Mode $TestMode -Config $ConfigFile
    
    # 如果是交互模式，等待用户确认
    if (-not $PSBoundParameters.ContainsKey('TestMode')) {
        Write-Host ""
        Read-Host "按任意键退出..."
    }
    
    exit $exitCode
}

# 执行主程序
Main