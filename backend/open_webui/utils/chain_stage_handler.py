"""
思维链阶段消息处理器
- 监听 Redis 队列 ai-conversation-chain-stage-queue
- 将链路阶段通过 Socket.IO 推送给前端
"""

import logging
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

# 阶段 → 展示文案
CHAIN_STAGE_MAP = {
    "think": "正在思考中",
    "search": "正在检索信息",
    "collect_message": "正在分析信息",
    "message_analysis": "正在分析关键问题",
    "blue_image": "正在规划视频蓝图",
    "check_blue_image": "正在检查蓝图进度",
    "select_video_script": "正在挑选视频脚本",
    "parse_hot_video": "正在拆解爆款视频",
    "generate_video_text": "正在生成视频文案",
    "generate_final_video": "正在生成视频",
}


async def handle_chain_stage_message(message: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> None:
    """
    处理思维链阶段消息并通过 Socket.IO 推送
    """
    from open_webui.socket.main import SESSION_POOL, USER_POOL, sio  # 延迟导入避免循环

    session_id = message.get("session_id")
    socket_id = message.get("socket_id")
    user_id = message.get("user_id")
    chain_stage = message.get("chain_stage")
    timestamp = message.get("create_ts")

    if not chain_stage:
        log.debug("chain_stage 缺失，跳过: %s", message)
        return

    # 选择目标连接：优先 socket_id -> session_id -> user_id
    target_sid = None
    extra_targets = []

    if socket_id and socket_id in SESSION_POOL:
        target_sid = socket_id
    if not target_sid and session_id:
        target_sid = _find_socket_by_session_id(session_id, SESSION_POOL)
    if not target_sid and user_id:
        # 允许一个用户多连接，同步到全部
        if hasattr(SESSION_POOL, "items"):
            for sid, data in SESSION_POOL.items():
                if isinstance(data, dict) and data.get("user_id") == user_id:
                    extra_targets.append(sid)
            if extra_targets:
                target_sid = extra_targets.pop(0)
        if not target_sid:
            target_sid = _find_socket_by_user_id(user_id, USER_POOL, SESSION_POOL)

    if not target_sid:
        log.warning("思维链消息未找到可用 Socket: socket_id=%s session_id=%s user_id=%s", socket_id, session_id, user_id)
        return

    payload = {
        "type": "chain-stage-update",
        "session_id": session_id,
        "user_id": user_id,
        "chain_stage": chain_stage,
        "displayText": CHAIN_STAGE_MAP.get(chain_stage, chain_stage),
        "timestamp": timestamp,
    }

    await sio.emit("chain-stage-update", payload, to=target_sid)
    for sid in extra_targets:
        try:
            await sio.emit("chain-stage-update", payload, to=sid)
        except Exception as emit_exc:
            log.error("同步思维链事件到额外 SID %s 失败: %s", sid, emit_exc, exc_info=True)

    log.info("已推送思维链阶段: %s -> %s (session=%s)", chain_stage, payload["displayText"], session_id)


def register_chain_stage_queue_handler(redis_queue_listener) -> None:
    """
    注册思维链阶段消息队列处理器
    """
    redis_queue_listener.register_handler(
        "ai-conversation-chain-stage-queue",
        handle_chain_stage_message,
        {"dead_letter_queue": "chain_stage_dead_letter"},
    )
    log.info("已注册思维链阶段消息队列处理器")


def _find_socket_by_session_id(session_id: str, session_pool) -> Optional[str]:
    if not session_id or not session_pool:
        return None
    if session_id in session_pool:
        return session_id
    if hasattr(session_pool, "items"):
        for sid, data in session_pool.items():
            if isinstance(data, dict) and data.get("session_id") == session_id:
                return sid
    return None


def _find_socket_by_user_id(user_id: str, user_pool, session_pool) -> Optional[str]:
    if not user_id:
        return None
    if user_pool and hasattr(user_pool, "get"):
        user_sids = user_pool.get(user_id)
        if isinstance(user_sids, list):
            for sid in reversed(user_sids):
                if sid in session_pool:
                    return sid
    return None
