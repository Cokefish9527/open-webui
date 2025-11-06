#!/usr/bin/env python3
"""Common utilities for task system automated testing scripts."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import requests

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# Ensure repository paths are available when scripts run directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "task_system_auto_test.toml"


@dataclass
class AdminAuthConfig:
    base_url: str
    email: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scope: Optional[str] = None
    token_endpoint: str = "/external/admin/oauth/token"


@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    queue: str = "ai-conversation-agent-message-queue"


@dataclass
class DatabaseConfig:
    dsn: Optional[str] = None


@dataclass
class VerifyConfig:
    poll_interval: float = 3.0
    timeout_sec: float = 60.0


@dataclass
class ReportConfig:
    output_path: Path = PROJECT_ROOT / "reports"


@dataclass
class TaskSystemConfig:
    admin_auth: AdminAuthConfig
    redis: RedisConfig
    database: DatabaseConfig
    verify: VerifyConfig
    report: ReportConfig
    raw: Dict[str, Any]

    def ensure_report_dir(self) -> Path:
        self.report.output_path.mkdir(parents=True, exist_ok=True)
        return self.report.output_path


class ConfigError(RuntimeError):
    """Raised when configuration is missing required fields."""


def _resolve_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def load_config(path: Optional[str | os.PathLike[str]] = None) -> TaskSystemConfig:
    config_path = _resolve_path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise ConfigError(f"配置文件不存在: {config_path}")

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    admin_section = data.get("admin_api") or {}
    base_url = admin_section.get("base_url")
    if not base_url:
        raise ConfigError("admin_api.base_url 未配置")
    admin_auth = AdminAuthConfig(
        base_url=base_url.rstrip("/"),
        email=admin_section.get("email"),
        password=admin_section.get("password"),
        token=admin_section.get("token"),
        client_id=admin_section.get("client_id"),
        client_secret=admin_section.get("client_secret"),
        scope=admin_section.get("scope"),
        token_endpoint=admin_section.get("token_endpoint", "/external/admin/oauth/token"),
    )

    redis_section = data.get("redis") or {}
    redis_conf = RedisConfig(
        host=redis_section.get("host", "localhost"),
        port=int(redis_section.get("port", 6379)),
        queue=redis_section.get("queue", "ai-conversation-agent-message-queue"),
    )

    db_section = data.get("db") or {}
    database_conf = DatabaseConfig(dsn=db_section.get("dsn"))

    verify_section = data.get("verify") or {}
    verify_conf = VerifyConfig(
        poll_interval=float(verify_section.get("poll_interval", 3.0)),
        timeout_sec=float(verify_section.get("timeout_sec", 60.0)),
    )

    report_section = data.get("report") or {}
    output_path = report_section.get("output_path")
    report_conf = ReportConfig(
        output_path=_resolve_path(output_path) if output_path else PROJECT_ROOT / "reports"
    )

    return TaskSystemConfig(
        admin_auth=admin_auth,
        redis=redis_conf,
        database=database_conf,
        verify=verify_conf,
        report=report_conf,
        raw=data,
    )


def join_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def utc_ts() -> int:
    return int(time.time())


def dump_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def init_logger(name: str = "task_system_test", verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = "%(asctime)s | %(levelname)s | %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    return logger


def ensure_database_url(config: TaskSystemConfig) -> None:
    """确保 DATABASE_URL 环境变量与配置保持一致。"""
    if config.database.dsn:
        current = os.environ.get("DATABASE_URL")
        if current != config.database.dsn:
            os.environ["DATABASE_URL"] = config.database.dsn


def obtain_admin_bearer_token(
    config: TaskSystemConfig,
    logger: Optional[logging.Logger] = None,
    session: Optional[requests.Session] = None,
) -> str:
    """根据配置返回 Admin API Bearer Token。优先使用静态 token。"""
    if config.admin_auth.token:
        return config.admin_auth.token

    if not config.admin_auth.client_id or not config.admin_auth.client_secret:
        raise ConfigError("admin_api.client_id/client_secret 未配置，无法获取令牌")

    sess = session or requests.Session()
    payload = {
        "grant_type": "client_credentials",
        "client_id": config.admin_auth.client_id,
        "client_secret": config.admin_auth.client_secret,
    }
    if config.admin_auth.scope:
        payload["scope"] = config.admin_auth.scope

    token_url = join_url(config.admin_auth.base_url, config.admin_auth.token_endpoint)
    resp = sess.post(token_url, json=payload, timeout=15)
    if resp.status_code != 200:
        raise ConfigError(
            f"获取管理端令牌失败: {resp.status_code} {resp.text}"
        )

    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ConfigError("令牌响应缺少 access_token 字段")

    if logger:
        logger.debug("获取外部管理端令牌成功，expires_in=%s", data.get("expires_in"))
    return token


def create_admin_session(
    config: TaskSystemConfig,
    logger: Optional[logging.Logger] = None,
) -> requests.Session:
    """创建带有 Bearer Token 的 requests.Session。"""
    sess = requests.Session()
    token = obtain_admin_bearer_token(config, logger=logger, session=sess)
    sess.headers.update({"Authorization": f"Bearer {token}"})
    return sess

