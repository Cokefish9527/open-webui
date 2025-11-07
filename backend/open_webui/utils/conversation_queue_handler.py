"""
对话消息队列处理器
处理来自n8n工作流的对话消息，通过Socket.IO通知客户端
"""

import asyncio
import json
import logging
import os
import time
from collections import deque
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from open_webui.env import SRC_LOG_LEVELS, REDIS_URL
# 延迟导入，在函数内部导入Socket.IO相关模块
# from open_webui.socket.main import sio, SESSION_POOL, USER_POOL
# 延迟导入，在函数内部导入Redis客户端
# from open_webui.utils.redis_queue_listener import get_redis_client
from open_webui.utils.robust_json_parser import robust_json_parse, reformat_for_frontend
from open_webui.services.blueprint_sync_service import (
    sync_blueprint_for_user,
    BlueprintSyncResult,
)
from open_webui.services.task_template_registry import task_template_registry

# 配置日志
log = logging.getLogger(__name__)
# 强制设置日志级别为DEBUG，便于调试
log.setLevel(logging.DEBUG)

BLUEPRINT_SYNC_DEBOUNCE_SECONDS = int(os.environ.get("BLUEPRINT_SYNC_DEBOUNCE_SECONDS", "20"))
BLUEPRINT_SYNC_TOKEN_TTL_SECONDS = int(os.environ.get("BLUEPRINT_SYNC_TOKEN_TTL_SECONDS", "300"))
BLUEPRINT_SYNC_TOKEN_CACHE_SIZE = int(os.environ.get("BLUEPRINT_SYNC_TOKEN_CACHE_SIZE", "256"))

_RECENT_BLUEPRINT_SYNC_TS: Dict[str, float] = {}
_RECENT_BLUEPRINT_TOKENS: Dict[str, float] = {}
_RECENT_BLUEPRINT_TOKEN_QUEUE: deque = deque()
_BLUEPRINT_LOCKS: Dict[str, asyncio.Lock] = {}


def get_redis_client():
    """获取Redis客户端实例"""
    # 延迟导入Redis模块
    import redis
    # 使用项目配置的Redis连接信息
    return redis.from_url(REDIS_URL)


