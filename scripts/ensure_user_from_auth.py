#!/usr/bin/env python3
"""
根据 auth 表补齐缺失的 user 记录，避免登录校验失败。
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///backend/data/webui.db")


from sqlalchemy import text  # noqa: E402

from open_webui.internal.db import get_db  # noqa: E402
from open_webui.models.auths import Auth  # noqa: E402
from open_webui.models.users import Users  # noqa: E402
import open_webui.models.organizations  # noqa: F401,E402
import open_webui.models.hsai_companies  # noqa: F401,E402

DEFAULT_ROLE = os.environ.get("ENSURE_USER_ROLE", "admin")
DEFAULT_PROFILE_IMAGE = os.environ.get("ENSURE_USER_PROFILE", "/user.png")


def ensure_user(email: str, role: str, name: str) -> bool:
    email = email.lower()

    with get_db() as db:
        auth = db.query(Auth).filter_by(email=email, active=True).first()
        if not auth:
            print(f"[ERROR] 未找到 auth 记录: {email}")
            return False

    existing = Users.get_user_by_email(email)
    if existing:
        print(f"[OK] user 表已存在记录: {email}")
        return True

    insert_stmt = text(
        """
        INSERT INTO "user"
        (id, name, email, role, profile_image_url,
         last_active_at, updated_at, created_at,
         api_key, settings, info,
         info_collection_completed, business_name, company_id,
         organization_id, is_super_admin, is_org_admin, oauth_sub)
        VALUES
        (:id, :name, :email, :role, :profile_image_url,
         NOW(), NOW(), NOW(),
         NULL, NULL, NULL,
         FALSE, NULL, NULL,
         NULL, :is_super_admin, FALSE, NULL)
        ON CONFLICT (id) DO NOTHING
        """
    )

    with get_db() as db:
        db.execute(
            insert_stmt,
            {
                "id": auth.id,
                "name": name,
                "email": email,
                "role": role,
                "profile_image_url": DEFAULT_PROFILE_IMAGE,
                "is_super_admin": role == "admin",
            },
        )
        db.commit()

    check = Users.get_user_by_email(email)
    if check:
        print(f"[CREATED] 补齐 user 记录: {email} (id={auth.id}, role={role})")
        return True

    print(f"[WARN] 插入 SQL 执行完毕，但 user 表仍缺少 {email}，请手动检查数据库。")
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="补齐 auth/user 记录")
    parser.add_argument("--email", required=True, help="目标邮箱")
    parser.add_argument("--role", default=DEFAULT_ROLE, help="用户角色，默认 admin")
    parser.add_argument(
        "--name",
        help="用户姓名，默认取邮箱前缀",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    name = args.name or args.email.split("@")[0]

    ok = ensure_user(args.email, args.role, name)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
