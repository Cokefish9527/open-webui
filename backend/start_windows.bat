@echo off
chcp 65001 >nul
echo === Open-WebUI 启动脚本 ===
echo.

:: Set Hugging Face endpoint to a mirror for faster downloads
SET HF_ENDPOINT=https://hf-mirror.com
echo 设置 Hugging Face 镜像: %HF_ENDPOINT%

:: Set environment variable to disable symlinks for Hugging Face cache
SET HF_HUB_DISABLE_SYMLINKS_WARNING=1

:: Clear potentially problematic environment variables
set BT_PYTHON=

:: Get the directory of the current script
SET "SCRIPT_DIR=%~dp0"
echo 切换到脚本目录: %SCRIPT_DIR%
cd /d "%SCRIPT_DIR%" || (
    echo 错误: 无法切换到脚本目录
    pause
    exit /b 1
)
echo 当前工作目录: %CD%
echo.

:: Detect Python executable path
echo 检测Python环境...
set "PYTHON_EXE="

:: First check common virtual environment locations
if exist "%SCRIPT_DIR%venv\Scripts\python.exe" (
    echo 发现本地虚拟环境: %SCRIPT_DIR%venv
    set "PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%..\.\.venv\Scripts\python.exe" (
    echo 发现父目录虚拟环境: %SCRIPT_DIR%..\.\.venv
    set "PYTHON_EXE=%SCRIPT_DIR%..\.\.venv\Scripts\python.exe"
) else if exist "C:\work\open-webui\.venv\Scripts\python.exe" (
    echo 发现特定虚拟环境: C:\work\open-webui\.venv
    set "PYTHON_EXE=C:\work\open-webui\.venv\Scripts\python.exe"
) else (
    :: Try to find system Python
    echo 尝试使用系统Python...
    if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe" (
        set "PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe"
        echo 找到系统Python: %PYTHON_EXE%
    ) else if exist "C:\Python311\python.exe" (
        set "PYTHON_EXE=C:\Python311\python.exe"
        echo 找到系统Python: %PYTHON_EXE%
    ) else (
        echo 错误: 未找到Python 3.11安装。
        echo 请检查以下路径是否存在Python:
        echo - C:\work\open-webui\.venv\Scripts\python.exe
        echo - C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe
        echo - C:\Python311\python.exe
        pause
        exit /b 1
    )
)

:: Test Python availability
echo.
echo 测试Python可用性...
"%PYTHON_EXE%" --version
if %ERRORLEVEL% neq 0 (
    echo 错误: Python无法正常运行
    pause
    exit /b 1
)
echo Python测试成功!
echo.

SETLOCAL ENABLEDELAYEDEXPANSION

:: Set environment variables
echo 配置环境变量...
set "PYTHONPATH=%CD%;%PYTHONPATH%"
set "DATA_DIR=%CD%\data"
set "DATABASE_URL=sqlite:///%CD:\=/%/data/webui.db"
echo 设置PYTHONPATH: %CD%
echo 设置DATA_DIR: %DATA_DIR%
echo 设置DATABASE_URL: %DATABASE_URL%

:: Create necessary directories
if not exist "data" mkdir data
if not exist "data\uploads" mkdir "data\uploads"
if not exist "data\cache" mkdir "data\cache"
if not exist "data\vector_db" mkdir "data\vector_db"
echo 确保数据目录存在: %DATA_DIR%
echo.

:: Add conditional Playwright browser installation
IF /I "%WEB_LOADER_ENGINE%" == "playwright" (
    IF "%PLAYWRIGHT_WS_URL%" == "" (
        echo Installing Playwright browsers...
        "%PYTHON_EXE%" -m playwright install chromium
        "%PYTHON_EXE%" -m playwright install-deps chromium
    )

    "%PYTHON_EXE%" -c "import nltk; nltk.download('punkt_tab')"
)

IF "%PORT%"=="" SET PORT=8080
IF "%HOST%"=="" SET HOST=0.0.0.0

:: WebSocket configuration to fix path issues
SET "SOCKETIO_PATH=/ws/socket.io"

:: Check necessary modules
echo 检查必要的模块...
"%PYTHON_EXE%" -c "import sys; sys.path.insert(0, '.'); import open_webui.main; print('open_webui模块可用')" 2>nul
if %ERRORLEVEL% neq 0 (
    echo 警告: open_webui模块检查失败，但将继续尝试启动服务器...
)
echo open_webui模块检查完成!
echo.

:: Execute uvicorn with explicit Python path
IF "%UVICORN_WORKERS%"=="" SET UVICORN_WORKERS=1

echo === 启动服务器 ===
echo 使用Python: %PYTHON_EXE%
echo 主机: %HOST%
echo 端口: %PORT%
echo 工作进程数: %UVICORN_WORKERS%
echo 服务将在 http://localhost:%PORT% 上运行
REM 按 Ctrl+C 停止服务
echo.

:: Use the detected Python executable
"%PYTHON_EXE%" -m uvicorn open_webui.main:app --host "%HOST%" --port "%PORT%" --forwarded-allow-ips '*' --workers %UVICORN_WORKERS% --ws auto