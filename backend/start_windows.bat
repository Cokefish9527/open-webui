@echo off

:: Set Hugging Face endpoint to a mirror for faster downloads
SET HF_ENDPOINT=https://hf-mirror.com

:: Set environment variable to disable symlinks for Hugging Face cache
SET HF_HUB_DISABLE_SYMLINKS_WARNING=1

:: Clear potentially problematic environment variables
set BT_PYTHON=

:: Set the Python 3.11 path explicitly
set PYTHON_HOME=C:\Users\bmkz\AppData\Local\Programs\Python\Python311
set VIRTUAL_ENV=D:\Work\hsch\open-webui\venv

:: Set PATH to use Python 3.11 and virtual environment
set PATH=%PYTHON_HOME%;%PYTHON_HOME%\Scripts;%VIRTUAL_ENV%\Scripts;%PATH%

SETLOCAL ENABLEDELAYEDEXPANSION

:: Get the directory of the current script
SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || exit /b

:: Add conditional Playwright browser installation
IF /I "%WEB_LOADER_ENGINE%" == "playwright" (
    IF "%PLAYWRIGHT_WS_URL%" == "" (
        echo Installing Playwright browsers...
        "%PYTHON_HOME%\Scripts\playwright.exe" install chromium
        "%PYTHON_HOME%\Scripts\playwright.exe" install-deps chromium
    )

    "%VIRTUAL_ENV%\Scripts\python.exe" -c "import nltk; nltk.download('punkt_tab')"
)

SET "KEY_FILE=.webui_secret_key"
IF NOT "%WEBUI_SECRET_KEY_FILE%" == "" (
    SET "KEY_FILE=%WEBUI_SECRET_KEY_FILE%"
)

IF "%PORT%"=="" SET PORT=8080
IF "%HOST%"=="" SET HOST=0.0.0.0
SET "WEBUI_SECRET_KEY=%WEBUI_SECRET_KEY%"
SET "WEBUI_JWT_SECRET_KEY=%WEBUI_JWT_SECRET_KEY%"

:: Check if WEBUI_SECRET_KEY and WEBUI_JWT_SECRET_KEY are not set
IF "%WEBUI_SECRET_KEY%%WEBUI_JWT_SECRET_KEY%" == " " (
    echo Loading WEBUI_SECRET_KEY from file, not provided as an environment variable.

    IF NOT EXIST "%KEY_FILE%" (
        echo Generating WEBUI_SECRET_KEY
        :: Generate a random value to use as a WEBUI_SECRET_KEY in case the user didn't provide one
        SET /p WEBUI_SECRET_KEY=<nul
        FOR /L %%i IN (1,1,12) DO SET /p WEBUI_SECRET_KEY=<!random!>>%KEY_FILE%
        echo WEBUI_SECRET_KEY generated
    )

    echo Loading WEBUI_SECRET_KEY from %KEY_FILE%
    SET /p WEBUI_SECRET_KEY=<%KEY_FILE%
)

:: Execute uvicorn with explicit Python path
SET "WEBUI_SECRET_KEY=%WEBUI_SECRET_KEY%"
IF "%UVICORN_WORKERS%"=="" SET UVICORN_WORKERS=1

:: Use the virtual environment's Python executable directly
"%VIRTUAL_ENV%\Scripts\python.exe" -m uvicorn open_webui.main:app --host "%HOST%" --port "%PORT%" --forwarded-allow-ips '*' --workers %UVICORN_WORKERS% --ws auto