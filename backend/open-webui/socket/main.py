import asyncio
import socketio
import logging
import sys
import time
import os
from redis import asyncio as aioredis
from typing import Any, Dict, List, Optional, Union

from open_webui.models.users import Users, UserNameResponse
from open_webui.models.channels import Channels
from open_webui.models.chats import Chats
from open_webui.utils.redis import (
    get_sentinels_from_env,
    get_sentinel_url_from_env,
)

from open_webui.env import (
    ENABLE_WEBSOCKET_SUPPORT,
    WEBSOCKET_MANAGER,
    WEBSOCKET_REDIS_URL,
    WEBSOCKET_REDIS_LOCK_TIMEOUT,
    WEBSOCKET_SENTINEL_PORT,
    WEBSOCKET_SENTINEL_HOSTS,
)
from open_webui.utils.auth import decode_token
from open_webui.socket.utils import RedisDict, RedisLock

from open_webui.env import (
    GLOBAL_LOG_LEVEL,
    SRC_LOG_LEVELS,
)

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["SOCKET"])

# Initialize global variables
sio: Optional[socketio.AsyncServer] = None
mgr: Optional[socketio.AsyncRedisManager] = None

if WEBSOCKET_MANAGER == "redis":
    if WEBSOCKET_SENTINEL_HOSTS:
        mgr = socketio.AsyncRedisManager(
            get_sentinel_url_from_env(
                WEBSOCKET_REDIS_URL, WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT
            )
        )
    else:
        mgr = socketio.AsyncRedisManager(WEBSOCKET_REDIS_URL)
    sio = socketio.AsyncServer(
        cors_allowed_origins=[],
        async_mode="asgi",
        transports=(["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
        client_manager=mgr,
    )
else:
    sio = socketio.AsyncServer(
        cors_allowed_origins=[],
        async_mode="asgi",
        transports=(["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
    )

# Ensure sio is not None
if sio is None:
    raise RuntimeError("Failed to initialize socket.io server")

# Timeout duration in seconds
TIMEOUT_DURATION = 3

# Dictionary to maintain the user pool
SESSION_POOL: Union[Dict[str, Any], RedisDict] = {}
USER_POOL: Union[Dict[str, List[str]], RedisDict] = {}
USAGE_POOL: Union[Dict[str, Dict[str, Any]], RedisDict] = {}

if WEBSOCKET_MANAGER == "redis":
    log.debug("Using Redis to manage websockets.")
    redis_sentinels = get_sentinels_from_env(
        WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT
    )
    SESSION_POOL = RedisDict(
        "open-webui:session_pool",
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
    )
    USER_POOL = RedisDict(
        "open-webui:user_pool",
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
    )
    USAGE_POOL = RedisDict(
        "open-webui:usage_pool",
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
    )

    clean_up_lock = RedisLock(
        redis_url=WEBSOCKET_REDIS_URL,
        lock_name="usage_cleanup_lock",
        timeout_secs=WEBSOCKET_REDIS_LOCK_TIMEOUT,
        redis_sentinels=redis_sentinels,
    )
    aquire_func = clean_up_lock.aquire_lock
    renew_func = clean_up_lock.renew_lock
    release_func = clean_up_lock.release_lock
else:
    SESSION_POOL = {}
    USER_POOL = {}
    USAGE_POOL = {}
    aquire_func = release_func = renew_func = lambda: True


async def periodic_usage_pool_cleanup():
    if not aquire_func():
        log.debug("Usage pool cleanup lock already exists. Not running it.")
        return
    log.debug("Running periodic_usage_pool_cleanup")
    try:
        while True:
            if not renew_func():
                log.error(f"Unable to renew cleanup lock. Exiting usage pool cleanup.")
                raise Exception("Unable to renew usage pool cleanup lock.")

            now = int(time.time())
            send_usage = False
            
            # 简化处理，假设USAGE_POOL是dict类型
            if isinstance(USAGE_POOL, dict):
                usage_items = list(USAGE_POOL.items())
            else:
                # RedisDict情况，直接遍历
                usage_items = []
                for key in USAGE_POOL.keys():
                    usage_items.append((key, USAGE_POOL[key]))
            
            for model_id, connections in usage_items:
                # Creating a list of sids to remove if they have timed out
                expired_sids = []
                # 简化处理，假设connections是dict类型
                if isinstance(connections, dict):
                    connections_items = list(connections.items())
                else:
                    # RedisDict情况，直接遍历
                    connections_items = []
                    for key in connections.keys():
                        connections_items.append((key, connections[key]))
                        
                for sid, details in connections_items:
                    if now - details["updated_at"] > TIMEOUT_DURATION:
                        expired_sids.append(sid)

                for sid in expired_sids:
                    del connections[sid]

                if not connections:
                    log.debug(f"Cleaning up model {model_id} from usage pool")
                    del USAGE_POOL[model_id]
                else:
                    USAGE_POOL[model_id] = connections

                send_usage = True
            await asyncio.sleep(TIMEOUT_DURATION)
    finally:
        release_func()


# Get socketio path from environment variable, with fallback to default
SOCKETIO_PATH = os.environ.get("SOCKETIO_PATH", "/socket.io")

# 由于在main.py中使用了app.mount("/ws", socket_app)，这里应该使用相对路径
app = socketio.ASGIApp(
    sio,
    socketio_path="",  # 使用空字符串，因为路径已经在挂载时处理
)

def get_event_emitter(request_info, update_db=True):
    async def __event_emitter__(event_data):
        user_id = request_info["user_id"]

        # 简化处理
        user_pool_value = USER_POOL.get(user_id, [])
        if not isinstance(user_pool_value, list):
            # RedisDict情况，获取实际值
            user_pool_list = list(user_pool_value) if hasattr(user_pool_value, '__iter__') else [user_pool_value]
        else:
            user_pool_list = user_pool_value
            
        session_id_value = request_info.get("session_id")
        session_id_list = [session_id_value] if session_id_value else []
        
        session_ids = list(set(user_pool_list + session_id_list))

        emit_tasks = []
        if sio is not None:
            for session_id in session_ids:
                task = sio.emit(
                    "chat-events",
                    {
                        "chat_id": request_info.get("chat_id", None),
                        "message_id": request_info.get("message_id", None),
                        "data": event_data,
                    },
                    to=session_id,
                )
                emit_tasks.append(task)

        if emit_tasks:
            await asyncio.gather(*emit_tasks)

        if update_db:
            if "type" in event_data and event_data["type"] == "status":
                Chats.add_message_status_to_chat_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                    event_data.get("data", {}),
                )

            if "type" in event_data and event_data["type"] == "message":
                message = Chats.get_message_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                )

                if message:
                    content = message.get("content", "")
                    content += event_data.get("data", {}).get("content", "")

                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        request_info["chat_id"],
                        request_info["message_id"],
                        {
                            "content": content,
                        },
                    )

            if "type" in event_data and event_data["type"] == "replace":
                content = event_data.get("data", {}).get("content", "")

                Chats.upsert_message_to_chat_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                    {
                        "content": content,
                    },
                )

    return __event_emitter__


