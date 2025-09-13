@echo off
chcp 65001 >nul
echo.
echo ====================================================
echo            工作流场景测试脚本启动器
echo ====================================================
echo.

REM 设置错误处理
setlocal enabledelayedexpansion

REM 检测Python环境
set PYTHON_CMD=
set VENV_PATH=

echo [调试] 正在检测Python环境...

REM 检测虚拟环境路径
if exist "venv\Scripts\python.exe" (
    set VENV_PATH=venv\Scripts
    set PYTHON_CMD=venv\Scripts\python.exe
    echo [调试] 找到虚拟环境: venv\Scripts
) else if exist "..\venv\Scripts\python.exe" (
    set VENV_PATH=..\venv\Scripts
    set PYTHON_CMD=..\venv\Scripts\python.exe
    echo [调试] 找到虚拟环境: ..\venv\Scripts
) else if exist "..\.venv\Scripts\python.exe" (
    set VENV_PATH=..\.venv\Scripts
    set PYTHON_CMD=..\.venv\Scripts\python.exe
    echo [调试] 找到虚拟环境: ..\.venv\Scripts
) else if exist "C:\work\open-webui\.venv\Scripts\python.exe" (
    set VENV_PATH=C:\work\open-webui\.venv\Scripts
    set PYTHON_CMD=C:\work\open-webui\.venv\Scripts\python.exe
    echo [调试] 找到虚拟环境: C:\work\open-webui\.venv\Scripts
)

if "%PYTHON_CMD%"=="" (
    echo [错误] 找不到Python虚拟环境！
    echo 请确保已创建并安装了依赖的虚拟环境
    echo 参考路径：venv\Scripts\python.exe
    pause
    exit /b 1
)

echo [调试] 使用Python: %PYTHON_CMD%

REM 设置环境变量
set PYTHONPATH=C:\work\open-webui\backend
echo [调试] 设置PYTHONPATH: %PYTHONPATH%

REM 显示菜单
:menu
echo.
echo 请选择测试模式：
echo.
echo 1. 快速测试 (quick) - 基本功能验证
echo 2. 完整测试 (full) - 所有功能验证
echo 3. 企业信息收集测试 (company_info)
echo 4. 视频创作测试 (video_creation)
echo 5. 视频分析测试 (video_analysis) 
echo 6. WOC管理功能测试 (woc_management)
echo 7. 显示帮助信息
echo 8. 退出
echo.
set /p choice="请输入选择 (1-8): "

REM 处理选择
if "%choice%"=="1" (
    set TEST_MODE=quick
    goto run_test
)
if "%choice%"=="2" (
    set TEST_MODE=full
    goto run_test
)
if "%choice%"=="3" (
    set TEST_MODE=company_info
    goto run_test
)
if "%choice%"=="4" (
    set TEST_MODE=video_creation
    goto run_test
)
if "%choice%"=="5" (
    set TEST_MODE=video_analysis
    goto run_test
)
if "%choice%"=="6" (
    set TEST_MODE=woc_management
    goto run_test
)
if "%choice%"=="7" (
    goto show_help
)
if "%choice%"=="8" (
    echo 退出测试
    exit /b 0
)

echo [错误] 无效选择，请重新输入
goto menu

:run_test
echo.
echo ====================================================
echo 开始运行 %TEST_MODE% 模式测试...
echo ====================================================
echo [调试] 执行命令: "%PYTHON_CMD%" test_workflow_scenarios.py %TEST_MODE%
echo.

REM 运行测试
"%PYTHON_CMD%" test_workflow_scenarios.py %TEST_MODE%

REM 检查执行结果
if !errorlevel! equ 0 (
    echo.
    echo ====================================================
    echo            测试执行完成 - 成功
    echo ====================================================
) else (
    echo.
    echo ====================================================
    echo            测试执行完成 - 发现问题
    echo ====================================================
    echo 错误代码: !errorlevel!
)

echo.
echo 按任意键继续...
pause >nul
goto menu

:show_help
echo.
echo ====================================================
echo                    帮助信息
echo ====================================================
echo.
echo 测试模式说明：
echo.
echo [快速测试] - 验证基本功能
echo   - WOC健康检查
echo   - WOC状态查询  
echo   - 企业信息收集工作流
echo.
echo [完整测试] - 验证所有功能
echo   - 所有快速测试项目
echo   - 视频创作工作流
echo   - 视频分析工作流
echo   - 直接工作流触发
echo   - 用户执行列表查询
echo.
echo [专项测试] - 验证特定功能
echo   - company_info: 企业信息收集
echo   - video_creation: 视频创作
echo   - video_analysis: 视频分析
echo   - woc_management: WOC管理功能
echo.
echo 测试前置条件：
echo   1. 服务器正在运行 (默认 http://localhost:8080)
echo   2. WOC工作流编排中心已启用
echo   3. n8n工作流服务可用
echo   4. 测试用户 admin@localhost 存在且密码为 admin
echo.
echo 环境配置：
echo   Python环境: %PYTHON_CMD%
echo   PYTHONPATH: %PYTHONPATH%
echo.
echo ====================================================
echo.
echo 按任意键返回主菜单...
pause >nul
goto menu