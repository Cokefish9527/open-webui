import argparse
import json
import os
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, Iterable, List, Optional, Sequence, Tuple

import psycopg2
from psycopg2.extras import execute_batch


DEFAULT_BATCH_SIZE = 1000
DEFAULT_EXCLUDE_TABLES = {"sqlite_sequence", "alembic_version"}
OPTIONAL_SKIP_TABLES = {"redis_queue_messages"}

TIMESTAMP_COLUMNS = {
    "created_at",
    "updated_at",
    "last_active_at",
    "started_at",
    "completed_at",
    "published_at",
    "consumed_at",
    "timestamp",
    "last_executed_at",
    "token_expires_at",
    "scheduled_at",
    "processed_at",
    "learned_at",
    "last_stats_update_at",
    "migrated_at",
}

BOOLEAN_COLUMNS = {
    "is_deleted",
    "is_pinned",
    "is_collapsed",
    "is_super_admin",
    "is_org_admin",
    "active",
    "archived",
    "is_expanded",
    "info_collection_completed",
}

JSON_COLUMNS = {
    "settings",
    "info",
    "meta",
    "data",
    "config",
    "access_control",
    "definition",
    "variables",
    "tags",
    "material_metadata",
    "ai_analysis",
    "items",
    "permissions",
    "content",
    "detail",
    "inputs",
    "outputs",
    "execution_log",
    "publish_data",
    "response_data",
    "metrics",
    "previous_metrics",
    "growth_rate",
    "company_info",
    "config_value",
    "collaborators",
    "shared_sessions",
    "position",
    "style",
    "actions",
}

DEFAULT_MIGRATION_PRIORITY = [
    "migratehistory",
    "companies",
    "auth",
    "user",
    "hsai_projects",
    "hsai_workflows",
    "hsai_material_folders",
]


def script_root() -> Path:
    return Path(__file__).resolve()


def project_root() -> Path:
    return script_root().parents[2]


def backend_root() -> Path:
    return script_root().parents[1]


DEFAULT_SQLITE_PATH = backend_root() / "data" / "webui.db"
DEFAULT_ENV_FILES = [project_root() / ".env", backend_root() / ".env"]


def parse_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            if value and value[0] in {"'", '"'} and value[-1] == value[0]:
                value = value[1:-1]

            values[key] = value

    return values


def load_env_cache() -> Dict[str, str]:
    cache: Dict[str, str] = {}
    for env_path in DEFAULT_ENV_FILES:
        cache.update(parse_env_file(env_path))
    return cache


ENV_CACHE = load_env_cache()


def get_env_value(name: str) -> Optional[str]:
    if name in os.environ:
        return os.environ[name]
    return ENV_CACHE.get(name)


def confirm(message: str, auto_yes: bool) -> None:
    if auto_yes:
        return
    response = input(f"{message} [y/N]: ").strip().lower()
    if response not in {"y", "yes"}:
        print("用户取消操作，退出。")
        sys.exit(0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 SQLite 数据迁移至 PostgreSQL（支持备份提示、表级控制与序列校准）。"
    )
    parser.add_argument(
        "--sqlite-path",
        default=str(DEFAULT_SQLITE_PATH),
        help=f"SQLite 数据库路径（默认：{DEFAULT_SQLITE_PATH})",
    )
    parser.add_argument(
        "--postgres-url",
        default=get_env_value("DATABASE_URL"),
        help="PostgreSQL 连接 URL，若未传入则读取环境变量 DATABASE_URL。",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(get_env_value("MIGRATION_BATCH_SIZE") or DEFAULT_BATCH_SIZE),
        help="批量插入的行数，默认 1000。",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        help="仅迁移指定表（可传多个），默认迁移全部应用表。",
    )
    parser.add_argument(
        "--exclude-tables",
        nargs="+",
        default=[],
        help="迁移时额外排除的表名。",
    )
    parser.add_argument(
        "--skip-truncate",
        action="store_true",
        help="跳过迁移前的 TRUNCATE 步骤。",
    )
    parser.add_argument(
        "--skip-sequence-reset",
        action="store_true",
        help="跳过迁移后的序列校准。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅输出计划，不执行实际迁移。",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="自动确认所有提示（用于非交互式执行）。",
    )
    parser.add_argument(
        "--schema",
        default=get_env_value("DATABASE_SCHEMA"),
        help="目标 PostgreSQL schema，默认读取 DATABASE_SCHEMA 或 public。",
    )
    return parser.parse_args()