# 导入HSAI事件注册函数
from open_webui.socket.hsai_events import register_hsai_events

# 注册HSAI事件
# 创建一个模拟的请求信息来获取事件发射器
request_info = {"user_id": "system"}
emitter = get_event_emitter(request_info, update_db=False)
register_hsai_events(sio, emitter)


def get_models_in_use():
    # List models that are currently in use
    # 简化处理
    if isinstance(USAGE_POOL, dict):
        return list(USAGE_POOL.keys())
    else:
        # RedisDict情况
        return list(USAGE_POOL.keys())


def get_active_user_ids():
    """Get the list of active user IDs."""
    # 简化处理
    if isinstance(USER_POOL, dict):
        return list(USER_POOL.keys())
    else:
        # RedisDict情况
        return list(USER_POOL.keys())


def get_user_active_status(user_id):
    """Check if a user is currently active."""
    return user_id in USER_POOL


def get_user_id_from_session_pool(sid):
    user = SESSION_POOL.get(sid)
    if user:
        return user["id"]
    return None


def get_user_ids_from_room(room):
    if sio is not None and hasattr(sio.manager, 'get_participants'):
        active_session_ids = sio.manager.get_participants(
            namespace="/",
            room=room,
        )

        active_user_ids = []
        for session_id in active_session_ids:
            session_data = SESSION_POOL.get(session_id[0])
            if session_data:
                # 简化处理
                if isinstance(session_data, dict):
                    session_dict = session_data
                else:
                    # RedisDict情况，获取实际值
                    session_dict = dict(session_data) if hasattr(session_data, '__iter__') else session_data
                user_id = session_dict.get("id")
                if user_id:
                    active_user_ids.append(user_id)
        return list(set(active_user_ids))
    return []


def get_active_status_by_user_id(user_id):
    if user_id in USER_POOL:
        return True
    return False


