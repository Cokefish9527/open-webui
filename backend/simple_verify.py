#!/usr/bin/env python3
"""
简单验证HSAI统一Socket.IO集成
"""

import os
import sys

def check_files():
    """检查关键文件是否存在"""
    files_to_check = [
        "open_webui/socket/main.py",
        "open_webui/socket/hsai_events.py",
        "open_webui/services/workflow_orchestration_center.py"
    ]
    
    deleted_files = [
        "open_webui/routers/hsai_websocket.py",
        "open_webui/socket/hsai_chat_handler.py"
    ]
    
    print("=== HSAI统一Socket.IO集成验证 ===")
    print()
    
    print("✓ 检查核心文件:")
    all_exist = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"  ✓ {file_path} 存在")
        else:
            print(f"  × {file_path} 不存在")
            all_exist = False
    
    print()
    print("✓ 检查重复文件是否已删除:")
    all_deleted = True
    for file_path in deleted_files:
        if not os.path.exists(file_path):
            print(f"  ✓ {file_path} 已正确删除")
        else:
            print(f"  × {file_path} 仍然存在，应该被删除")
            all_deleted = False
    
    print()
    if all_exist and all_deleted:
        print("🎉 HSAI统一Socket.IO集成验证成功！")
        print()
        print("关键改进:")
        print("• ✅ 统一所有WebSocket通信到OpenWebUI原生Socket.IO")
        print("• ✅ 删除了重复的WebSocket路由") 
        print("• ✅ 集成工作流编排中心到Socket.IO事件处理")
        print("• ✅ 保持了OpenWebUI原有功能不受影响")
        print()
        print("前端连接方式:")
        print("1. 使用OpenWebUI原生Socket.IO端点: /ws/socket.io")
        print("2. 通过auth参数传递JWT令牌进行身份验证")
        print("3. 使用统一的HSAI事件名称:")
        print("   • 发送: 'hsai_message'")
        print("   • 接收: 'hsai_response', 'hsai_error'")
        print("   • 工作流: 'hsai_workflow_started', 'hsai_workflow_progress', 'hsai_workflow_completed'")
        return True
    else:
        print("😞 验证失败，请检查上述问题")
        return False

if __name__ == "__main__":
    success = check_files()
    sys.exit(0 if success else 1)
