"""
工作流测试脚本快速修复工具
解决WebSocket连接timeout参数问题和URL格式问题

问题原因：
1. websockets.connect()不支持timeout参数
2. WebSocket URL格式不正确
3. 配置文件JSON格式问题

修复内容：
1. 移除timeout参数
2. 修正WebSocket URL格式  
3. 修复配置文件格式
"""

import os
import json
import re
from pathlib import Path

def fix_websocket_timeout_issue():
    """修复WebSocket timeout参数问题"""
    print("🔧 开始修复WebSocket timeout参数问题...")
    
    files_to_fix = [
        "test_workflow_scenarios.py",
        "enhanced_workflow_tester.py"
    ]
    
    fixes_applied = 0
    
    for file_name in files_to_fix:
        file_path = Path(file_name)
        if not file_path.exists():
            print(f"⚠️ 文件不存在: {file_name}")
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 修复1: 移除websockets.connect中的timeout参数
            pattern1 = r'async with websockets\.connect\(([^,]+),\s*timeout=[^)]+\)'
            replacement1 = r'async with websockets.connect(\1)'
            content = re.sub(pattern1, replacement1, content)
            
            # 修复2: 修正WebSocket URL格式
            pattern2 = r'ws_url = f["\'].*?websocket_url.*?\{self\.user_id\}\?token=.*?["\']'
            replacement2 = 'ws_url = f"ws://localhost:8080/hsai/ws/{self.user_id}?token={self.token}"'
            content = re.sub(pattern2, replacement2, content)
            
            # 检查是否有修改
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 已修复: {file_name}")
                fixes_applied += 1
            else:
                print(f"ℹ️  无需修复: {file_name}")
                
        except Exception as e:
            print(f"❌ 修复失败 {file_name}: {e}")
    
    return fixes_applied

def fix_config_file():
    """修复配置文件格式问题"""
    print("🔧 检查配置文件格式...")
    
    config_file = Path("test_config.json")
    if not config_file.exists():
        print("⚠️ 配置文件不存在: test_config.json")
        return False
        
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # 检查是否缺少开头的大括号
        if not content.startswith('{'):
            content = '{' + content
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ 已修复配置文件格式")
            return True
        
        # 验证JSON格式
        json.loads(content)
        print("ℹ️  配置文件格式正确")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件JSON格式错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 配置文件检查失败: {e}")
        return False

def check_dependencies():
    """检查依赖包"""
    print("🔧 检查Python依赖包...")
    
    required_packages = [
        "websockets",
        "requests", 
        "asyncio"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}: 未安装")
    
    if missing_packages:
        print(f"\n缺少依赖包: {', '.join(missing_packages)}")
        print("安装命令: pip install " + " ".join(missing_packages))
        return False
    
    return True

def create_fixed_test_script():
    """创建修复后的测试脚本示例"""
    print("🔧 创建修复后的测试脚本示例...")
    
    fixed_script = '''"""
修复后的WebSocket测试示例
解决timeout参数问题
"""

import asyncio
import json
import websockets
import requests

async def test_websocket_fixed():
    """修复后的WebSocket测试"""
    
    # 1. 登录获取token
    login_data = {
        "email": "saiter2306@163.com",
        "password": "123456"
    }
    
    response = requests.post(
        "http://localhost:8080/api/v1/auths/signin",
        json=login_data
    )
    
    if response.status_code != 200:
        print("❌ 登录失败")
        return False
    
    result = response.json()
    token = result.get("token")
    user_id = result.get("id")
    
    print(f"✅ 登录成功，用户ID: {user_id}")
    
    # 2. 连接WebSocket（修复后的格式）
    ws_url = f"ws://localhost:8080/hsai/ws/{user_id}?token={token}"
    
    try:
        # 注意：移除了timeout参数
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket连接成功")
            
            # 发送测试消息
            test_message = {
                "type": "chat",
                "content": "Hello, 测试消息",
                "user_id": user_id,
                "entry_type": "chat",
                "session_id": f"test_{int(time.time())}",
                "metadata": {}
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 消息发送成功")
            
            # 等待响应
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            print(f"📥 收到响应: {response}")
            
            return True
            
    except Exception as e:
        print(f"❌ WebSocket测试失败: {e}")
        return False

if __name__ == "__main__":
    import time
    result = asyncio.run(test_websocket_fixed())
    print("✅ 测试完成" if result else "❌ 测试失败")
'''
    
    try:
        with open("fixed_websocket_test.py", 'w', encoding='utf-8') as f:
            f.write(fixed_script)
        print("✅ 创建修复示例: fixed_websocket_test.py")
        return True
    except Exception as e:
        print(f"❌ 创建示例失败: {e}")
        return False

def main():
    """主修复流程"""
    print("=" * 60)
    print("🛠️  工作流测试脚本快速修复工具")
    print("=" * 60)
    
    print("\n📋 修复内容:")
    print("1. WebSocket连接timeout参数问题")
    print("2. WebSocket URL格式问题")
    print("3. 配置文件JSON格式问题")
    print("4. 依赖包检查")
    
    print("\n🚀 开始修复...")
    
    # 检查依赖
    deps_ok = check_dependencies()
    
    # 修复脚本文件
    fixes_applied = fix_websocket_timeout_issue()
    
    # 修复配置文件
    config_ok = fix_config_file()
    
    # 创建修复示例
    example_created = create_fixed_test_script()
    
    print("\n" + "=" * 60)
    print("📊 修复结果总结")
    print("=" * 60)
    print(f"脚本文件修复: {fixes_applied} 个文件")
    print(f"配置文件: {'✅ 正常' if config_ok else '❌ 有问题'}")
    print(f"依赖包: {'✅ 完整' if deps_ok else '❌ 缺少'}")
    print(f"修复示例: {'✅ 已创建' if example_created else '❌ 创建失败'}")
    
    if fixes_applied > 0 or not deps_ok:
        print("\n🔄 建议重新运行测试脚本验证修复效果")
    
    if not deps_ok:
        print("\n⚠️  请先安装缺少的依赖包，然后重新运行测试")
    
    print("\n✨ 修复完成！")

if __name__ == "__main__":
    main()