if sio is not None:
    @sio.on("usage")
    async def usage(sid, data):
        if sid in SESSION_POOL:
            model_id = data["model"]
            # Record the timestamp for the last update
            current_time = int(time.time())

            # Store the new usage data and task
            USAGE_POOL[model_id] = {
                **(USAGE_POOL[model_id] if model_id in USAGE_POOL else {}),
                sid: {"updated_at": current_time},
            }


    @sio.event
    async def connect(sid, environ, auth):
        log.info(f"📥 CONNECT事件 - SID: {sid}")
        log.debug(f".environ: {environ}")
        log.debug(f".auth: {auth}")
        
        user = None
        if auth and "token" in auth:
            log.info("🔐 验证token...")
            data = decode_token(auth["token"])
            log.debug(f"解码token结果: {data}")

            if data is not None and "id" in data:
                user = Users.get_user_by_id(data["id"])
                log.debug(f"获取用户信息: {user}")

            if user:
                log.info(f"✅ 用户 {user.name} ({user.email}) 认证成功")
                SESSION_POOL[sid] = user.model_dump()
                if user.id in USER_POOL:
                    USER_POOL[user.id] = USER_POOL[user.id] + [sid]
                else:
                    USER_POOL[user.id] = [sid]
                log.info(f"💾 会话 {sid} 已存储到会话池")
            else:
                log.warning("❌ 用户认证失败")
                return False
        else:
            log.warning("⚠️  连接请求中没有提供认证信息")
            return False


    @sio.on("user-join")
    async def user_join(sid, data):

        auth = data["auth"] if "auth" in data else None
        if not auth or "token" not in auth:
            return

        data = decode_token(auth["token"])
        if data is None or "id" not in data:
            return

        user = Users.get_user_by_id(data["id"])
        if not user:
            return

        SESSION_POOL[sid] = user.model_dump()
        if user.id in USER_POOL:
            USER_POOL[user.id] = USER_POOL[user.id] + [sid]
        else:
            USER_POOL[user.id] = [sid]

        # Join all the channels
        channels = Channels.get_channels_by_user_id(user.id)
        log.debug(f"{channels=}")
        if sio is not None:
            for channel in channels:
                await sio.enter_room(sid, f"channel:{channel.id}")
        return {"id": user.id, "name": user.name}


    @sio.on("join-channels")
    async def join_channel(sid, data):
        auth = data["auth"] if "auth" in data else None
        if not auth or "token" not in auth:
            return

        data = decode_token(auth["token"])
        if data is None or "id" not in data:
            return

        user = Users.get_user_by_id(data["id"])
        if not user:
            return

        # Join all the channels
        channels = Channels.get_channels_by_user_id(user.id)
        log.debug(f"{channels=}")
        if sio is not None:
            for channel in channels:
                await sio.enter_room(sid, f"channel:{channel.id}")


    @sio.on("channel-events")
    async def channel_events(sid, data):
        room = f"channel:{data['channel_id']}"
        if sio is not None and hasattr(sio.manager, 'get_participants'):
            participants = sio.manager.get_participants(
                namespace="/",
                room=room,
            )

            sids = [sid for sid, _ in participants]
            if sid not in sids:
                return

            event_data = data["data"]
            event_type = event_data["type"]

            if event_type == "typing":
                await sio.emit(
                    "channel-events",
                    {
                        "channel_id": data["channel_id"],
                        "message_id": data.get("message_id", None),
                        "data": event_data,
                        "user": UserNameResponse(**SESSION_POOL[sid]).model_dump(),
                    },
                    room=room,
                )


    @sio.event
    async def disconnect(sid):
        log.info(f"📥 DISCONNECT事件 - SID: {sid}")
        
        if sid in SESSION_POOL:
            user = SESSION_POOL[sid]
            del SESSION_POOL[sid]
            log.info(f"🗑️  会话 {sid} 已从会话池移除")

            user_id = user["id"]
            USER_POOL[user_id] = [_sid for _sid in USER_POOL[user_id] if _sid != sid]

            if len(USER_POOL[user_id]) == 0:
                del USER_POOL[user_id]
                log.info(f"🗑️  用户 {user_id} 已从用户池移除")
            else:
                log.info(f"🔄 用户 {user_id} 仍有 {len(USER_POOL[user_id])} 个连接")
        else:
            log.warning(f"⚠️  未知会话 {sid} 断开连接")


def get_event_call(request_info):
    async def __event_caller__(event_data):
        if sio is not None:
            response = await sio.call(
                "chat-events",
                {
                    "chat_id": request_info.get("chat_id", None),
                    "message_id": request_info.get("message_id", None),
                    "data": event_data,
                },
                to=request_info["session_id"],
            )
            return response
        return None

    return __event_caller__


get_event_caller = get_event_call