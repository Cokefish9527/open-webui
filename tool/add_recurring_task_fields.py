#!/usr/bin/env python3
"""
为 PostgreSQL 中的 hsai_tasks 增加循环任务字段，并创建状态日志表。

执行方式：
    python tool/add_recurring_task_fields.py --database-url <URL> [--dry-run]

默认读取 open_webui.env.DATABASE_URL。重复执行应保持幂等。
"""

import argparse
import os
import sys
from textwrap import dedent

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def get_database_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url
    from open_webui.env import DATABASE_URL  # type: ignore

    return DATABASE_URL


def execute_sql(engine, sql: str, dry_run: bool = False) -> None:
    from sqlalchemy import text

    print(sql.strip() + (";" if not sql.strip().endswith(";") else ""))
    if dry_run:
        return
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()


def run_migration(database_url: str, dry_run: bool = False) -> None:
    if "postgresql" not in database_url.lower():
        raise RuntimeError("该脚本目前仅支持 PostgreSQL 数据库")

    from sqlalchemy import create_engine

    engine = create_engine(database_url)
    print(f"连接数据库：{database_url}")
    if dry_run:
        print("⚙️  Dry-run 模式，仅打印 SQL，不执行实际写入。")

    alter_tasks_sql = [
        "ALTER TABLE hsai_tasks ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE hsai_tasks ADD COLUMN IF NOT EXISTS recurring_state VARCHAR(64)",
        "ALTER TABLE hsai_tasks ADD COLUMN IF NOT EXISTS last_run_at BIGINT",
        "ALTER TABLE hsai_tasks ADD COLUMN IF NOT EXISTS next_run_at BIGINT",
        "ALTER TABLE hsai_tasks ADD COLUMN IF NOT EXISTS external_controller VARCHAR(255)",
        "ALTER TABLE hsai_tasks ADD COLUMN IF NOT EXISTS recurring_meta JSONB",
    ]
    create_log_table_sql = dedent(
        """
        CREATE TABLE IF NOT EXISTS hsai_task_state_logs (
            id VARCHAR(64) PRIMARY KEY,
            task_id VARCHAR(64) NOT NULL REFERENCES hsai_tasks(id) ON DELETE CASCADE,
            from_state VARCHAR(64),
            to_state VARCHAR(64) NOT NULL,
            operator_id VARCHAR(64),
            operator_name VARCHAR(128),
            source VARCHAR(64),
            message TEXT,
            snapshot_json JSONB,
            created_at BIGINT NOT NULL
        )
        """
    )
    index_sql = [
        "CREATE INDEX IF NOT EXISTS idx_hsai_task_state_logs_task ON hsai_task_state_logs (task_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_hsai_tasks_recurring_state ON hsai_tasks (is_recurring, recurring_state)",
    ]

    for stmt in alter_tasks_sql:
        execute_sql(engine, stmt, dry_run=dry_run)

    execute_sql(engine, create_log_table_sql, dry_run=dry_run)

    for stmt in index_sql:
        execute_sql(engine, stmt, dry_run=dry_run)

    print("✅  循环任务字段与状态日志表检查完毕。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="为任务系统增加循环字段/日志表")
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
    except Exception as exc:
        print(f"❌ 脚本执行失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
