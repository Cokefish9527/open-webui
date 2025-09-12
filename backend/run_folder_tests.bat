@echo off
setlocal enabledelayedexpansion

:: 文件夹接口测试启动脚本
:: 遵循Windows批处理脚本开发规范：详细调试信息、多环境检测、清晰错误提示

echo ========================================
echo 文件夹接口测试启动脚本
echo ========================================
echo.

:: 设置颜色和编码
chcp 65001 >nul 2>&1

:: 输出调试信息
echo [调试] 当前目录: %CD%
echo [调试] 脚本位置: %~dp0
echo [调试] 时间: %DATE% %TIME%
echo.

:: 检测Python环境 - 支持多种路径
echo [步骤1] 检测Python环境...

set PYTHON_EXE=
set VENV_PATH=

:: 检测虚拟环境路径（支持多种常见位置）
if exist "%~dp0venv\Scripts\python.exe" (
    set "VENV_PATH=%~dp0venv"
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
    echo [调试] 找到虚拟环境: %~dp0venv
) else if exist "%~dp0..\..\.venv\Scripts\python.exe" (
    set "VENV_PATH=%~dp0..\..\.venv"
    set "PYTHON_EXE=%~dp0..\..\.venv\Scripts\python.exe"
    echo [调试] 找到虚拟环境: %~dp0..\..\.venv
) else if exist "C:\work\open-webui\.venv\Scripts\python.exe" (
    set "VENV_PATH=C:\work\open-webui\.venv"
    set "PYTHON_EXE=C:\work\open-webui\.venv\Scripts\python.exe"
    echo [调试] 找到虚拟环境: C:\work\open-webui\.venv
) else (
    echo [警告] 未找到虚拟环境，尝试使用系统Python
    where python >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到Python解释器
        echo.
        echo 请确保满足以下条件之一：
        echo 1. 在 backend\venv 目录下有Python虚拟环境
        echo 2. 在项目根目录 .venv 下有Python虚拟环境  
        echo 3. 系统PATH中包含python命令
        echo.
        pause
        exit /b 1
    )
    set "PYTHON_EXE=python"
    echo [调试] 使用系统Python
)

echo [成功] Python环境: %PYTHON_EXE%
echo.

:: 激活虚拟环境（如果存在）
if defined VENV_PATH (
    echo [步骤2] 激活虚拟环境...
    call "%VENV_PATH%\Scripts\activate.bat"
    if errorlevel 1 (
        echo [警告] 虚拟环境激活失败，继续使用当前环境
    ) else (
        echo [成功] 虚拟环境已激活
    )
    echo.
)

:: 验证Python和依赖
echo [步骤3] 验证Python环境...
"%PYTHON_EXE%" --version
if errorlevel 1 (
    echo [错误] Python无法正常运行
    pause
    exit /b 1
)

echo [调试] 检查requests模块...
"%PYTHON_EXE%" -c "import requests; print('requests版本:', requests.__version__)" 2>nul
if errorlevel 1 (
    echo [警告] requests模块未安装或版本不兼容
    echo [提示] 请运行: pip install requests
    echo.
)
echo.

:: 检查测试脚本
echo [步骤4] 检查测试脚本...

set "WORKFLOW_SCRIPT=%~dp0test_folder_workflow.py"
set "SIMPLE_SCRIPT=%~dp0simple_folder_test.py"

if not exist "%WORKFLOW_SCRIPT%" (
    echo [错误] 找不到完整测试脚本: %WORKFLOW_SCRIPT%
    pause
    exit /b 1
)

if not exist "%SIMPLE_SCRIPT%" (
    echo [错误] 找不到简单测试脚本: %SIMPLE_SCRIPT%
    pause
    exit /b 1
)

echo [成功] 测试脚本检查完成
echo.

:: 提示用户配置TOKEN
echo [步骤5] 检查配置...
echo.
echo ⚠️  重要提示：
echo 请确保在测试脚本中设置了有效的TOKEN变量
echo 文件位置：
echo   - 完整测试: %WORKFLOW_SCRIPT%
echo   - 简单测试: %SIMPLE_SCRIPT%
echo.
echo 找到这一行并替换TOKEN：
echo   TOKEN = "your_token_here"
echo.

:: 询问用户选择测试类型
:CHOOSE_TEST
echo 请选择要运行的测试类型：
echo [1] 完整工作流测试 (详细的5步测试流程)
echo [2] 简单快速测试 (基础功能验证)
echo [3] 退出
echo.
set /p CHOICE="请输入选择 (1-3): "

if "%CHOICE%"=="1" (
    echo.
    echo [启动] 运行完整工作流测试...
    echo ========================================
    "%PYTHON_EXE%" "%WORKFLOW_SCRIPT%"
    set TEST_RESULT=!errorlevel!
) else if "%CHOICE%"=="2" (
    echo.
    echo [启动] 运行简单快速测试...
    echo ========================================
    "%PYTHON_EXE%" "%SIMPLE_SCRIPT%"
    set TEST_RESULT=!errorlevel!
) else if "%CHOICE%"=="3" (
    echo [退出] 用户选择退出
    goto :END
) else (
    echo [错误] 无效的选择，请重新输入
    echo.
    goto :CHOOSE_TEST
)

echo.
echo ========================================
if !TEST_RESULT! equ 0 (
    echo [完成] 测试执行完成
) else (
    echo [警告] 测试执行可能遇到问题 (退出代码: !TEST_RESULT!)
)
echo ========================================
echo.

:: 询问是否继续测试
echo 是否要运行其他测试? (Y/N)
set /p CONTINUE="请输入选择: "
if /i "%CONTINUE%"=="Y" (
    echo.
    goto :CHOOSE_TEST
)

:END
echo.
echo 💡 提示：
echo 如果测试失败，请检查：
echo 1. 后端服务器是否正在运行 (http://localhost:8080)
echo 2. TOKEN配置是否正确
echo 3. 网络连接是否正常
echo 4. API接口路径是否正确
echo.
echo 测试脚本位置：
echo   - 完整测试: %WORKFLOW_SCRIPT%
echo   - 简单测试: %SIMPLE_SCRIPT%
echo   - 诊断脚本: %~dp0diagnose_folder_issue.py
echo.

pause