def connect_sqlite(path: str) -> sqlite3.Connection:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"未找到 SQLite 数据库文件：{resolved}")

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    return conn


def connect_postgresql(url: str) -> psycopg2.extensions.connection:
    if not url:
        raise ValueError("未提供 PostgreSQL 连接 URL，请通过 --postgres-url 或设置 DATABASE_URL。")

    conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn


def qualified_table(table_name: str, schema: Optional[str]) -> str:
    if schema:
        return f'"{schema}"."{table_name}"'
    return f'"{table_name}"'


def sqlite_quote(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def fetch_sqlite_tables(conn: sqlite3.Connection) -> List[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = sorted([row[0] for row in cursor.fetchall()])
    cursor.close()
    return tables


def fetch_sqlite_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({sqlite_quote(table)})")
    columns = [row[1] for row in cursor.fetchall()]
    cursor.close()
    return columns


def fetch_sqlite_rows(
    conn: sqlite3.Connection, table: str, chunk_size: int
) -> Generator[List[sqlite3.Row], None, None]:
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {sqlite_quote(table)}")
    while True:
        rows = cursor.fetchmany(chunk_size)
        if not rows:
            break
        yield rows
    cursor.close()


def postgres_table_exists(conn: psycopg2.extensions.connection, table: str, schema: Optional[str]) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = %s AND (%s IS NULL OR table_schema = %s)
        )
        """,
        (table, schema, schema),
    )
    exists = cursor.fetchone()[0]
    cursor.close()
    return bool(exists)


def fetch_postgres_column_types(
    conn: psycopg2.extensions.connection, table: str, schema: Optional[str]
) -> Dict[str, Tuple[str, str]]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT column_name, data_type, udt_name
        FROM information_schema.columns
        WHERE table_name = %s
          AND (%s IS NULL OR table_schema = %s)
        """,
        (table, schema, schema),
    )
    mapping = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
    cursor.close()
    return mapping


def truncate_tables(
    conn: psycopg2.extensions.connection,
    tables: Sequence[str],
    schema: Optional[str],
    dry_run: bool,
) -> None:
    if dry_run:
        print("DRY RUN: 将跳过 TRUNCATE 步骤。")
        return

    cursor = conn.cursor()
    for table in tables:
        qualified = qualified_table(table, schema)
        try:
            cursor.execute(f"TRUNCATE TABLE {qualified} RESTART IDENTITY CASCADE;")
            print(f"  已执行 TRUNCATE {qualified}")
        except Exception as exc:
            conn.rollback()
            cursor.close()
            raise RuntimeError(f"TRUNCATE {qualified} 失败：{exc}") from exc
    conn.commit()
    cursor.close()


def disable_foreign_keys(conn: psycopg2.extensions.connection, dry_run: bool) -> None:
    if dry_run:
        print("DRY RUN: 将不修改外键约束状态。")
        return

    cursor = conn.cursor()
    cursor.execute("SET session_replication_role = 'replica';")
    conn.commit()
    cursor.close()
    print("已禁用外键约束（session_replication_role = replica）。")


def enable_foreign_keys(conn: psycopg2.extensions.connection, dry_run: bool) -> None:
    if dry_run:
        print("DRY RUN: 外键约束保持原状。")
        return

    cursor = conn.cursor()
    cursor.execute("SET session_replication_role = 'origin';")
    conn.commit()
    cursor.close()
    print("已恢复外键约束（session_replication_role = origin）。")


def convert_timestamp(value):
    if value is None:
        return None

    try:
        if isinstance(value, str):
            if value.isdigit():
                timestamp = int(value)
            else:
                return value
        elif isinstance(value, (int, float)):
            timestamp = int(value)
        else:
            return value

        if timestamp > 9999999999:
            timestamp = timestamp / 1000

        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError, TypeError):
        return value


