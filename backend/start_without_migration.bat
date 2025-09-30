@echo off
REM 启动脚本，禁用自动迁移检查

REM 设置环境变量禁用迁移
set SKIP_MIGRATIONS=true

REM 启动服务
python -m open_webui.main