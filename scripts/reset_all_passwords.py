#!/usr/bin/env python3
"""
批量重置用户密码脚本。

使用 open_webui 的哈希方法，将 auth 表中所有账号的密码统一更新为指定默认值。
默认密码可通过环境变量 RESET_PASSWORD_DEFAULT 覆盖，默认为 hsai1234。
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from open_webui.env import DATABASE_URL as DEFAULT_DATABASE_URL  # noqa: E402
from open_webui.utils.auth import get_password_hash  # noqa: E402


def reset_all_passwords(default_password: str, database_url: str) -> int:
    """
    将 auth 表全部账号密码更新为默认值，返回受影响的行数。
    """
    hashed = get_password_hash(default_password)
    engine = create_engine(database_url)

    with engine.begin() as connection:
        result = connection.execute(
            text("UPDATE auth SET password = :password"), {"password": hashed}
        )
        return result.rowcount


def main() -> None:
    default_password = os.environ.get("RESET_PASSWORD_DEFAULT", "hsai1234")
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

    updated_rows = reset_all_passwords(default_password, database_url)
    print(
        f"Reset password for {updated_rows} account(s) "
        f"to the default value '{default_password}'."
    )


if __name__ == "__main__":
    main()