def convert_boolean(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes", "on", "active"}
    return bool(value)


def convert_json(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if isinstance(value, (bytes, bytearray)):
        try:
            return json.dumps(json.loads(value.decode("utf-8")))
        except Exception:
            return json.dumps(value.decode("utf-8", errors="ignore"))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            json.loads(stripped)
            return stripped
        except json.JSONDecodeError:
            return json.dumps(stripped)
    return json.dumps(value)


def convert_numeric(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            if "." in stripped:
                return float(stripped)
            return int(stripped)
        except ValueError:
            return value
    return value


def convert_value_for_postgresql(
    value,
    column_name: str,
    table_name: str,
    pg_column_types: Dict[str, Tuple[str, str]],
):
    if value is None:
        return None

    data_type, udt_name = pg_column_types.get(column_name, (None, None)) if pg_column_types else (None, None)

    if data_type in {"bigint", "integer", "smallint"} or udt_name in {"int8", "int4", "int2"}:
        return convert_numeric(value)

    if data_type in {"numeric", "real", "double precision"} or udt_name in {"numeric", "float4", "float8"}:
        return convert_numeric(value)

    if (
        data_type in {"boolean"}
        or udt_name == "bool"
        or column_name in BOOLEAN_COLUMNS
    ):
        return convert_boolean(value)

    if data_type in {"json", "jsonb"} or column_name in JSON_COLUMNS:
        return convert_json(value)

    if data_type and "timestamp" in data_type:
        return convert_timestamp(value)

    if data_type == "date":
        return convert_timestamp(value)

    if column_name in TIMESTAMP_COLUMNS:
        return convert_timestamp(value)

    if column_name == "active" and table_name == "auth":
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, str):
            return 1 if value.lower() in {"true", "1", "yes", "on"} else 0
        return int(bool(value))

    return value


def build_insert_query(table: str, columns: Sequence[str], schema: Optional[str]) -> str:
    column_names = ", ".join(f'"{col}"' for col in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    target = qualified_table(table, schema)
    return f"INSERT INTO {target} ({column_names}) VALUES ({placeholders})"


def import_table(
    conn_sqlite: sqlite3.Connection,
    conn_postgresql: psycopg2.extensions.connection,
    table: str,
    columns: Sequence[str],
    batch_size: int,
    schema: Optional[str],
    dry_run: bool,
) -> int:
    source_columns = list(columns)
    pg_column_types = fetch_postgres_column_types(conn_postgresql, table, schema)
    if table == "user":
        pg_column_types.pop("credit_balance", None)

    missing_columns = [col for col in source_columns if col not in pg_column_types]
    if missing_columns:
        print(f"  [WARN] PostgreSQL 缺少列 {missing_columns}，迁移时将跳过。")

    columns = [col for col in source_columns if col in pg_column_types]
    if not columns:
        print(f"  [WARN] {table} 在目标库中无匹配列，跳过迁移。")
        return 0

    index_map = [source_columns.index(col) for col in columns]
    column_type_map = {col: pg_column_types[col] for col in columns}
    insert_query = build_insert_query(table, columns, schema)
    total_inserted = 0

    if dry_run:
        cursor = conn_sqlite.cursor()
        cursor.execute(f"SELECT COUNT(1) FROM {sqlite_quote(table)}")
        count = cursor.fetchone()[0]
        cursor.close()
        print(f"DRY RUN: 将迁移 {table}，行数 {count}")
        return count

    cursor_pg = conn_postgresql.cursor()

    try:
        for batch in fetch_sqlite_rows(conn_sqlite, table, batch_size):
            converted_rows: List[Tuple] = []
            for row in batch:
                converted_row = []
                for idx, column in zip(index_map, columns):
                    converted_row.append(
                        convert_value_for_postgresql(
                            row[idx], column, table, column_type_map
                        )
                    )
                converted_rows.append(tuple(converted_row))

            if not converted_rows:
                continue

            try:
                execute_batch(cursor_pg, insert_query, converted_rows, page_size=batch_size)
                total_inserted += len(converted_rows)
            except Exception as exc:
                conn_postgresql.rollback()
                sample = converted_rows[0] if converted_rows else ()
                raise RuntimeError(
                    f"插入 {table} 失败：{exc}\n示例数据：{sample}"
                ) from exc

        conn_postgresql.commit()
        return total_inserted
    finally:
        cursor_pg.close()


def reset_sequences(
    conn: psycopg2.extensions.connection,
    tables: Iterable[str],
    schema: Optional[str],
    dry_run: bool,
) -> None:
    if dry_run:
        print("DRY RUN: 将跳过序列校准。")
        return

    cursor = conn.cursor()
    for table in tables:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
              AND (%s IS NULL OR table_schema = %s)
              AND column_default LIKE 'nextval%%'
            """,
            (table, schema, schema),
        )
        serial_columns = [row[0] for row in cursor.fetchall()]

        for column in serial_columns:
            seq_target = f"{schema}.{table}" if schema else table
            cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", (seq_target, column))
            result = cursor.fetchone()
            if not result or result[0] is None:
                continue
            sequence_name = result[0]

            cursor.execute(
                f"SELECT COALESCE(MAX(\"{column}\"), 0) FROM {qualified_table(table, schema)}"
            )
            max_value = cursor.fetchone()[0] or 0
            is_called = max_value > 0

            cursor.execute(
                "SELECT setval(%s, %s, %s)",
                (sequence_name, max_value if max_value > 0 else 1, is_called),
            )
            print(
                f"  序列 {sequence_name} 已更新为 {max_value if max_value > 0 else 1} "
                f"(is_called={is_called})"
            )

    conn.commit()
    cursor.close()


def order_tables(tables: Iterable[str]) -> List[str]:
    tables_set = list(tables)
    ordered = []
    for name in DEFAULT_MIGRATION_PRIORITY:
        if name in tables_set:
            ordered.append(name)
            tables_set.remove(name)
    ordered.extend(sorted(tables_set))
    return ordered


def suggest_backup(postgres_url: str) -> None:
    print("\n建议在迁移前执行数据库备份，例如：")
    safe_url = postgres_url.replace("@", "@***:")
    print(f"  pg_dump \"{safe_url}\" --format=custom --file=backup_before_migration.dump\n")


def main() -> None:
    args = parse_args()
    schema = args.schema or "public"

    print("=== SQLite → PostgreSQL 数据库迁移脚本 ===")
    print(f"SQLite 路径: {args.sqlite_path}")
    print(f"PostgreSQL URL: {args.postgres_url}")
    print(f"目标 Schema: {schema}")
    print(f"批量大小: {args.batch_size}")
    if args.dry_run:
        print("运行模式: DRY RUN（仅输出计划）")
    print("")

    suggest_backup(args.postgres_url or "")

    conn_sqlite = connect_sqlite(args.sqlite_path)
    conn_postgresql = connect_postgresql(args.postgres_url)

    start_time = time.perf_counter()
    table_stats: Dict[str, int] = {}
    skipped_tables: List[str] = []

    try:
        available_tables = fetch_sqlite_tables(conn_sqlite)

        exclude_tables = DEFAULT_EXCLUDE_TABLES.union(OPTIONAL_SKIP_TABLES)
        if args.exclude_tables:
            exclude_tables.update(args.exclude_tables)

        target_tables = [
            table
            for table in available_tables
            if table not in exclude_tables
            and (not args.tables or table in args.tables)
        ]

        target_tables = order_tables(target_tables)

        print(f"即将迁移 {len(target_tables)} 张表：{target_tables}\n")

        if not args.dry_run and not args.skip_truncate:
            confirm(
                "将对目标库执行 TRUNCATE（含 RESTART IDENTITY CASCADE），请确保已备份。确认继续？",
                auto_yes=args.yes,
            )

        if not args.skip_truncate:
            truncate_tables(conn_postgresql, target_tables, schema, args.dry_run)

        disable_foreign_keys(conn_postgresql, args.dry_run)

        for table in target_tables:
            if not postgres_table_exists(conn_postgresql, table, schema):
                skipped_tables.append(table)
                print(f"[WARN] 目标库缺少表 {table}，已跳过。")
                continue

            columns = fetch_sqlite_columns(conn_sqlite, table)
            if table == "user" and "credit_balance" in columns:
                columns = [col for col in columns if col != "credit_balance"]

            print(f"迁移表 {table}，列：{columns}")
            inserted = import_table(
                conn_sqlite,
                conn_postgresql,
                table,
                columns,
                args.batch_size,
                schema,
                args.dry_run,
            )
            table_stats[table] = inserted
            print(f"  已迁移 {table}: {inserted} 行\n")

        if not args.skip_sequence_reset:
            reset_sequences(conn_postgresql, table_stats.keys(), schema, args.dry_run)

        enable_foreign_keys(conn_postgresql, args.dry_run)

        elapsed = time.perf_counter() - start_time
        print("=== 迁移完成 ===")
        print(f"总耗时：{elapsed:.2f} 秒")
        migrated_rows = sum(table_stats.values())
        print(f"累计迁移行数：{migrated_rows}")
        if table_stats:
            print("各表行数：")
            for name, count in table_stats.items():
                print(f"  - {name}: {count}")
        if skipped_tables:
            print(f"以下表在目标库缺失，未迁移：{skipped_tables}")

    except Exception as exc:
        conn_postgresql.rollback()
        print(f"迁移过程中出现错误：{exc}", file=sys.stderr)
        raise
    finally:
        conn_sqlite.close()
        conn_postgresql.close()


if __name__ == "__main__":
    main()
