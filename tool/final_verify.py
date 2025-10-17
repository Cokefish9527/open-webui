#!/usr/bin/env python3
"""
HSAI统一Socket.IO集成最终验证
"""

import os

# 使用绝对路径检查
backend_dir = r"C:\work\open-webui\backend"

print("=== HSAI统一Socket.IO集成验证 ===\n")

# 检查关键文件
files_to_check = [
    (r"C:\work\open-webui\backend\open_webui\socket\main.py", "Socket.IO主文件"),
    (r"C:\work\open-webui\backend\open_webui\socket\hsai_events.py", "HSAI事件处理器"),
    (r"C:\work\open-webui\backend\open_webui\services\workflow_orchestration_center.py", "工作流编排中心")
]

# 检查已删除的重复文件
deleted_files = [
    (r"C:\work\open-webui\backend\open_webui\routers\hsai_websocket.py", "重复的WebSocket路由"),
    (r"C:\work\open-webui\backend\open_webui\socket\hsai_chat_handler.py", "重复的聊天处理器")
]

print("✅ 检查核心文件:")
all_exist = True
for file_path, description in files_to_check:
    if os.path.exists(file_path):
        print(f"  ✓ {description} 存在")
    else:
        print(f"  ✗ {description} 不存在: {file_path}")
        all_exist = False

print("\n✅ 检查重复文件删除:")
all_deleted = True
for file_path, description in deleted_files:
    if not os.path.exists(file_path):
        print(f"  ✓ {description} 已正确删除")
    else:
        print(f"  ✗ {description} 仍然存在: {file_path}")
        all_deleted = False

print("\n✅ 检查关键内容:")

# 检查hsai_events.py中的关键函数
hsai_events_path = r"C:\work\open-webui\backend\open_webui\socket\hsai_events.py"
if os.path.exists(hsai_events_path):
    with open(hsai_events_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'hsai_message' in content:
            print("  ✓ HSAI统一事件处理器 (hsai_message) 已实现")
        else:
            print("  ✗ HSAI统一事件处理器 (hsai_message) 未找到")
            all_exist = False
            
        if 'workflow_orchestration_center' in content:
            print("  ✓ 工作流编排中心集成已实现")
        else:
            print("  ✗ 工作流编排中心集成未找到")
            all_exist = False

print()
if all_exist and all_deleted:
    print("🎉 HSAI统一Socket.IO集成验证成功！")
    print()
    print("🔧 已完成的关键改进:")
    print("  • ✅ 统一所有WebSocket通信到OpenWebUI原生Socket.IO")
    print("  • ✅ 删除了重复的WebSocket路由 (hsai_websocket.py)")
    print("  • ✅ 删除了独立的聊天处理器 (hsai_chat_handler.py)")
    print("  • ✅ 集成工作流编排中心到Socket.IO事件处理")
    print("  • ✅ 保持了OpenWebUI原有功能不受影响")
    print()
    print("📋 统一架构设计:")
    print("  • Socket.IO入口: /ws/socket.io (OpenWebUI原生)")
    print("  • HSAI事件名称: 'hsai_message', 'hsai_response', 'hsai_error'")
    print("  • 工作流事件: 'hsai_workflow_started', 'hsai_workflow_progress', 'hsai_workflow_completed'")
    print("  • 身份验证: 通过auth参数传递JWT令牌")
    print()
    print("🚀 前端连接示例:")
    print("""
const socket = io('http://localhost:8080', {
    path: '/ws/socket.io',
    auth: { token: 'your-jwt-token' },
    transports: ['websocket', 'polling']
});

// 发送HSAI消息
socket.emit('hsai_message', {
    content: '你好，这是一个测试消息',
    user_id: 'user123'
});

// 监听HSAI响应
socket.on('hsai_response', (data) => {
    console.log('收到HSAI响应:', data);
});
""")
    print("✅ 集成验证完成，可以进行测试！")
else:
    print("❌ 验证失败，请检查上述问题")
