import asyncio
import socketio
import logging
import sys
import time
import os
from redis import asyncio as aioredis
from typing import Any, Dict, List, Optional, Union
from open_webui.socket.utils import RedisDict

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
SESSION_POOL: Union[RedisDict, Dict[str, Any]] 
USER_POOL: Union[RedisDict, Dict[str, List[str]]] 
USAGE_POOL: Union[RedisDict, Dict[str, Dict[str, Any]]] 
SESSION_ID_TO_SID: Union[RedisDict, Dict[str, str]] 

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
    SESSION_ID_TO_SID = RedisDict(
        "open-webui:session_id_to_sid",
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
    SESSION_ID_TO_SID = {}
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
            for model_id, connections in list(USAGE_POOL.items()):
                # Creating a list of sids to remove if they have timed out
                expired_sids = [
                    sid
                    for sid, details in connections.items()
                    if now - details["updated_at"] > TIMEOUT_DURATION
                ]

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

        # 获取用户的所有会话ID
        session_ids = []
        try:
            if isinstance(USER_POOL, RedisDict):
                user_sessions = USER_POOL.get(user_id, [])
                # 如果是awaitable，需要await
                if user_sessions is not None and hasattr(user_sessions, '__await__'):
                    session_ids = await user_sessions
                else:
                    session_ids = user_sessions if user_sessions is not None else []
            else:
                session_ids = USER_POOL.get(user_id, [])
        except:
            session_ids = []
            
        # 确保session_ids是列表类型
        if not isinstance(session_ids, list):
            session_ids = []
            
        # 如果请求信息中包含session_id，也添加到列表中
        if request_info.get("session_id"):
            session_ids = list(set(session_ids + [request_info.get("session_id")]))

        # 发送事件到所有相关会话
        emit_tasks = []
        for session_id in session_ids:
            if sio is not None:
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


def get_models_in_use():
    # List models that are currently in use
    try:
        if isinstance(USAGE_POOL, RedisDict):
            # For RedisDict, we need to handle async operations
            # Since this is a sync function, we can't await, so return empty list
            return []
        else:
            return list(USAGE_POOL.keys())
    except:
        return []


def get_active_user_ids():
    """Get the list of active user IDs."""
    try:
        if isinstance(USER_POOL, RedisDict):
            # For RedisDict, we need to handle async operations
            # Since this is a sync function, we can't await, so return empty list
            return []
        else:
            return list(USER_POOL.keys())
    except:
        return []


def get_user_active_status(user_id):
    """Check if a user is currently active."""
    try:
        if isinstance(USER_POOL, RedisDict):
            # This would need to be async to properly handle RedisDict
            # For now, return False as we can't properly check
            return False
        else:
            return user_id in USER_POOL
    except:
        return False


def get_user_id_from_session_pool(sid):
    try:
        if isinstance(SESSION_POOL, RedisDict):
            # This would need to be async to properly handle RedisDict
            # For now, return None as we can't properly check
            return None
        else:
            user = SESSION_POOL.get(sid)
        if user:
            return user["id"]
        return None
    except:
        return None


def get_user_ids_from_room(room):
    if sio is not None and hasattr(sio, 'manager') and sio.manager is not None and hasattr(sio.manager, 'get_participants'):
        try:
            active_session_ids = sio.manager.get_participants(
                namespace="/",
                room=room,
            )

            active_user_ids = []
            for session_id in active_session_ids:
                if isinstance(SESSION_POOL, dict):
                    session_data = SESSION_POOL.get(session_id[0], {})
                else:
                    # For RedisDict, we can't properly handle this in sync context
                    session_data = {}
                if session_data and "id" in session_data:
                    active_user_ids.append(session_data["id"])
            
            return list(set(active_user_ids))
        except:
            return []
    return []


def get_active_status_by_user_id(user_id):
    try:
        if isinstance(USER_POOL, RedisDict):
            # This would need to be async to properly handle RedisDict
            # For now, return False as we can't properly check
            return False
        else:
            return user_id in USER_POOL
    except:
        return False


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


# Only register events if sio is not None
if sio is not None:
    # 类型断言，告诉类型检查器sio不为None
    from typing import cast
    sio_not_none = cast(socketio.AsyncServer, sio)
    
    @sio_not_none.on("usage")
    async def usage(sid, data):
        try:
            if isinstance(SESSION_POOL, RedisDict):
                session_exists = sid in SESSION_POOL
            else:
                session_exists = sid in SESSION_POOL
                
            if session_exists:
                model_id = data["model"]
                # Record the timestamp for the last update
                current_time = int(time.time())

                # Store the new usage data and task
                if isinstance(USAGE_POOL, RedisDict):
                    existing_data = USAGE_POOL.get(model_id, {})
                    # 如果是awaitable，需要await
                    if existing_data is not None and hasattr(existing_data, '__await__'):
                        existing_data = await existing_data
                    
                    # 确保existing_data是字典类型
                    if not isinstance(existing_data, dict):
                        existing_data = {}
                        
                    new_data = dict(existing_data)
                    new_data[sid] = {"updated_at": current_time}
                    USAGE_POOL[model_id] = new_data
                else:
                    USAGE_POOL[model_id] = {
                        **(USAGE_POOL[model_id] if model_id in USAGE_POOL else {}),
                        sid: {"updated_at": current_time},
                    }
        except Exception as e:
            log.error(f"Error in usage handler: {e}")


    @sio_not_none.event
    async def connect(sid, environ, auth):
        log.info(f"📥 CONNECT事件 - SID: {sid}")
        log.debug(f".environ: {environ}")
        log.debug(f".auth: {auth}")
        
        try:
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
                    user_data = user.model_dump()
                    # 存储session_id到sid的映射
                    # 使用UUID方式构造session_id，而不是时间戳拼接
                    import uuid
                    session_id = f"session_{user.id}_{uuid.uuid4().hex[:8]}"
                    if isinstance(data, dict) and data.get("session_id"):
                        session_id = data.get("session_id")
                    
                    # 确保session_id不为None
                    if session_id is None:
                        session_id = f"session_{user.id}_{uuid.uuid4().hex[:8]}"
                    
                    if isinstance(SESSION_ID_TO_SID, RedisDict):
                        SESSION_ID_TO_SID[session_id] = sid
                    else:
                        SESSION_ID_TO_SID[session_id] = sid
                        
                    user_data["session_id"] = session_id
                    
                    if isinstance(SESSION_POOL, RedisDict):
                        SESSION_POOL[sid] = user_data
                    else:
                        SESSION_POOL[sid] = user_data
                        
                    if isinstance(USER_POOL, RedisDict):
                        user_sids = USER_POOL.get(user.id, [])
                        # 如果是awaitable，需要await
                        if user_sids is not None and hasattr(user_sids, '__await__'):
                            user_sids = await user_sids
                        # 确保user_sids是列表类型
                        if not isinstance(user_sids, list):
                            user_sids = []
                        USER_POOL[user.id] = user_sids + [sid]
                    else:
                        if user.id in USER_POOL:
                            USER_POOL[user.id] = USER_POOL[user.id] + [sid]
                        else:
                            USER_POOL[user.id] = [sid]
                    log.info(f"💾 会话 {sid} 已存储到会话池，session_id: {session_id}")
                else:
                    log.warning("❌ 用户认证失败")
                    return False
            else:
                log.warning("⚠️  连接请求中没有提供认证信息")
                return False
        except Exception as e:
            log.error(f"Error in connect handler: {e}")
            return False


    @sio_not_none.on("user-join")
    async def user_join(sid, data):
        try:
            auth = data["auth"] if "auth" in data else None
            if not auth or "token" not in auth:
                return

            data = decode_token(auth["token"])
            if data is None or "id" not in data:
                return

            user = Users.get_user_by_id(data["id"])
            if not user:
                return

            user_data = user.model_dump()
            # 存储session_id到sid的映射
            # 使用UUID方式构造session_id，而不是时间戳拼接
            import uuid
            session_id = f"session_{user.id}_{uuid.uuid4().hex[:8]}"
            if isinstance(data, dict) and data.get("session_id"):
                session_id = data.get("session_id")
            
            # 确保session_id不为None
            if session_id is None:
                session_id = f"session_{user.id}_{uuid.uuid4().hex[:8]}"
            
            if isinstance(SESSION_ID_TO_SID, RedisDict):
                SESSION_ID_TO_SID[session_id] = sid
            else:
                SESSION_ID_TO_SID[session_id] = sid
                
            user_data["session_id"] = session_id
            
            if isinstance(SESSION_POOL, RedisDict):
                SESSION_POOL[sid] = user_data
            else:
                SESSION_POOL[sid] = user_data
                
            if isinstance(USER_POOL, RedisDict):
                user_sids = USER_POOL.get(user.id, [])
                # 如果是awaitable，需要await
                if user_sids is not None and hasattr(user_sids, '__await__'):
                    user_sids = await user_sids
                # 确保user_sids是列表类型
                if not isinstance(user_sids, list):
                    user_sids = []
                USER_POOL[user.id] = user_sids + [sid]
            else:
                if user.id in USER_POOL:
                    USER_POOL[user.id] = USER_POOL[user.id] + [sid]
                else:
                    USER_POOL[user.id] = [sid]

            # Join all the channels
            channels = Channels.get_channels_by_user_id(user.id)
            log.debug(f"{channels=}")
            for channel in channels:
                await sio_not_none.enter_room(sid, f"channel:{channel.id}")
            return {"id": user.id, "name": user.name, "session_id": session_id}
        except Exception as e:
            log.error(f"Error in user_join handler: {e}")


    @sio_not_none.on("join-channels")
    async def join_channel(sid, data):
        try:
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
            for channel in channels:
                await sio_not_none.enter_room(sid, f"channel:{channel.id}")
        except Exception as e:
            log.error(f"Error in join_channel handler: {e}")


    @sio_not_none.on("channel-events")
    async def channel_events(sid, data):
        try:
            room = f"channel:{data['channel_id']}"
            if hasattr(sio_not_none, 'manager') and sio_not_none.manager is not None and hasattr(sio_not_none.manager, 'get_participants'):
                participants = sio_not_none.manager.get_participants(
                    namespace="/",
                    room=room,
                )

                sids = [sid for sid, _ in participants]
                if sid not in sids:
                    return

                event_data = data["data"]
                event_type = event_data["type"]

                if event_type == "typing":
                    if isinstance(SESSION_POOL, RedisDict):
                        session_data = SESSION_POOL.get(sid, {})
                        # 如果是awaitable，需要await
                        if session_data is not None and hasattr(session_data, '__await__'):
                            session_data = await session_data
                    else:
                        session_data = SESSION_POOL.get(sid, {})
                        
                    # 确保session_data是字典类型
                    if not isinstance(session_data, dict):
                        session_data = {}
                        
                    # 确保session_data包含UserNameResponse所需的所有字段
                    user_info = {
                        "id": session_data.get("id", ""),
                        "name": session_data.get("name", ""),
                        "role": session_data.get("role", "user"),
                        "profile_image_url": session_data.get("profile_image_url", "")
                    }
                    
                    await sio_not_none.emit(
                        "channel-events",
                        {
                            "channel_id": data["channel_id"],
                            "message_id": data.get("message_id", None),
                            "data": event_data,
                            "user": user_info,
                        },
                        room=room,
                    )
        except Exception as e:
            log.error(f"Error in channel_events handler: {e}")


    @sio_not_none.event
    async def disconnect(sid):
        log.info(f"📥 DISCONNECT事件 - SID: {sid}")
        
        try:
            if isinstance(SESSION_POOL, RedisDict):
                session_data = SESSION_POOL.get(sid, {})
                # 如果是awaitable，需要await
                if session_data is not None and hasattr(session_data, '__await__'):
                    session_data = await session_data
            else:
                session_data = SESSION_POOL.get(sid, {})
                
            # 确保session_data是字典类型
            if not isinstance(session_data, dict):
                session_data = {}
                
            if session_data:
                session_id = session_data.get("session_id")
                if session_id:
                    if isinstance(SESSION_ID_TO_SID, RedisDict):
                        try:
                            del SESSION_ID_TO_SID[session_id]
                        except KeyError:
                            pass
                    else:
                        try:
                            del SESSION_ID_TO_SID[session_id]
                        except KeyError:
                            pass
                            
                if isinstance(SESSION_POOL, RedisDict):
                    try:
                        del SESSION_POOL[sid]
                    except KeyError:
                        pass
                else:
                    try:
                        del SESSION_POOL[sid]
                    except KeyError:
                        pass
                        
                log.info(f"🗑️  会话 {sid} 已从会话池移除")

                user_id = session_data["id"]
                if isinstance(USER_POOL, RedisDict):
                    user_sids = USER_POOL.get(user_id, [])
                    # 如果是awaitable，需要await
                    if user_sids is not None and hasattr(user_sids, '__await__'):
                        user_sids = await user_sids
                    # 确保user_sids是列表类型
                    if not isinstance(user_sids, list):
                        user_sids = []
                    # 过滤掉当前断开的sid
                    updated_sids = [_sid for _sid in user_sids if _sid != sid]
                    if len(updated_sids) == 0:
                        try:
                            del USER_POOL[user_id]
                            log.info(f"🗑️  用户 {user_id} 已从用户池移除")
                        except KeyError:
                            pass
                    else:
                        USER_POOL[user_id] = updated_sids
                        log.info(f"🔄 用户 {user_id} 仍有 {len(updated_sids)} 个连接")
                else:
                    if user_id in USER_POOL:
                        USER_POOL[user_id] = [_sid for _sid in USER_POOL[user_id] if _sid != sid]

                        if len(USER_POOL[user_id]) == 0:
                            try:
                                del USER_POOL[user_id]
                                log.info(f"🗑️  用户 {user_id} 已从用户池移除")
                            except KeyError:
                                pass
                        else:
                            log.info(f"🔄 用户 {user_id} 仍有 {len(USER_POOL[user_id])} 个连接")
            else:
                log.warning(f"⚠️  未知会话 {sid} 断开连接")
        except Exception as e:
            log.error(f"Error in disconnect handler: {e}")


# 导入HSAI事件注册函数
from open_webui.socket.hsai_events import register_hsai_events

# 注册HSAI事件
# 创建一个模拟的请求信息来获取事件发射器
request_info = {"user_id": "system"}
emitter = get_event_emitter(request_info, update_db=False)
register_hsai_events(sio, emitter)

get_event_caller = get_event_call