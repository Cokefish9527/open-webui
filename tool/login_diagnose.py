#!/usr/bin/env python3
"""
模拟 Socket 测试页登录请求并诊断后台认证失败原因。
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///backend/data/webui.db")

IMPORT_ERROR: Optional[Exception] = None
try:
    from open_webui.internal.db import get_db  # type: ignore  # noqa: E402
    from open_webui.models.auths import Auth, Auths  # type: ignore  # noqa: E402
    from open_webui.utils.auth import verify_password  # type: ignore  # noqa: E402
except Exception as exc:  # pragma: no cover
    IMPORT_ERROR = exc
    if TYPE_CHECKING:
        from open_webui.models.auths import Auth  # pragma: no cover
    else:
        def _missing(*_args, **_kwargs):
            raise IMPORT_ERROR  # type: ignore

        get_db = _missing  # type: ignore
        Auth = Any  # type: ignore
        Auths = Any  # type: ignore
        verify_password = lambda *_args, **_kwargs: False  # type: ignore

DEFAULT_BASE_URL = os.environ.get("LOGIN_BASE_URL", "http://localhost:8080")
DEFAULT_EMAIL = os.environ.get("LOGIN_EMAIL", "saiter2306001@163.com")
DEFAULT_PASSWORD = os.environ.get("LOGIN_PASSWORD", "hsai1234")
DEFAULT_TIMEOUT = int(os.environ.get("LOGIN_TIMEOUT", "30"))


def request_login(base_url: str, email: str, password: str, timeout: int) -> requests.Response:
    payload = {"email": email, "password": password}
    return requests.post(
        f"{base_url.rstrip('/')}/api/v1/auths/signin",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=timeout,
    )


def load_auth_record(email: str) -> Optional[Auth]:
    if IMPORT_ERROR:
        raise IMPORT_ERROR
    with get_db() as db:
        return db.query(Auth).filter_by(email=email.lower(), active=True).first()


def diagnose(email: str, password: str) -> Dict[str, Any]:
    info: Dict[str, Any] = {}

    if IMPORT_ERROR:
        info["import_error"] = repr(IMPORT_ERROR)
        return info

    record = load_auth_record(email)
    if not record:
        info["auth_record"] = None
        return info

    info["auth_record"] = {"id": record.id, "active": record.active, "hash": record.password}
    try:
        info["hash_verify_result"] = verify_password(password, record.password)
    except Exception as exc:  # pragma: no cover
        info["hash_verify_error"] = repr(exc)

    try:
        from open_webui.models.users import Users  # type: ignore  # noqa: E402

        user = Auths.authenticate_user(email.lower(), password)
        info["authenticate_user_result"] = bool(user)
        try:
            users_row = Users.get_user_by_email(email.lower())
            info["users_table_record"] = users_row.model_dump() if users_row else None
        except Exception as users_exc:  # pragma: no cover
            info["users_lookup_error"] = repr(users_exc)
    except Exception as exc:  # pragma: no cover
        info["authenticate_user_error"] = repr(exc)

    return info


def main() -> int:
    base_url = DEFAULT_BASE_URL
    email = DEFAULT_EMAIL
    password = DEFAULT_PASSWORD
    timeout = DEFAULT_TIMEOUT

    print("==== Login Request ====")
    print(f"Base URL : {base_url}")
    print(f"Email    : {email}")

    try:
        response = request_login(base_url, email, password, timeout)
    except Exception as exc:
        print(f"[Request Error] {exc}")
        return 1

    print(f"HTTP {response.status_code}")
    if response.headers.get("content-type", "").startswith("application/json"):
        try:
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        except ValueError:
            print(response.text)
    else:
        print(response.text)

    print("\n==== Server Diagnose ====")
    result = diagnose(email, password)
    if "import_error" in result:
        print(f"导入 open_webui 模块失败: {result['import_error']}")
    elif not result.get("auth_record"):
        print("未在数据库中找到匹配的 auth 记录。")
    else:
        record = result["auth_record"]
        print(f"Auth ID : {record['id']}")
        print(f"Active  : {record['active']}")
        print(f"Hash    : {record['hash']}")
        if "hash_verify_result" in result:
            print(f"verify_password -> {result['hash_verify_result']}")
        if "hash_verify_error" in result:
            print(f"verify_password raised: {result['hash_verify_error']}")
        if "authenticate_user_result" in result:
            print(f"Auths.authenticate_user -> {result['authenticate_user_result']}")
        if "authenticate_user_error" in result:
            print(f"Auths.authenticate_user raised: {result['authenticate_user_error']}")
        if "users_table_record" in result:
            print(f"Users table record -> {bool(result['users_table_record'])}")
        if "users_lookup_error" in result:
            print(f"Users lookup raised: {result['users_lookup_error']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
