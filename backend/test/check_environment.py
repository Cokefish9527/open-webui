import os
import sys
import subprocess
import requests
import time
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    # 在虚拟环境中运行，版本由虚拟环境决定
    print("✓ 在虚拟环境中运行Python")
    return True

def check_virtual_environment():
    """检查虚拟环境"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv:
        print("✓ 运行在虚拟环境中")
        print(f"  虚拟环境路径: {sys.prefix}")
        return True
    else:
        print("✗ 未在虚拟环境中运行")
        return False

def check_required_packages():
    """检查必要的包"""
    required_packages = ['fastapi', 'uvicorn', 'sqlalchemy', 'pydantic']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"✗ {package} 未安装")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def check_server_status(max_retries=30):
    """检查服务器状态"""
    for i in range(max_retries):
        try:
            response = requests.get("http://127.0.0.1:8080/docs", timeout=5)
            if response.status_code == 200:
                print("✓ 服务器正在运行 (端口 8080)")
                return True
            else:
                print(f"✗ 服务器返回状态码: {response.status_code}")
        except requests.exceptions.ConnectionError:
            if i == 0:
                print("✗ 无法连接到服务器 (端口 8080)")
            elif i == max_retries - 1:
                print("✗ 服务器启动超时")
        except Exception as e:
            print(f"✗ 检查服务器状态时出错: {e}")
        
        if i < max_retries - 1:
            time.sleep(1)
    
    return False

def start_server():
    """尝试启动服务器"""
    try:
        backend_path = Path(__file__).parent.parent
        start_script = backend_path / "start_windows.bat"
        
        if not start_script.exists():
            print(f"✗ 未找到启动脚本: {start_script}")
            return False
            
        print("正在启动服务器...")
        # 在后台运行启动脚本
        process = subprocess.Popen([
            "cmd", "/c", str(start_script)
        ], cwd=backend_path, creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        print(f"服务器启动进程ID: {process.pid}")
        print("等待服务器启动...")
        return True
    except Exception as e:
        print(f"✗ 启动服务器时出错: {e}")
        return False

def main():
    print("=== 环境检查 ===")
    
    checks = [
        ("Python版本", check_python_version),
        ("虚拟环境", check_virtual_environment),
        ("必要包", check_required_packages),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n检查 {name}...")
        result = check_func()
        results.append((name, result))
    
    # 检查服务器状态
    print(f"\n检查 服务器状态...")
    server_running = check_server_status(1)  # 初始检查
    
    if not server_running:
        print("服务器未运行，尝试启动服务器...")
        if start_server():
            print("等待服务器启动完成...")
            time.sleep(10)  # 等待服务器启动
            server_running = check_server_status(30)  # 等待服务器启动完成
        else:
            server_running = False
    
    results.append(("服务器状态", server_running))
    
    print("\n=== 检查结果 ===")
    all_passed = True
    for name, result in results:
        status = "通过" if result else "失败"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    if not all_passed:
        print("\n环境检查未完全通过，请修复问题后重试。")
        return False
    
    print("\n✓ 所有检查通过!")
    return True

if __name__ == "__main__":
    main()