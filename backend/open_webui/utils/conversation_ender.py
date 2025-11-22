"""
通用对话结束机制
提供统一的接口来结束对话并通知客户端
"""

import logging
from typing import Optional, Dict, Any

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


async def end_conversation(
    user_id: str,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    message: str = "对话已结束",
    reason: str = "task_completed"
) -> bool:
    """
    结束对话并通知客户端
    
    Args:
        user_id: 用户ID
        session_id: 会话ID（可选）
        task_id: 任务ID（可选）
        message: 结束消息
        reason: 结束原因
        
    Returns:
        bool: 是否成功发送结束通知
    """
    try:
        # 导入Socket.IO相关模块
        from open_webui.socket.main import sio, USER_POOL, SESSION_POOL, SESSION_ID_TO_SID
        
        if sio is None:
            log.warning("Socket.IO未初始化，无法发送对话结束通知")
            return False
            
        # 构建对话结束消息
        end_message = {
            "type": "conversation_ended",
            "success": True,
            "message": message,
            "reason": reason,
            "task_id": task_id,
            "session_id": session_id,
            "timestamp": int(__import__('time').time() * 1000)
        }
        
        # 确定发送目标
        target_sids = []
        
        # 如果提供了session_id，尝试找到对应的SID
        if session_id:
            # 首先尝试通过SESSION_ID_TO_SID映射查找
            if SESSION_ID_TO_SID:
                sid = SESSION_ID_TO_SID.get(session_id)
                if sid:
                    target_sids.append(sid)
                else:
                    # 回退到遍历SESSION_POOL的方式
                    if hasattr(SESSION_POOL, 'items'):
                        for sid, session_data in SESSION_POOL.items():
                            if isinstance(session_data, dict) and session_data.get("session_id") == session_id:
                                target_sids.append(sid)
                                break
        
        # 如果没有通过session_id找到SID，尝试通过user_id查找
        if not target_sids and user_id:
            if isinstance(USER_POOL, dict):
                user_sids = USER_POOL.get(user_id, [])
            else:
                user_sids = USER_POOL.get(user_id, [])
                # 如果是awaitable，需要await
                if user_sids is not None and hasattr(user_sids, '__await__'):
                    # 在同步函数中无法await，回退到遍历SESSION_POOL的方式
                    user_sids = []
                # 确保user_sids是列表类型
                if not isinstance(user_sids, list):
                    user_sids = []
            
            # 验证SID是否仍然有效（在SESSION_POOL中存在）
            for sid in user_sids:
                if sid in SESSION_POOL:
                    target_sids.append(sid)
        
        # 如果找到了目标SID，发送对话结束消息
        if target_sids:
            for sid in target_sids:
                try:
                    await sio.emit("hsai_response", end_message, to=sid)
                    log.info(f"已发送对话结束通知到SID {sid}: user_id={user_id}, session_id={session_id}")
                except Exception as e:
                    log.error(f"发送对话结束通知到SID {sid}时发生错误: {e}")
            return True
        else:
            log.warning(f"未找到用户 {user_id} 的活动连接，无法发送对话结束通知")
            return False
            
    except Exception as e:
        log.error(f"结束对话时发生错误: {e}", exc_info=True)
        return False


async def end_conversation_for_task_completion(
    user_id: str,
    task_id: str,
    session_id: Optional[str] = None,
    task_type: str = "unknown"
) -> bool:
    """
    当任务完成时结束对话
    
    Args:
        user_id: 用户ID
        task_id: 任务ID
        session_id: 会话ID（可选）
        task_type: 任务类型
        
    Returns:
        bool: 是否成功发送结束通知
    """
    message = f"{task_type}任务已完成，对话结束"
    return await end_conversation(
        user_id=user_id,
        session_id=session_id,
        task_id=task_id,
        message=message,
        reason="task_completed"
    )


# 兼容旧版本的函数名
async def notify_conversation_end(
    user_id: str,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    message: str = "对话已结束"
) -> bool:
    """
    通知对话结束（兼容旧版本）
    
    Args:
        user_id: 用户ID
        session_id: 会话ID（可选）
        task_id: 任务ID（可选）
        message: 结束消息
        
    Returns:
        bool: 是否成功发送结束通知
    """
    return await end_conversation(user_id, session_id, task_id, message, "notified")