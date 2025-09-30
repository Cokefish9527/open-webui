#!/bin/bash
# 启动脚本，禁用自动迁移检查

# 设置环境变量禁用迁移
export SKIP_MIGRATIONS=true

# 启动服务
python -m open_webui.main