async def handle_conversation_agent_message(message: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> None:
    """
    处理对话代理消息队列中的消息
    按照服务端消息结构规范文档重新封装消息并发送给前端
    
    Args:
        message: 从Redis队列中获取的消息数据
        config: 配置信息（可选）
    """
    try:
        # 延迟导入Socket.IO相关模块
        from open_webui.socket.main import SESSION_POOL, USER_POOL, sio
        # 导入用户模型
        from open_webui.models.users import Users
        
        log.info(f"处理对话代理消息: session_id={message.get('session_id')}, status={message.get('status')}")
        log.debug(f"完整消息内容: {message}")
        
        # 获取消息关键字段
        session_id = message.get("session_id")
        socket_id = message.get("socket_id")  # 优先使用socket_id
        status = message.get("status", "FINISHED")
        reply_id = message.get("reply_id")
        operate_id = message.get("operate_id")
        user_id = message.get("user_id", "")  # 提取user_id
        content_type = message.get("content_type", "")

        blueprint_sync_result: Optional[BlueprintSyncResult] = None
        if content_type == "blue_image_content" and status == "FINISHED" and user_id:
            dedupe_token = _extract_blueprint_token(message)
            should_skip, skip_reason = _should_skip_blueprint_sync(user_id, dedupe_token)
            if should_skip:
                log.info(
                    "[BlueprintSync] 跳过 user_id=%s reason=%s token=%s",
                    user_id,
                    skip_reason,
                    dedupe_token,
                )
            else:
                lock = _get_blueprint_lock(user_id)
                async with lock:
                    should_skip, skip_reason = _should_skip_blueprint_sync(user_id, dedupe_token)
                    if should_skip:
                        log.info(
                            "[BlueprintSync] 跳过 user_id=%s reason=%s token=%s",
                            user_id,
                            skip_reason,
                            dedupe_token,
                        )
                    else:
                        blueprint_sync_result = await _run_blueprint_sync(
                            message,
                            user_id=user_id,
                            dedupe_token=dedupe_token,
                        )
        
        # 检查是否是信息收集完成的消息 (blue_image类型且状态为FINISHED)
        if content_type == "blue_image" and status == "FINISHED" and user_id:
            log.info(f"检测到信息收集完成消息，更新用户 {user_id} 的信息收集状态")
            # 更新用户信息收集完成状态
            Users.update_user_info_collection_status(user_id, True)
            # 触发一次企业/默认项目/主线任务的幂等补种
            try:
                from open_webui.services.onboarding_orchestrator import ensure_company_project_and_main_tasks
                summary = ensure_company_project_and_main_tasks(user_id)
                log.info(f"Onboarding orchestrator summary: {summary}")
            except Exception as e:
                log.error(f"执行 Onboarding Orchestrator 时发生错误: {e}")
        
        # 查找对应的Socket.IO连接，按照socket_id->session_id->user_id的顺序
        target_sid = None
        
        # 1. 优先尝试通过socket_id查找
        if socket_id:
            log.debug(f"尝试通过socket_id {socket_id} 查找Socket.IO连接")
            if socket_id in SESSION_POOL:
                target_sid = socket_id
                log.info(f"通过socket_id {socket_id} 找到匹配的Socket.IO连接")
            else:
                log.warning(f"未找到socket_id {socket_id} 对应的Socket.IO连接")
        
        # 2. 如果通过socket_id找不到，尝试通过session_id查找
        if not target_sid and session_id:
            log.debug(f"尝试通过session_id {session_id} 查找Socket.IO连接")
            target_sid = _find_socket_by_session_id(session_id, SESSION_POOL)
            
        # 3. 如果通过session_id找不到，尝试使用user_id查找
        if not target_sid and user_id:
            log.warning(f"未找到session_id {session_id} 对应的Socket.IO连接，尝试通过user_id {user_id} 查找")
            target_sid = _find_socket_by_user_id(user_id, USER_POOL, SESSION_POOL)
            
        if not target_sid:
            # 添加更多调试信息
            log.warning(f"未找到socket_id {socket_id}、session_id {session_id} 或 user_id {user_id} 对应的Socket.IO连接")
            # 记录当前SESSION_POOL中的所有session_id
            try:
                if hasattr(SESSION_POOL, 'items'):
                    existing_session_ids = []
                    for sid, session_data in SESSION_POOL.items():
                        if isinstance(session_data, dict) and session_data.get("session_id"):
                            existing_session_ids.append(f"{session_data.get('session_id')}->{sid}")
                    log.debug(f"当前SESSION_POOL中的session_id映射: {existing_session_ids}")
                else:
                    log.debug("SESSION_POOL不是dict类型，无法遍历")
            except Exception as e:
                log.error(f"记录SESSION_POOL信息时发生错误: {e}")
            return
            
        # Reformat message for frontend rendering
        frontend_message = reformat_for_frontend(message)
        
        if sio is not None and blueprint_sync_result and blueprint_sync_result.notifications:
            emit_targets = []
            if target_sid:
                emit_targets.append(target_sid)
            elif user_id:
                fallback_sid = _find_socket_by_user_id(user_id, USER_POOL, SESSION_POOL)
                if fallback_sid:
                    emit_targets.append(fallback_sid)
            if not emit_targets:
                log.debug("Blueprint notifications could not find an active Socket.IO target.")
            else:
                for notification in blueprint_sync_result.notifications:
                    for sid in emit_targets:
                        try:
                            await sio.emit(notification.event, notification.payload, to=sid)
                            log.debug(
                                "Blueprint notification sent event=%s target=%s",
                                notification.event,
                                sid,
                            )
                        except Exception as emit_exc:
                            log.error(
                                "Failed to emit blueprint notification: %s",
                                emit_exc,
                                exc_info=True,
                            )
        
        # Send packaged message back to frontend
        if sio is not None:
            await sio.emit("hsai_response", frontend_message, to=target_sid)
            log.info(
                "Dispatched packaged message to frontend: session_id=%s, status=%s",
                session_id,
                status,
            )
        else:
            log.error("Socket.IO is not initialized")
        
    except Exception as e:
        log.error(f"处理对话代理消息时发生错误: {e}", exc_info=True)
        raise


def _find_socket_by_session_id(session_id: str, SESSION_POOL) -> Optional[str]:
    """
    根据session_id查找对应的Socket.IO连接ID
    直接使用前端传递的session_id来维持会话
    """
    try:
        # 延迟导入Socket.IO相关模块
        from open_webui.socket.main import SESSION_ID_TO_SID
        
        log.debug(f"开始查找session_id {session_id} 对应的Socket.IO连接")
        
        # 首先尝试通过SESSION_ID_TO_SID映射查找
        if SESSION_ID_TO_SID:
            log.debug("尝试通过SESSION_ID_TO_SID映射查找")
            if isinstance(SESSION_ID_TO_SID, dict):
                sid = SESSION_ID_TO_SID.get(session_id)
                if sid:
                    log.info(f"通过SESSION_ID_TO_SID找到匹配的Socket.IO连接: {sid} 对应 session_id: {session_id}")
                    return sid
                else:
                    log.debug(f"SESSION_ID_TO_SID中未找到session_id {session_id}")
            else:
                # 对于RedisDict，需要特殊处理
                try:
                    log.debug("SESSION_ID_TO_SID是RedisDict类型，尝试获取")
                    sid = SESSION_ID_TO_SID.get(session_id)
                    if hasattr(sid, '__await__'):
                        # 这是一个异步操作，但在同步函数中无法处理
                        # 回退到遍历SESSION_POOL的方式
                        log.debug("SESSION_ID_TO_SID返回异步对象，回退到遍历SESSION_POOL方式")
                        pass
                    elif sid:
                        log.info(f"通过SESSION_ID_TO_SID找到匹配的Socket.IO连接: {sid} 对应 session_id: {session_id}")
                        return sid
                    else:
                        log.debug(f"SESSION_ID_TO_SID中未找到session_id {session_id}")
                except Exception as e:
                    log.error(f"通过SESSION_ID_TO_SID查找时发生异常: {e}")
                    # 如果无法通过SESSION_ID_TO_SID查找，回退到遍历SESSION_POOL的方式
                    pass
        
        # 如果通过SESSION_ID_TO_SID找不到，回退到遍历SESSION_POOL的方式
        log.debug("回退到遍历SESSION_POOL方式查找")
        # 直接遍历SESSION_POOL查找匹配的session_id
        if hasattr(SESSION_POOL, 'items'):
            found_count = 0
            for sid, session_data in SESSION_POOL.items():
                found_count += 1
                # 检查session_data中是否包含session_id字段，并且与传入的session_id匹配
                if isinstance(session_data, dict) and session_data.get("session_id") == session_id:
                    log.info(f"找到匹配的Socket.IO连接: {sid} 对应 session_id: {session_id}")
                    return sid
            
            log.debug(f"遍历SESSION_POOL完成，共检查了{found_count}个会话，未找到匹配的session_id")
        else:
            log.debug("SESSION_POOL没有items方法，无法遍历")
        
        # 如果没有找到直接匹配的session_id，记录日志
        log.debug(f"未找到session_id {session_id} 对应的Socket.IO连接")
        return None
        
    except Exception as e:
        log.error(f"查找Socket.IO连接时发生错误: {e}", exc_info=True)
        return None


def _find_socket_by_user_id(user_id: str, USER_POOL, SESSION_POOL) -> Optional[str]:
    """
    根据user_id查找对应的Socket.IO连接ID
    通过USER_POOL获取用户的所有连接，然后返回最新的一个
    
    Args:
        user_id: 用户ID
        USER_POOL: 用户连接池
        SESSION_POOL: 会话连接池
        
    Returns:
        Optional[str]: 找到的Socket.IO连接ID，未找到返回None
    """
    try:
        log.debug(f"开始查找user_id {user_id} 对应的Socket.IO连接")
        
        # 从USER_POOL获取用户的所有连接
        if isinstance(USER_POOL, dict):
            user_sids = USER_POOL.get(user_id, [])
        else:
            # 对于RedisDict，需要特殊处理
            user_sids = USER_POOL.get(user_id, [])
            # 如果是awaitable，需要await
            if user_sids is not None and hasattr(user_sids, '__await__'):
                # 在同步函数中无法await，直接返回None
                log.warning("RedisDict类型在同步函数中无法处理")
                return None
            # 确保user_sids是列表类型
            if not isinstance(user_sids, list):
                user_sids = []
                
        log.debug(f"用户 {user_id} 的所有连接: {user_sids}")
        
        # 如果用户有连接，返回最新的一个（列表中的最后一个）
        if user_sids:
            # 验证sid是否仍然有效（在SESSION_POOL中存在）
            for sid in reversed(user_sids):  # 从最新的开始检查
                if sid in SESSION_POOL:
                    log.info(f"通过user_id {user_id} 找到匹配的Socket.IO连接: {sid}")
                    return sid
                    
        log.debug(f"未找到user_id {user_id} 对应的Socket.IO连接")
        return None

    except Exception as e:
        log.error(f"通过user_id查找Socket.IO连接时发生错误: {e}", exc_info=True)
        return None


def _extract_blueprint_token(message: Dict[str, Any]) -> Optional[str]:
    for key in (
        "blueprint_message_id",
        "message_id",
        "reply_id",
        "operate_id",
        "request_id",
        "id",
    ):
        value = message.get(key)
        if value:
            return f"{key}:{value}"
    session_id = message.get("session_id")
    status = message.get("status")
    if session_id:
        return f"session:{session_id}:{status}"
    return None


def _should_skip_blueprint_sync(user_id: str, token: Optional[str]) -> Tuple[bool, str]:
    now = time.time()
    last_ts = _RECENT_BLUEPRINT_SYNC_TS.get(user_id)
    if last_ts and now - last_ts < BLUEPRINT_SYNC_DEBOUNCE_SECONDS:
        return True, f"debounce<{BLUEPRINT_SYNC_DEBOUNCE_SECONDS}s"
    if token:
        token_ts = _RECENT_BLUEPRINT_TOKENS.get(token)
        if token_ts and now - token_ts < BLUEPRINT_SYNC_TOKEN_TTL_SECONDS:
            return True, "duplicate_token"
    return False, ""


def _mark_blueprint_sync(user_id: str, token: Optional[str]) -> None:
    now = time.time()
    _RECENT_BLUEPRINT_SYNC_TS[user_id] = now
    if not token:
        return
    _RECENT_BLUEPRINT_TOKENS[token] = now
    _RECENT_BLUEPRINT_TOKEN_QUEUE.append((token, now))
    while len(_RECENT_BLUEPRINT_TOKEN_QUEUE) > BLUEPRINT_SYNC_TOKEN_CACHE_SIZE:
        old_token, _ = _RECENT_BLUEPRINT_TOKEN_QUEUE.popleft()
        _RECENT_BLUEPRINT_TOKENS.pop(old_token, None)
    while _RECENT_BLUEPRINT_TOKEN_QUEUE:
        old_token, ts = _RECENT_BLUEPRINT_TOKEN_QUEUE[0]
        if now - ts <= BLUEPRINT_SYNC_TOKEN_TTL_SECONDS:
            break
        _RECENT_BLUEPRINT_TOKEN_QUEUE.popleft()
        _RECENT_BLUEPRINT_TOKENS.pop(old_token, None)


def _get_blueprint_lock(user_id: str) -> asyncio.Lock:
    lock = _BLUEPRINT_LOCKS.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _BLUEPRINT_LOCKS[user_id] = lock
    return lock


async def _run_blueprint_sync(
    message: Dict[str, Any],
    user_id: str,
    dedupe_token: Optional[str],
) -> Optional[BlueprintSyncResult]:
    try:
        task_template_registry.refresh(force=False)
    except Exception as refresh_exc:  # pylint: disable=broad-except
        log.warning("刷新任务模板缓存失败，将继续使用现有缓存: %s", refresh_exc)

    start_ts = time.perf_counter()
    try:
        result = await asyncio.to_thread(sync_blueprint_for_user, message)
    except Exception as sync_exc:
        log.error("战略蓝图同步失败 user_id=%s: %s", user_id, sync_exc, exc_info=True)
        return None

    duration = time.perf_counter() - start_ts
    for log_line in result.logs:
        log.info("[BlueprintSync] %s", log_line)
    log.info(
        "[BlueprintSync] success user_id=%s template_source=%s created=%s updated=%s subtasks=%s duration=%.2fs",
        user_id,
        task_template_registry.source,
        len(result.created_tasks),
        len(result.updated_tasks),
        len(result.generated_subtasks),
        duration,
    )
    _mark_blueprint_sync(user_id, dedupe_token)
    return result


def register_conversation_queue_handler(redis_queue_listener) -> None:
    """
    注册对话消息队列处理器
    
    Args:
        redis_queue_listener: Redis队列监听器实例
    """
    # 注册对话代理消息队列处理器
    redis_queue_listener.register_handler(
        "ai-conversation-agent-message-queue", 
        handle_conversation_agent_message,
        {
            "timeout": 30,
            "max_retry": 3,
            "dead_letter_queue": "conversation_agent_dead_letter"
        }
    )
    
    log.info("已注册对话消息队列处理器")
