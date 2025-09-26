#!/usr/bin/env python3
"""
更新后的WebSocket连接测试脚本
验证端口改为8080后的连接
"""

import asyncio
import websockets
import json
import time
import jwt
import os
import sys
from typing import Dict, Any
import requests

# 添加项目路径到sys.path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# 使用与后端服务相同的密钥
JWT_SECRET_KEY = "t0p-s3cr3t"  # 默认密钥，与后端配置中的WEBUI_SECRET_KEY一致

# 测试用户信息
TEST_USER = {
    "id": "test_user_001",
    "name": "Test User",
    "email": "test@example.com"
}

def generate_test_token(user_id: str) -> str:
    """生成测试用JWT令牌"""
    payload = {
        "id": user_id,
        "exp": int(time.time()) + 3600,  # 1小时过期
        "iat": int(time.time())
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

async def test_websocket_workflow():
    """测试WebSocket工作流端到端流程"""
    print("=" * 60)
    print("开始WebSocket工作流端到端测试 (端口8080)")
    print("=" * 60)
    
    # 1. 生成测试令牌
    token = generate_test_token(TEST_USER["id"])
    print(f"[1/3] 生成测试令牌: {token[:20]}...")
    
    # 2. 连接到WebSocket服务器 (使用更新后的端口8080)
    websocket_url = "ws://localhost:8080/api/v1/ws/hsai/" + TEST_USER["id"]
    query_params = f"?token={token}"
    
    try:
        print(f"[2/3] 连接到WebSocket服务器: {websocket_url}")
        async with websockets.connect(websocket_url + query_params) as websocket:
            print("✓ WebSocket连接建立成功")
            
            # 等待连接确认消息
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                connection_msg = json.loads(response)
                print(f"  ← 接收到连接确认消息: {connection_msg.get('content', 'N/A')}")
                
                # 显示可用的工作流
                if 'available_workflows' in connection_msg:
                    print("  可用工作流:")
                    for workflow in connection_msg['available_workflows']:
                        print(f"    - {workflow['name']}: {workflow['description']}")
            except asyncio.TimeoutError:
                print("  ← 等待连接确认消息超时")
            
            # 3. 发送测试消息
            import uuid
            test_message = {
                "type": "chat",
                "content": "测试WebSocket连接",
                "user_id": login_result.get("id"),  # 使用登录返回的用户ID
                "entry_type": "chat",
                "session_id": f"test_session_{uuid.uuid4().hex[:8]}",  # 使用UUID而不是时间戳
                "timestamp": int(time.time())
            }
            
            print(f"\n[3/4] 发送测试消息: {test_message['content']}")
            
            # 发送消息
            await websocket.send(json.dumps(test_message, ensure_ascii=False))
            print("  → 消息发送成功")
            
            # 等待并接收响应
            try:
                print("  ← 等待工作流响应...")
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                response_data = json.loads(response)
                print(f"  ← 接收到工作流响应:")
                print(f"    类型: {response_data.get('messageType', 'N/A')}")
                print(f"    状态: {response_data.get('status', 'N/A')}")
                print(f"    内容: {response_data.get('displayText', 'N/A')[:100]}...")
                
                # 检查响应结构是否符合华商AI工作流前端对接规范
                required_fields = ['success', 'messageType', 'displayText', 'data', 'status']
                missing_fields = [field for field in required_fields if field not in response_data]
                if missing_fields:
                    print(f"    ⚠ 警告: 响应缺少字段 {missing_fields}")
                else:
                    print(f"    ✓ 响应结构符合规范")
                        
            except asyncio.TimeoutError:
                print("  ← 等待响应超时（30秒）")
            except json.JSONDecodeError as e:
                print(f"  ← 响应解析失败: {e}")
            except Exception as e:
                print(f"  ← 接收响应时出错: {e}")
            
            print("\n测试完成，关闭WebSocket连接")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"✗ WebSocket连接失败，状态码: {e.status_code}")
        if e.status_code == 403:
            print("  可能原因: 认证失败，请检查JWT令牌配置")
        elif e.status_code == 404:
            print("  可能原因: WebSocket端点不存在，请检查服务器配置")
    except Exception as e:
        print(f"✗ WebSocket连接异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("华商AI WebSocket连接测试 (端口8080)")
    print("确保后端服务已在8080端口启动")
    
    # 测试WebSocket端到端流程
    asyncio.run(test_websocket_workflow())
    
    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)