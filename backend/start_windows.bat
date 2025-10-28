@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

echo === Open-WebUI Windows Launcher ===
echo.

:: Optional mirror configuration (comment out if not needed)
set "HF_ENDPOINT=https://hf-mirror.com"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
set "BT_PYTHON="

:: Change into backend directory
set "BACKEND_DIR=%~dp0"
set "PROJECT_DIR=%BACKEND_DIR%.."
cd /d "%BACKEND_DIR%" || (
    echo [ERROR] Unable to change directory to %BACKEND_DIR%
    pause
    exit /b 1
)
echo Working directory: %CD%
echo.

:: Locate Python interpreter (prefer project venv)
set "PYTHON_EXE="
if exist "%PROJECT_DIR%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_DIR%\venv\Scripts\python.exe"
) else if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
) else if exist "C:\work\open-webui\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=C:\work\open-webui\.venv\Scripts\python.exe"
)

if not defined PYTHON_EXE (
    for %%P in (
        "C:\Program Files\Python311\python.exe"
        "C:\Program Files\Python3119\python.exe"
        "C:\Python311\python.exe"
        "C:\Python3119\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    ) do (
        if not defined PYTHON_EXE (
            if exist %%~P set "PYTHON_EXE=%%~P"
        )
    )
)

if not defined PYTHON_EXE (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)

if not defined PYTHON_EXE (
    for /f "delims=" %%i in ('where py 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)

if not defined PYTHON_EXE (
    echo [ERROR] Python 3.11+ interpreter not found.
    echo         Ensure a 3.11 installation exists or create a virtual environment.
    pause
    exit /b 1
)

echo Using Python: %PYTHON_EXE%

:: Verify Python version
for /f "tokens=2 delims= " %%i in ('"%PYTHON_EXE%" --version 2^>^&1') do set "PY_VERSION_NUM=%%i"
for /f "tokens=1,2 delims=." %%i in ("%PY_VERSION_NUM%") do (
    set "PY_MAJOR=%%i"
    set "PY_MINOR=%%j"
)

set "PY_OK=0"
if "%PY_MAJOR%"=="3" (
    for /f %%m in ("%PY_MINOR%") do (
        if %%m GEQ 11 set "PY_OK=1"
    )
)

if "%PY_OK%"=="0" (
    echo [WARNING] Detected Python %PY_VERSION_NUM%. Python 3.11 or newer is recommended.
)
echo.

:: Basic sanity check
"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Unable to execute Python: %PYTHON_EXE%
    pause
    exit /b 1
)

:: Prepare environment variables
set "PYTHONPATH="
set "DATA_DIR=%CD%\data"

set "ENV_DATABASE_URL="
if not defined DATABASE_URL (
    if exist "%PROJECT_DIR%\.env" (
        for /f "usebackq tokens=1* delims==" %%A in (`findstr /R "^DATABASE_URL=" "%PROJECT_DIR%\.env"`) do (
            if /I "%%A"=="DATABASE_URL" (
                set "ENV_DATABASE_URL=%%B"
            )
        )
    )
    if defined ENV_DATABASE_URL (
        for /f "delims=" %%Z in ("!ENV_DATABASE_URL!") do set "ENV_DATABASE_URL=%%~Z"
        set "ENV_DATABASE_URL=!ENV_DATABASE_URL:'=!"
        set "DATABASE_URL=!ENV_DATABASE_URL!"
    )
)

if not defined DATABASE_URL (
    set "DATABASE_URL=sqlite:///%CD:\=/%/data/webui.db"
)

if not exist "data" mkdir "data"
if not exist "data\uploads" mkdir "data\uploads"
if not exist "data\cache" mkdir "data\cache"
if not exist "data\vector_db" mkdir "data\vector_db"

echo DATA_DIR     = %DATA_DIR%
echo DATABASE_URL = %DATABASE_URL%
echo.

:: Optional Playwright support
if /I "%WEB_LOADER_ENGINE%"=="playwright" (
    if "%PLAYWRIGHT_WS_URL%"=="" (
        "%PYTHON_EXE%" -m playwright install chromium
        "%PYTHON_EXE%" -m playwright install-deps chromium
    )
    "%PYTHON_EXE%" -c "import nltk; nltk.download('punkt_tab')"
)

if "%HOST%"=="" set "HOST=0.0.0.0"
if "%PORT%"=="" set "PORT=8080"
if "%UVICORN_WORKERS%"=="" set "UVICORN_WORKERS=1"
set "SOCKETIO_PATH=/ws/socket.io"

:: Quick import check (non-fatal)
"%PYTHON_EXE%" -c "import sys; sys.path.insert(0, '.'); import open_webui.main" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] open_webui package import check failed. Continuing anyway...
)

echo === Starting Server ===
echo Host   : %HOST%
echo Port   : %PORT%
echo Workers: %UVICORN_WORKERS%
echo Launching at http://localhost:%PORT%
echo.

"%PYTHON_EXE%" -m uvicorn open_webui.main:app --host "%HOST%" --port "%PORT%" --forwarded-allow-ips="*" --workers %UVICORN_WORKERS% --ws auto

endlocal
