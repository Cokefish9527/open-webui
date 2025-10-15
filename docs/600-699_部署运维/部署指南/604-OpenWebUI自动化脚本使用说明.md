# Open-WebUI 自动化脚本使用说明

本项目提供了几个 PowerShell 脚本来帮助您快速设置和运行 Open-WebUI 服务。

## 脚本说明

### 1. setup_and_run.ps1 (推荐)
完整的自动化脚本，包含以下功能：
- 检查 Python 环境
- 创建虚拟环境（如果不存在）
- 激活虚拟环境
- 升级 pip
- 安装项目依赖
- 安装 Playwright 浏览器（如需要）
- 下载 NLTK 数据（如需要）
- 生成密钥文件
- 创建必要的数据目录
- 启动 Open-WebUI 服务

### 2. init_basic.ps1
基础初始化脚本，包含以下功能：
- 检查 Python 环境
- 创建虚拟环境
- 激活虚拟环境
- 升级 pip
- 安装项目依赖

### 3. run_service.ps1
服务运行脚本，包含以下功能：
- 激活虚拟环境
- 启动 Open-WebUI 服务

## 使用方法

### 方法一：使用完整自动化脚本（推荐）

```powershell
# 在项目根目录下执行
.\setup_and_run.ps1
```

### 方法二：分步执行

1. 初始化环境：
```powershell
.\init_basic.ps1
```

2. 运行服务：
```powershell
.\run_service.ps1
```

## 环境变量配置

您可以在运行脚本前设置以下环境变量来自定义服务：

- `PORT`: 服务端口，默认为 8080
- `HOST`: 服务主机，默认为 0.0.0.0
- `WEBUI_SECRET_KEY`: WebUI 密钥
- `WEBUI_JWT_SECRET_KEY`: JWT 密钥
- `WEB_LOADER_ENGINE`: Web 加载引擎（如设置为 "playwright" 将安装 Playwright）
- `PLAYWRIGHT_WS_URL`: Playwright WebSocket URL

例如：
```powershell
$env:PORT = "9000"
$env:HOST = "127.0.0.1"
.\setup_and_run.ps1
```

## 注意事项

1. 确保已安装 Python 3.11
2. 在 Windows 上运行时，可能需要先执行 `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` 来允许脚本执行
3. 首次运行时可能需要一些时间来安装依赖
4. 服务启动后，可以通过浏览器访问 `http://localhost:8080` 来使用 Open-WebUI

## 停止服务

按 `Ctrl+C` 可以停止服务。