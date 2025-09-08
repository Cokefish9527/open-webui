from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from open_webui.socket.hsai_chat_handler import chat_handler
from open_webui.utils.viral_learning_scheduler import viral_learning_scheduler
from open_webui.utils.auth import get_current_user as get_verified_user
from open_webui.models.users import Users

# 导入新的工作流集成模块
from open_webui.utils.n8n_workflow_manager import workflow_manager
from open_webui.utils.workflow_selector import workflow_selector, SelectionContext
from open_webui.utils.n8n_client import n8n_client, ExecutionRequest
from open_webui.utils.message_processor import message_processor

# 修改导入语句
from open_webui.env import WEBUI_SECRET_KEY as JWT_SECRET_KEY

import json
import logging
import jwt
import time
import asyncio
from typing import Dict, List, Optional

log = logging.getLogger(__name__)
router = APIRouter(tags=["HSAI WebSocket"])

@router.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    log.info("[应用启动] HSAI WebSocket路由器正在启动...")
    
    # 初始化工作流管理器
    await workflow_manager.initialize()
    log.info("[应用启动] 工作流管理器初始化完成")
    
    # 初始化N8N客户端
    await n8n_client.initialize()
    log.info("[应用启动] N8N客户端初始化完成")
    
    # 启动爆款学习工作流定时调度器
    await viral_learning_scheduler.start()
    log.info("[应用启动] 爆款学习调度器启动完成")

@router.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    log.info("[应用关闭] HSAI WebSocket路由器正在关闭...")
    
    # 关闭N8N客户端
    await n8n_client.close()
    log.info("[应用关闭] N8N客户端已关闭")
    
    # 停止爆款学习工作流定时调度器
    await viral_learning_scheduler.stop()
    log.info("[应用关闭] 爆款学习调度器已停止")

async def get_user_from_token(token: str):
    """从token获取用户信息"""
    try:
        log.info(f"[用户认证] 开始验证token: {token[:10]}...")
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("id")
        if user_id:
            user = Users.get_user_by_id(user_id)
            log.info(f"[用户认证] 用户认证成功: {user_id}")
            return user
    except Exception as e:
        log.error(f"[用户认证] Token验证失败: {e}", exc_info=True)
    return None

@router.websocket("/hsai/ws/{user_id}")
async def hsai_websocket_endpoint(
    websocket: WebSocket, 
    user_id: str,
    token: str = Query(...),
    session_id: str = Query(None)
):
    """
    HSAI WebSocket端点 - OpenWebUI与n8n协同核心
    
    实现客户端 ←→ WebSocket ←→ OpenWebUI ←→ n8n webhook 的完整协同流程
    
    Args:
        websocket: WebSocket连接对象
        user_id: 用户ID
        token: 认证token (通过query参数传递)
    
    协同流程:
        1. 客户端通过WebSocket连接到OpenWebUI
        2. 客户端发送对话消息
        3. OpenWebUI转发消息到n8n webhook
        4. n8n处理后返回结构化响应
        5. OpenWebUI处理响应并通过WebSocket返回客户端
    """
    
    log.info(f"[WebSocket连接] 收到用户 {user_id} 的WebSocket连接请求")
    
    # 验证用户身份
    if not token:
        log.warning(f"[身份验证] 用户 {user_id} 缺少认证token")
        await websocket.close(code=4001, reason="缺少认证token")
        return
    
    try:
        # 验证token并获取用户信息
        user = await get_user_from_token(token)
        if not user or user.id != user_id:
            log.warning(f"[身份验证] 用户 {user_id} 身份验证失败")
            await websocket.close(code=4003, reason="身份验证失败")
            return
            
        log.info(f"[身份验证] 用户 {user.name} ({user_id}) 身份验证成功")
        
    except Exception as e:
        log.error(f"[身份验证] 用户 {user_id} 身份验证过程中发生错误: {e}", exc_info=True)
        await websocket.close(code=4003, reason="身份验证失败")
        return
    
    # 建立WebSocket连接
    log.info(f"[WebSocket连接] 为用户 {user_id} 建立WebSocket连接")
    await chat_handler.connect(websocket, user_id)
    log.info(f"[WebSocket连接] 用户 {user_id} 的WebSocket连接建立成功")
    
    try:
        # 发送连接成功消息
        pass  # 消息已经在connect方法中发送
        
        while True:
            # 接收客户端消息
            try:
                data = await websocket.receive_text()
                log.info(f"[消息接收] 从用户 {user_id} 接收到原始消息: {data}")
                
                message_data = json.loads(data)
                log.info(f"[消息解析] 解析用户 {user_id} 的消息成功: {message_data.get('type', 'unknown')}")
                
                # 处理消息（包含完整的n8n协同逻辑）
                log.info(f"[消息处理] 开始处理用户 {user_id} 的消息")
                await chat_handler.handle_message(user_id, message_data)
                log.info(f"[消息处理] 用户 {user_id} 的消息处理完成")
                
            except json.JSONDecodeError as e:
                error_msg = f"用户 {user_id} 发送的消息JSON格式错误: {e}"
                log.error(f"[消息处理] {error_msg}", exc_info=True)
                error_response = {
                    "type": "error",
                    "content": "消息JSON格式错误",
                    "timestamp": time.time()
                }
                log.info(f"[错误响应] 发送错误响应给用户 {user_id}: {error_response}")
                await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                
            except Exception as e:
                error_msg = f"处理用户 {user_id} 的消息时发生错误: {str(e)}"
                log.error(f"[消息处理] {error_msg}", exc_info=True)
                error_response = {
                    "type": "error",
                    "content": f"消息处理失败: {str(e)}",
                    "timestamp": time.time()
                }
                log.info(f"[错误响应] 发送错误响应给用户 {user_id}: {error_response}")
                await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                
    except WebSocketDisconnect:
        log.info(f"[WebSocket断开] 用户 {user_id} 的WebSocket连接已断开")
    except Exception as e:
        log.error(f"[WebSocket错误] 用户 {user_id} 的WebSocket连接发生错误: {e}", exc_info=True)
    finally:
        log.info(f"[WebSocket清理] 清理用户 {user_id} 的WebSocket连接")
        await chat_handler.disconnect(user_id)

