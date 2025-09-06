# Python 版本升级指南

本项目要求使用 Python 3.11+ 版本。如果您当前的 Python 版本低于此要求，请按照以下步骤进行升级。

## 自动升级脚本

我们提供了自动升级脚本，可以帮助您完成 Python 版本升级和环境重新设置：

### 1. 运行升级和设置脚本

```powershell
# 在项目根目录下执行
.\upgrade_and_setup.ps1
```

该脚本将：
1. 检查当前 Python 版本
2. 如果版本低于 3.11，则自动下载并安装 Python 3.11
3. 删除旧的虚拟环境
4. 创建新的虚拟环境
5. 安装项目依赖

### 2. 仅升级 Python 脚本

如果您只想升级 Python 而不重新设置环境：

```powershell
# 在项目根目录下执行
.\upgrade_python.ps1
```

## 手动升级步骤

如果您更喜欢手动升级，可以按照以下步骤操作：

### 1. 下载 Python 3.11

访问 [Python 官方下载页面](https://www.python.org/downloads/release/python-3119/) 下载适用于 Windows 的安装程序。

### 2. 安装 Python 3.11

运行下载的安装程序，确保选择以下选项：
- 添加 Python 到环境变量 PATH
- 安装 pip

### 3. 验证安装

打开新的 PowerShell 窗口并运行：

```powershell
python --version
```

您应该看到类似 `Python 3.11.9` 的输出。

### 4. 重新创建虚拟环境

```powershell
# 删除旧的虚拟环境
Remove-Item ".\venv" -Recurse -Force

# 创建新的虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 升级 pip
python -m pip install --upgrade pip

# 安装依赖
cd backend
pip install -r requirements.txt
```

## 注意事项

1. 升级 Python 后，您需要重新创建虚拟环境
2. 安装过程中可能会出现用户账户控制(UAC)提示，请允许操作
3. 升级完成后，建议重新启动 PowerShell 窗口
4. 如果您使用 IDE，请确保它指向新的 Python 解释器

## 常见问题

### Q: 升级后仍然显示旧版本的 Python
A: 请重新启动 PowerShell 窗口，或手动刷新环境变量：
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

### Q: 虚拟环境激活失败
A: 确保 PowerShell 执行策略允许脚本执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```