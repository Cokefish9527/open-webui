#!/usr/bin/env python3
import os
from pathlib import Path

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///backend/data/webui.db",
)


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, email, role, last_active_at, created_at
                FROM "user"
                WHERE email = :email
                """,
            ),
            {"email": os.environ.get("TARGET_EMAIL", "saiter2306001@163.com")},
        ).fetchall()
        for row in rows:
            print(dict(row._mapping))
        if not rows:
            print("no rows found")


if __name__ == "__main__":
    main()