@router.get("/hsai/ws/status")
async def websocket_status():
    """获取WebSocket服务状态"""
    from open_webui.utils.n8n_monitor import n8n_monitor
    
    active_users = chat_handler.get_active_users()
    system_health = n8n_monitor.get_system_health()
    
    status_data = {
        "status": "running",
        "active_connections": len(active_users),
        "active_users": active_users,
        "total_sessions": len(chat_handler.user_sessions),
        "n8n_health": system_health
    }
    log.info(f"[状态查询] WebSocket服务状态: {status_data}")
    return status_data

@router.get("/hsai/ws/sessions/{session_id}/users")
async def get_session_users(session_id: str):
    """获取指定会话的活跃用户"""
    users = chat_handler.get_session_users(session_id)
    session_data = {
        "session_id": session_id,
        "active_users": users,
        "user_count": len(users)
    }
    log.info(f"[会话查询] 会话 {session_id} 的活跃用户: {session_data}")
    return session_data

@router.post("/hsai/ws/broadcast/{session_id}")
async def broadcast_to_session(
    session_id: str,
    message: dict,
    user=Depends(get_verified_user)
):
    """向指定会话广播消息"""
    try:
        log.info(f"[消息广播] 准备向会话 {session_id} 广播消息: {message}")
        # 添加发送者信息
        broadcast_message = {
            **message,
            "sender_id": user.id,
            "sender_name": user.name,
            "timestamp": time.time()
        }
        
        await chat_handler.broadcast_to_session(session_id, broadcast_message)
        
        response_data = {
            "status": "success",
            "session_id": session_id,
            "message_sent": True
        }
        log.info(f"[消息广播] 广播消息发送成功: {response_data}")
        return response_data
        
    except Exception as e:
        error_msg = f"向会话 {session_id} 广播消息失败: {str(e)}"
        log.error(f"[消息广播] {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"广播失败: {str(e)}"
        )

@router.get("/hsai/ws/health")
async def get_n8n_health():
    """获取n8n工作流健康状态"""
    from open_webui.utils.n8n_monitor import n8n_monitor
    
    health_data = n8n_monitor.get_system_health()
    log.info(f"[健康检查] n8n工作流健康状态: {health_data}")
    return health_data

@router.get("/hsai/ws/health/{workflow_type}")
async def get_workflow_health(workflow_type: str):
    """获取特定工作流健康状态"""
    from open_webui.utils.n8n_monitor import n8n_monitor
    from open_webui.config.n8n_workflows import N8NWorkflowType
    
    try:
        wf_type = N8NWorkflowType(workflow_type)
        health_data = n8n_monitor.get_workflow_health(wf_type)
        log.info(f"[健康检查] 工作流 {workflow_type} 健康状态: {health_data}")
        return health_data
    except ValueError:
        error_msg = f"无效的工作流类型: {workflow_type}"
        log.warning(f"[健康检查] {error_msg}")
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )

@router.post("/hsai/ws/cleanup")
async def cleanup_monitoring_data(
    max_age_hours: int = 24,
    user=Depends(get_verified_user)
):
    """清理监控数据（需要管理员权限）"""
    from open_webui.utils.n8n_monitor import n8n_monitor
    
    # 这里可以添加管理员权限检查
    # if not user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    log.info(f"[数据清理] 开始清理 {max_age_hours} 小时前的监控数据")
    n8n_monitor.cleanup_old_data(max_age_hours)
    
    response_data = {
        "status": "success",
        "message": f"已清理 {max_age_hours} 小时前的监控数据"
    }
    log.info(f"[数据清理] 监控数据清理完成: {response_data}")
    return response_data