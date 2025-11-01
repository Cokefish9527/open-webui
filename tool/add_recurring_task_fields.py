#!/usr/bin/env python3
"""
为 PostgreSQL 中的 hsai_tasks 增加循环任务字段，并创建状态日志表。
执行方式：python tool/add_recurring_task_fields.py --database-url <URL> [--dry-run]

默认读取 open_webui.env.DATABASE_URL。重复执行应保持幂等。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def _logger(message: str) -> None:
    print(message)


def get_database_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url
    from open_webui.env import DATABASE_URL  # type: ignore

    return DATABASE_URL


def run_migration(database_url: str, dry_run: bool = False) -> None:
    if "postgresql" not in database_url.lower():
        raise RuntimeError("该脚本目前仅支持 PostgreSQL 数据库")

    from sqlalchemy import create_engine
    from open_webui.env import DATABASE_SCHEMA  # type: ignore
    from open_webui.internal.migrations import ensure_recurring_task_schema

    engine = create_engine(database_url)
    print(f"连接数据库：{database_url}")
    if dry_run:
        print("⚙️  Dry-run 模式，仅打印 SQL，不执行实际写入。")

    diagnostics = ensure_recurring_task_schema(
        engine,
        schema=DATABASE_SCHEMA,
        dry_run=dry_run,
        logger=_logger,
    )

    if diagnostics["executed"]:
        print("✅ 循环任务字段与状态日志表已更新。")
    else:
        print("ℹ️  循环任务字段与状态日志表已存在，无需变更。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="为任务系统增加循环字段与日志表")
    parser.add_argument(
        "--database-url",
        dest="database_url",
        default=None,
        help="数据库连接串，默认读取 open_webui.env.DATABASE_URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印 SQL，不执行写入",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        database_url = get_database_url(args.database_url)
        run_migration(database_url, dry_run=args.dry_run)
        return 0
    except Exception as exc:  # pragma: no cover - CLI diagnostic
        print(f"❌ 脚本执行失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
