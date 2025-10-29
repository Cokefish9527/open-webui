#!/usr/bin/env python3
"""
修复 credit / credit_log 表的时间戳列类型漂移问题。

背景：
- 代码自 2025-10-23 起统一采用 EpochTimestamp (timestamptz)；
- 现网 PostgreSQL 仍为 bigint，导致 Credits.insert_new_credit 写入失败。

执行效果：
- 将 credit.updated_at / credit.created_at、credit_log.created_at 转为 timestamptz；
- 现有 bigint 数值视为秒级 Unix 时间，通过 to_timestamp 转换；
- 已经是 timestamptz 的列自动跳过，脚本可重复运行（幂等）。
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection


DEFAULT_DB_URL_ENV = "DATABASE_URL"
DEFAULT_SCHEMA = "public"


def ensure_path():
    """
    将 backend 目录加入 sys.path，便于脚本在项目根目录直接运行。
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.abspath(os.path.join(base_dir, ".."))
    backend_dir = os.path.join(project_dir, "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


def get_db_url(cmd_url: str | None) -> str:
    if cmd_url:
        return cmd_url
    env_url = os.environ.get(DEFAULT_DB_URL_ENV)
    if env_url:
        return env_url
    raise SystemExit(
        f"未找到数据库连接串，请通过 --database-url 或环境变量 {DEFAULT_DB_URL_ENV} 提供。"
    )


def fetch_column_type(conn: Connection, table: str, column: str) -> str | None:
    result = conn.execute(
        text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table
              AND column_name = :column
            """
        ),
        {"schema": DEFAULT_SCHEMA, "table": table, "column": column},
    ).scalar()
    return result


def alter_column_to_timestamptz(conn: Connection, table: str, column: str) -> bool:
    """
    将 bigint -> timestamptz。若已是 timestamptz，则返回 False。
    """
    current = fetch_column_type(conn, table, column)
    if current is None:
        raise SystemExit(f"无法在 {table}.{column} 找到列，请确认数据库结构。")

    if current.lower() in {"timestamp with time zone", "timestamptz"}:
        print(f"[跳过] {table}.{column} 已是 timestamptz")
        return False

    if current.lower() not in {"bigint", "integer", "numeric"}:
        raise SystemExit(
            f"{table}.{column} 当前类型 {current} 非预期（bigint），请手动检查。"
        )

    print(f"[调整] {table}.{column}: {current} -> timestamptz")
    conn.execute(
        text(
            f"""
            ALTER TABLE {DEFAULT_SCHEMA}.{table}
            ALTER COLUMN {column}
            TYPE TIMESTAMPTZ
            USING to_timestamp({column})
            """
        )
    )
    return True


def migrate(engine_url: str) -> None:
    engine = create_engine(engine_url)
    tasks: Iterable[Tuple[str, str]] = (
        ("credit", "created_at"),
        ("credit", "updated_at"),
        ("credit_log", "created_at"),
    )

    with engine.begin() as conn:
        for table, column in tasks:
            altered = alter_column_to_timestamptz(conn, table, column)
            if altered:
                # 移除潜在遗留默认值，确保后续由 ORM 控制
                conn.execute(
                    text(
                        f"""
                        ALTER TABLE {DEFAULT_SCHEMA}.{table}
                        ALTER COLUMN {column}
                        DROP DEFAULT
                        """
                    )
                )
    print("[完成] 时间戳列校正完成。")


def main():
    ensure_path()
    parser = argparse.ArgumentParser(
        description="修复 credit / credit_log 时间列类型为 timestamptz。"
    )
    parser.add_argument(
        "--database-url",
        dest="database_url",
        help="数据库连接串（缺省读取环境变量 DATABASE_URL）。",
    )
    args = parser.parse_args()

    db_url = get_db_url(args.database_url)
    migrate(db_url)


if __name__ == "__main__":
    main()
