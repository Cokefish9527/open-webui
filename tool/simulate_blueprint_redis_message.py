#!/usr/bin/env python3
"""
模拟向 Redis 队列发送蓝图节点消息，以触发任务系统主线流程。
脚本既可独立运行，也可被其他模块（如自动化测试编排器）导入复用。
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import redis

# 确保可以导入项目内模块
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))


DEFAULT_QUEUE = "ai-conversation-agent-message-queue"


def get_redis_connection(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    username: Optional[str] = None,
    decode_responses: bool = True,
) -> redis.Redis:
    """根据参数返回 Redis 连接实例，并校验连通性。"""
    client = redis.Redis(
        host=host,
        port=port,
        db=db,
        password=password,
        username=username,
        decode_responses=decode_responses,
    )
    client.ping()  # 如果连接失败会抛出异常
    return client


def generate_blueprint_message(
    user_id: str,
    session_id: Optional[str] = None,
    socket_id: Optional[str] = None,
    blueprint_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """生成符合任务系统消费逻辑的蓝图消息结构。"""
    session_id = session_id or str(uuid.uuid4())
    socket_id = socket_id or str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    default_blueprint = {
        "id": str(uuid.uuid4()),
        "blueprintVersion": "v1.0",
        "executionDurationDays": "30天",
        "plannedTotalPosts": "60篇",
        "postingFrequency": "2篇/天",
        "requiredTiktokAccounts": "2个",
        "session_id": session_id,
        "request_id": str(uuid.uuid4()),
        "user_id": user_id,
        "socket_id": socket_id,
        "blue_image": (
            "# 商业策略蓝图\n\n## 社媒渠道\n- 抖音矩阵\n- 小红书精选\n\n## 内容策略\n- 视频内容 60%\n- 图文内容 40%\n\n## 发布计划\n- 每日 2 条视频\n- 每日 3 条图文"
        ),
        "createdAt": now_iso,
        "updatedAt": now_iso,
    }
    blueprint_data = {**default_blueprint, **(blueprint_payload or {})}

    return {
        "type": "ai-conversation-agent-message-queue",
        "session_id": session_id,
        "socket_id": socket_id,
        "user_id": user_id,
        "content_type": "blue_image_content",
        "status": "FINISHED",
        "reply_id": str(uuid.uuid4()),
        "operate_id": str(uuid.uuid4()),
        "data": blueprint_data,
    }


def send_blueprint_message(
    redis_conn: redis.Redis,
    message: Dict[str, Any],
    queue_name: str = DEFAULT_QUEUE,
) -> None:
    """将消息压入指定 Redis 列表队列。"""
    redis_conn.lpush(queue_name, json.dumps(message, ensure_ascii=False))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="模拟向 Redis 队列发送蓝图节点消息，触发任务系统流程。"
    )
    parser.add_argument("--user-id", required=True, help="目标用户 ID")
    parser.add_argument("--session-id", help="自定义会话 ID")
    parser.add_argument("--socket-id", help="自定义 Socket ID")
    parser.add_argument("--queue-name", default=DEFAULT_QUEUE, help="Redis 列表队列名称")
    parser.add_argument("--host", default="localhost", help="Redis 主机")
    parser.add_argument("--port", type=int, default=6379, help="Redis 端口")
    parser.add_argument("--db", type=int, default=0, help="Redis 数据库编号")
    parser.add_argument("--password", help="Redis 密码（可选）")
    parser.add_argument("--username", help="Redis 用户名（可选）")
    parser.add_argument(
        "--blueprint-json",
        help="自定义蓝图字段（JSON 字符串），会 merge 到默认 payload",
    )

    args = parser.parse_args(argv)

    try:
        redis_conn = get_redis_connection(
            host=args.host,
            port=args.port,
            db=args.db,
            password=args.password,
            username=args.username,
        )
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[错误] 连接 Redis 失败: {exc}")
        return 1

    custom_payload = None
    if args.blueprint_json:
        try:
            custom_payload = json.loads(args.blueprint_json)
        except json.JSONDecodeError as exc:  # pragma: no cover
            print(f"[错误] 自定义蓝图 JSON 解析失败: {exc}")
            return 1

    message = generate_blueprint_message(
        user_id=args.user_id,
        session_id=args.session_id,
        socket_id=args.socket_id,
        blueprint_payload=custom_payload,
    )

    try:
        send_blueprint_message(redis_conn, message, queue_name=args.queue_name)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[错误] 推送消息失败: {exc}")
        return 1

    print("✅ 蓝图消息推送完成")
    print(f"   队列: {args.queue_name}")
    print(f"   用户: {args.user_id}")
    print(f"   会话: {message['session_id']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
