# Python版本锁定说明

## 目标
确保项目始终在Python 3.11环境下运行，防止因Python版本不兼容导致的问题。

## 当前环境状态
- Python版本: 3.11.9
- 虚拟环境路径: `D:\Work\hsch\open-webui\venv`
- 系统路径中Python 3.11位置: `C:\Users\bmkz\AppData\Local\Programs\Python\Python311\python.exe`

## 锁定措施

### 1. 环境变量设置
在系统环境变量中设置Python路径优先级，确保使用Python 3.11:
```
PATH = C:\Users\bmkz\AppData\Local\Programs\Python\Python311;C:\Users\bmkz\AppData\Local\Programs\Python\Python311\Scripts;...
```

### 2. 虚拟环境隔离
项目使用独立的虚拟环境，避免与系统其他Python项目冲突:
```bash
# 激活虚拟环境
.\venv\Scripts\Activate.ps1
```

### 3. 版本检查脚本
项目中包含版本检查脚本，确保运行时Python版本正确:
- [check_python_version.py](file:///D:/Work/hsch/open-webui/check_python_version.py) - 启动服务前检查Python版本

### 4. 依赖管理
所有依赖包都安装在虚拟环境中，与系统Python环境隔离。

## 恢复步骤

如果需要重新配置环境，请按以下步骤操作:

1. 删除现有虚拟环境:
   ```powershell
   Remove-Item -Recurse -Force .\venv
   ```

2. 使用Python 3.11创建新的虚拟环境:
   ```powershell
   C:\Users\bmkz\AppData\Local\Programs\Python\Python311\python.exe -m venv venv
   ```

3. 激活虚拟环境:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

4. 升级pip:
   ```powershell
   python -m pip install --upgrade pip
   ```

5. 安装项目依赖:
   ```powershell
   cd backend
   pip install -r requirements.txt
   ```

## 注意事项
1. 不要修改系统Python版本
2. 不要在系统Python环境中安装项目依赖
3. 启动服务前务必激活虚拟环境
4. 定期检查Python版本以确保环境正确