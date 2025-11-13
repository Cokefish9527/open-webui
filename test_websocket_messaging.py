import asyncio
import websockets
import json
import time
import requests
import uuid

async def test_websocket_messaging(site_name, site_url):
    print(f"\n=== 测试 {site_name} ({site_url}) 的WebSocket消息传递 ===")
    
    try:
        # 连接到WebSocket服务器
        ws_url = 'ws://localhost:8080/ws/socket.io/?EIO=4&transport=websocket'
        print(f"[{site_name}] 连接WebSocket服务器: {ws_url}")
        
        async with websockets.connect(ws_url, timeout=10) as websocket:
            print(f"[{site_name}] WebSocket连接成功")
            
            # 等待初始消息
            initial_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"[{site_name}] 收到初始消息: {initial_msg}")
            
            # 发送连接消息（模拟认证）
            # 注意：这里使用测试token，实际环境中需要有效的认证token
            auth_msg = '40{"token":"test_token_' + str(uuid.uuid4())[:8] + '"}'
            await websocket.send(auth_msg)
            print(f"[{site_name}] 发送认证消息: {auth_msg}")
            
            # 等待认证响应
            response_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"[{site_name}] 收到认证响应: {response_msg}")
            
            # 发送测试消息
            session_id = f"test_session_{uuid.uuid4().hex[:8]}"
            test_message = {
                "type": "chat",
                "content": f"测试消息 from {site_name}",
                "user_id": f"test_user_{site_name.lower().replace(' ', '_')}",
                "session_id": session_id,
                "entry_type": "chat",
                "timestamp": int(time.time())
            }
            
            # Socket.IO格式的消息: 42表示MESSAGE事件，后面跟着JSON数据
            message_packet = f'42["message", {json.dumps(test_message, ensure_ascii=False)}]'
            await websocket.send(message_packet)
            print(f"[{site_name}] 发送测试消息: {message_packet}")
            
            # 等待响应（设置较长的超时时间）
            print(f"[{site_name}] 等待响应消息...")
            start_time = time.time()
            response_received = False
            
            while time.time() - start_time < 15:  # 15秒超时
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    print(f"[{site_name}] 收到消息: {response}")
                    
                    # 检查是否为HSAI响应
                    response_str = str(response)
                    if 'hsai_response' in response_str or 'hsai_error' in response_str:
                        print(f"[{site_name}] 收到HSAI响应消息!")
                        response_received = True
                        break
                    elif response_str.startswith('42'):  # Socket.IO MESSAGE事件
                        print(f"[{site_name}] 收到Socket.IO消息事件")
                        response_received = True
                        break
                        
                except asyncio.TimeoutError:
                    continue  # 继续等待
            
            if response_received:
                print(f"[{site_name}] ✓ 成功收到响应消息")
            else:
                print(f"[{site_name}] ✗ 未在15秒内收到响应消息")
                
    except Exception as e:
        print(f"[{site_name}] WebSocket测试出错: {str(e)}")
        print(f"[{site_name}] 错误类型: {type(e).__name__}")

async def main():
    print("开始测试两个前端站点的WebSocket消息传递")
    
    # 测试两个站点
    await test_websocket_messaging('站点1', 'http://192.168.20.62:5173')
    await test_websocket_messaging('站点2', 'http://192.168.20.62:5174')
    
    print('\n测试完成')

if __name__ == "__main__":
    asyncio.run(main())