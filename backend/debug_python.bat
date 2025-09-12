@echo off
echo === 调试脚本 ===

echo 当前VIRTUAL_ENV: [%VIRTUAL_ENV%]
echo 检查Python可执行文件...

if not "%VIRTUAL_ENV%" == "" (
    set "PYTHON_EXE=%VIRTUAL_ENV%\Scripts\python.exe"
    echo 设置的Python路径: [%PYTHON_EXE%]
    
    echo 检查文件是否存在...
    if exist "%PYTHON_EXE%" (
        echo Python文件存在: %PYTHON_EXE%
    ) else (
        echo Python文件不存在: %PYTHON_EXE%
        echo 让我们列出目录内容...
        dir "%VIRTUAL_ENV%\Scripts\python*"
    )
) else (
    echo 未设置VIRTUAL_ENV环境变量
)

pause