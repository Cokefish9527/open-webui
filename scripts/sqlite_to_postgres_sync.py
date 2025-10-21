#!/usr/bin/env python
"""
工具脚本：将 SQLite 数据库的表结构与数据同步至 PostgreSQL。

默认行为为“重建+迁移”：
- 读取 SQLite 的全部用户表，提取列、索引、外键等信息；
- 在 PostgreSQL（默认 schema 为 public）中 DROP 并重建同名表（含索引）；
- 按批次将数据插入目标库，并生成 Markdown 迁移报告。

安全约束：
- 不在仓库中硬编码目标库凭据，需通过环境变量/CLI 传入；
- 默认开启事务，任一表迁移失败时会整体回滚；
- 提供 --dry-run 模式用于验证结构而不写入目标库；
- 提供 --backup-dir 选项，可在迁移前导出 SQLite .dump 及 pg_dump 备份。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import textwrap
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import psycopg2
from psycopg2 import sql
from psycopg2 import extras as pg_extras


# -------- 数据结构定义 -------- #

@dataclass
class ColumnSpec:
    name: str
    source_type: str
    not_null: bool
    default: Optional[str]
    is_pk: bool
    pg_type: str = "TEXT"
    notes: List[str] = field(default_factory=list)


@dataclass
class IndexSpec:
    name: str
    columns: List[str]
    unique: bool
    origin: str


@dataclass
class TableSpec:
    name: str
    columns: List[ColumnSpec]
    indexes: List[IndexSpec]
    foreign_keys: List[Tuple[str, str, str]]  # (column, ref_table, ref_column)


@dataclass
class TableReport:
    name: str
    row_count: int = 0
    duration_sec: float = 0.0
    created_indexes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    skipped: bool = False
    error: Optional[str] = None


@dataclass
class MigrationReport:
    started_at: dt.datetime
    finished_at: Optional[dt.datetime] = None
    dry_run: bool = False
    mode: str = "recreate"
    sqlite_path: str = ""
    postgres_dsn: str = ""
    postgres_schema: str = "public"
    table_reports: List[TableReport] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    backup_paths: List[str] = field(default_factory=list)

    def add_table_report(self, report: TableReport) -> None:
        self.table_reports.append(report)

    def to_markdown(self) -> str:
        finished_str = (
            self.finished_at.isoformat(timespec="seconds")
            if self.finished_at
            else "N/A"
        )
        duration = (
            (self.finished_at - self.started_at).total_seconds()
            if self.finished_at
            else 0.0
        )
        summary_rows = sum(r.row_count for r in self.table_reports if not r.error)
        summary_tables = len(self.table_reports)
        failed_tables = [r for r in self.table_reports if r.error]
        skipped_tables = [r for r in self.table_reports if r.skipped]

        lines = [
            "# 数据库迁移报告",
            "",
            f"- 启动时间：{self.started_at.isoformat(timespec='seconds')}",
            f"- 结束时间：{finished_str}",
            f"- 总耗时：{duration:.2f} 秒",
            f"- 模式：{self.mode}",
            f"- Dry-run：{'是' if self.dry_run else '否'}",
            f"- SQLite 源：`{self.sqlite_path}`",
            f"- PostgreSQL 目标：`{self._safe_dsn()}` / schema=`{self.postgres_schema}`",
            f"- 处理数据表：{summary_tables} 个",
            f"- 成功迁移行数：{summary_rows}",
            "",
            "## 备份与输出",
        ]

        if self.backup_paths:
            for p in self.backup_paths:
                lines.append(f"- {p}")
        else:
            lines.append("- （未启用备份）")

        if self.warnings:
            lines.extend(["", "## 全局警告"])
            for warn in self.warnings:
                lines.append(f"- {warn}")

        if self.errors:
            lines.extend(["", "## 全局错误"])
            for err in self.errors:
                lines.append(f"- {err}")

        lines.extend(
            [
                "",
                "## 明细",
                "",
                "| 表名 | 行数 | 耗时(s) | 新增索引 | 警告 | 状态 |",
                "| --- | ---: | ---: | --- | --- | --- |",
            ]
        )
        for report in self.table_reports:
            state = "skipped" if report.skipped else "ok"
            if report.error:
                state = "error"
            warn_text = "<br/>".join(report.warnings) if report.warnings else ""
            idx_text = "<br/>".join(report.created_indexes) if report.created_indexes else ""
            lines.append(
                f"| `{report.name}` | {report.row_count} | {report.duration_sec:.2f} | "
                f"{idx_text} | {warn_text} | {state} |"
            )

        if failed_tables:
            lines.extend(["", "## 失败表详情"])
            for report in failed_tables:
                lines.extend(
                    [
                        f"- `{report.name}`：{report.error}",
                        "",
                        "```text",
                        report.error,
                        "```",
                    ]
                )

        if skipped_tables:
            lines.extend(["", "## 跳过表"])
            for report in skipped_tables:
                lines.append(f"- `{report.name}`：{'; '.join(report.warnings)}")

        lines.extend(
            [
                "",
                "## 回滚建议",
                "",
                textwrap.dedent(
                    """
                    1. 若迁移后数据异常，可通过以下方式回滚：
                       - 使用报告中列出的 `pg_dump` 备份（若已启用）恢复。
                       - 或者重新执行脚本，加上 `--mode=recreate --strict` 以保证失败即回滚。
                    2. 如需仅回滚某张表，可在 PostgreSQL 中执行：
                       ```sql
                       TRUNCATE TABLE "<schema>"."<table>" CASCADE;
                       ```
                       再重新运行脚本，并加上 `--tables <table>` 限定范围（未来版本支持）。
                    3. 执行回滚前建议先使用 `BEGIN; ... ROLLBACK;` 验证恢复脚本的正确性。
                    """
                ).strip(),
            ]
        )
        return "\n".join(lines)

    def _safe_dsn(self) -> str:
        parts = []
        for entry in self.postgres_dsn.split():
            if entry.lower().startswith("password="):
                parts.append("password=******")
            else:
                parts.append(entry)
        return " ".join(parts)


# -------- CLI & 环境读取 -------- #

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="同步 SQLite 表结构与数据到 PostgreSQL。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--sqlite-path",
        default="backend/data/webui.db",
        help="SQLite 数据库文件路径",
    )
    parser.add_argument(
        "--mode",
        choices=["recreate"],
        default="recreate",
        help="同步模式。recreate=重建表后导入数据（默认）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将执行的操作，不对 PostgreSQL 写入。",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="插入 PostgreSQL 时的批量大小。",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="遇到首个错误立即终止并回滚事务（默认会记录错误并继续）。",
    )
    parser.add_argument(
        "--force-text",
        nargs="*",
        default=[],
        metavar="COLUMN",
        help="列名列表，强制保留为 TEXT 类，不做类型推断。",
    )
    parser.add_argument(
        "--schema",
        default=os.environ.get("DATABASE_SCHEMA", "public") or "public",
        help="PostgreSQL schema 名称。",
    )
    parser.add_argument(
        "--report-dir",
        default=".",
        help="迁移报告输出目录（Markdown）。",
    )
    parser.add_argument(
        "--report-name",
        default=None,
        help="报告文件名（默认包含时间戳）。",
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help="若指定，则在迁移前导出 SQLite .dump 与目标库 pg_dump。",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="打印更多调试信息。",
    )
    return parser.parse_args(argv)


def load_postgres_dsn() -> str:
    """
    允许从以下几种方式获取 PostgreSQL 连接信息：
    1. DATABASE_URL（postgresql://... 或 postgresql+psycopg2://...）
    2. POSTGRES_HOST / PORT / DB / USER / PASSWORD 等环境变量
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = "postgresql://" + db_url[len("postgres://") :]
        return db_url

    host = os.environ.get("POSTGRES_HOST")
    port = os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("POSTGRES_DB")
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")

    if not all([host, dbname, user, password]):
        raise RuntimeError(
            "未找到 PostgreSQL 凭据。请设置 DATABASE_URL 或 POSTGRES_HOST/DB/USER/PASSWORD 环境变量。"
        )

    dsn_parts = [
        f"host={host}",
        f"port={port}",
        f"dbname={dbname}",
        f"user={user}",
        f"password={password}",
    ]
    sslmode = os.environ.get("POSTGRES_SSLMODE")
    if sslmode:
        dsn_parts.append(f"sslmode={sslmode}")
    return " ".join(dsn_parts)


# -------- SQLite 元数据提取 -------- #

def open_sqlite(path: str) -> sqlite3.Connection:
    if not os.path.exists(path):
        raise FileNotFoundError(f"SQLite 数据库不存在：{path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_table_list(conn: sqlite3.Connection) -> List[str]:
    cursor = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    return [row["name"] for row in cursor.fetchall()]


def fetch_columns(conn: sqlite3.Connection, table: str) -> List[ColumnSpec]:
    cols: List[ColumnSpec] = []
    for row in conn.execute(f"PRAGMA table_info({quote_identifier(table)});"):
        cols.append(
            ColumnSpec(
                name=row["name"],
                source_type=row["type"] or "",
                not_null=bool(row["notnull"]),
                default=row["dflt_value"],
                is_pk=bool(row["pk"]),
            )
        )
    return cols


def fetch_indexes(conn: sqlite3.Connection, table: str) -> List[IndexSpec]:
    indexes: List[IndexSpec] = []
    for row in conn.execute(f"PRAGMA index_list({quote_identifier(table)});"):
        name: str = row["name"]
        if name.startswith("sqlite_autoindex"):
            continue
        columns = [
            info_row["name"]
            for info_row in conn.execute(f"PRAGMA index_info({quote_identifier(name)});")
        ]
        indexes.append(
            IndexSpec(
                name=name,
                columns=columns,
                unique=bool(row["unique"]),
                origin=row["origin"],
            )
        )
    return indexes


def fetch_foreign_keys(conn: sqlite3.Connection, table: str) -> List[Tuple[str, str, str]]:
    fkeys: List[Tuple[str, str, str]] = []
    for row in conn.execute(f"PRAGMA foreign_key_list({quote_identifier(table)});"):
        fkeys.append((row["from"], row["table"], row["to"]))
    return fkeys


def build_table_specs(conn: sqlite3.Connection, tables: Iterable[str]) -> Dict[str, TableSpec]:
    specs: Dict[str, TableSpec] = {}
    for table in tables:
        specs[table] = TableSpec(
            name=table,
            columns=fetch_columns(conn, table),
            indexes=fetch_indexes(conn, table),
            foreign_keys=fetch_foreign_keys(conn, table),
        )
    return specs


def topo_sort_tables(specs: Dict[str, TableSpec]) -> List[str]:
    graph: Dict[str, set] = {name: set() for name in specs}
    indegree: Dict[str, int] = {name: 0 for name in specs}
    for table, spec in specs.items():
        for _, ref_table, _ in spec.foreign_keys:
            if ref_table in graph:
                graph[table].add(ref_table)
    indegree = {t: len(graph[t]) for t in graph}

    queue: deque[str] = deque(sorted([t for t, d in indegree.items() if d == 0]))
    ordering: List[str] = []

    while queue:
        node = queue.popleft()
        ordering.append(node)
        for other, spec in specs.items():
            if node in graph[other]:
                graph[other].remove(node)
                indegree[other] -= 1
                if indegree[other] == 0:
                    queue.append(other)

    if len(ordering) != len(specs):
        dangling = set(specs) - set(ordering)
        ordering.extend(sorted(dangling))
    return ordering


# -------- 类型与数据转换 -------- #

BOOL_CANDIDATE_PREFIXES = ("is_", "has_", "can_", "should_", "need_", "allow_", "active", "enabled")
TIMESTAMP_SUFFIXES = ("_at", "_time", "_ts")
JSON_SUFFIXES = ("_json", "_config", "_data", "_info", "_payload", "_meta")


def infer_pg_type(
    column: ColumnSpec,
    sample_values: Sequence[Any],
    force_text: Sequence[str],
) -> Tuple[str, Optional[Any]]:
    name_lower = column.name.lower()
    base_type = (column.source_type or "").upper()
    values = [v for v in sample_values if v is not None]

    if column.name in force_text:
        return "TEXT", None

    if base_type.startswith("BLOB"):
        return "BYTEA", None

    if base_type.startswith("JSON"):
        return "JSONB", _ensure_json

    if not values:
        # 无样本数据，按声明类型映射
        return default_type_mapping(base_type)

    # 布尔推断
    if (
        base_type.startswith("INT")
        or base_type in ("INTEGER", "BOOLEAN")
        or name_lower.startswith(BOOL_CANDIDATE_PREFIXES)
    ):
        if all(v in (0, 1, True, False) for v in values):
            return "BOOLEAN", _convert_bool

    # JSON 推断
    if base_type in ("TEXT", "VARCHAR", "") or name_lower.endswith(JSON_SUFFIXES):
        if values and all(_is_valid_json(v) for v in values):
            return "JSONB", _ensure_json

    # 时间戳推断
    if base_type.startswith("INT") or base_type in ("INTEGER", "BIGINT", "") or name_lower.endswith(TIMESTAMP_SUFFIXES):
        timestamp_type, converter = _check_epoch(values)
        if timestamp_type:
            return timestamp_type, converter

    return default_type_mapping(base_type)


def default_type_mapping(base_type: str) -> Tuple[str, Optional[Any]]:
    if not base_type:
        return "TEXT", None
    if base_type.startswith("INT"):
        return "BIGINT", None
    if base_type in ("BOOLEAN",):
        return "BOOLEAN", _convert_bool
    if base_type.startswith("REAL") or base_type.startswith("FLOAT"):
        return "DOUBLE PRECISION", None
    if base_type.startswith("NUMERIC") or base_type.startswith("DECIMAL"):
        return "NUMERIC", None
    if base_type.startswith("TEXT") or base_type.startswith("CLOB"):
        return "TEXT", None
    if base_type.startswith("BLOB"):
        return "BYTEA", None
    if base_type.startswith("CHAR") or base_type.startswith("VARCHAR"):
        return "TEXT", None
    if base_type.startswith("JSON"):
        return "JSONB", _ensure_json
    return "TEXT", None


def normalize_default(default_value: Optional[str], pg_type: str) -> Optional[str]:
    if default_value is None:
        return None
    raw = default_value.strip()
    inner = raw.strip("()").strip()
    lowered = inner.strip("'\"").lower()
    if pg_type == "BOOLEAN":
        if lowered in ("1", "true", "t", "yes", "y"):
            return "TRUE"
        if lowered in ("0", "false", "f", "no", "n"):
            return "FALSE"
    return raw


def _is_valid_json(value: Any) -> bool:
    if isinstance(value, (dict, list)):
        return True
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return False
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return False
        try:
            parsed = json.loads(candidate)
            return isinstance(parsed, (dict, list))
        except json.JSONDecodeError:
            return False
    return False


def _ensure_json(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return pg_extras.Json(value) if value is not None else None
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return pg_extras.Json(json.loads(value))
        except json.JSONDecodeError:
            return value
    return value


def _convert_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ("true", "1", "t", "yes", "y")
    return bool(value)


def _check_epoch(values: Sequence[Any]) -> Tuple[Optional[str], Optional[Any]]:
    ints: List[int] = []
    for v in values:
        if isinstance(v, (int, float)):
            ints.append(int(v))
        elif isinstance(v, str) and v.isdigit():
            ints.append(int(v))
        else:
            return None, None
    if not ints:
        return None, None

    min_v, max_v = min(ints), max(ints)
    now_ts = int(time.time())
    if all(0 < v < 10**12 for v in ints) and any(v > 10**8 for v in ints):
        # 秒级时间戳
        return "TIMESTAMP WITH TIME ZONE", _epoch_to_datetime_seconds
    if max_v > 10**12 and max_v < 10**15:
        # 毫秒级时间戳
        return "TIMESTAMP WITH TIME ZONE", _epoch_to_datetime_millis
    if max_v > 10**15:
        # 微秒级
        return "TIMESTAMP WITH TIME ZONE", _epoch_to_datetime_micros
    if min_v < now_ts and max_v > now_ts - 50 * 365 * 24 * 3600:
        return "TIMESTAMP WITH TIME ZONE", _epoch_to_datetime_seconds
    return None, None


def _epoch_to_datetime_seconds(value: Any) -> Optional[dt.datetime]:
    if value is None:
        return None
    return dt.datetime.fromtimestamp(int(value), tz=dt.timezone.utc)


def _epoch_to_datetime_millis(value: Any) -> Optional[dt.datetime]:
    if value is None:
        return None
    return dt.datetime.fromtimestamp(int(value) / 1000.0, tz=dt.timezone.utc)


def _epoch_to_datetime_micros(value: Any) -> Optional[dt.datetime]:
    if value is None:
        return None
    return dt.datetime.fromtimestamp(int(value) / 1_000_000.0, tz=dt.timezone.utc)


# -------- PostgreSQL 操作 -------- #

def open_postgres(dsn: str) -> psycopg2.extensions.connection:
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = False
        return conn
    except Exception as exc:  # pragma: no cover - 直接抛给用户
        raise RuntimeError(f"连接 PostgreSQL 失败：{exc}") from exc


def ensure_schema(cursor, schema: str) -> None:
    if not schema or schema == "public":
        return
    cursor.execute(
        sql.SQL('CREATE SCHEMA IF NOT EXISTS {schema};').format(
            schema=sql.Identifier(schema)
        )
    )
    cursor.execute(
        sql.SQL('SET search_path TO {schema}, public;').format(
            schema=sql.Identifier(schema)
        )
    )


def drop_table(cursor, schema: str, table: str) -> None:
    cursor.execute(
        sql.SQL('DROP TABLE IF EXISTS {schema}.{table} CASCADE;').format(
            schema=sql.Identifier(schema),
            table=sql.Identifier(table),
        )
    )


def create_table(cursor, schema: str, table_spec: TableSpec) -> None:
    columns_sql = []
    pk_columns = [col.name for col in table_spec.columns if col.is_pk]

    for column in table_spec.columns:
        line = f'"{column.name}" {column.pg_type}'
        if column.not_null:
            line += " NOT NULL"
        if column.default is not None:
            line += f" DEFAULT {column.default}"
        columns_sql.append(line)

    pk_clause = ""
    if pk_columns:
        pk_cols = ", ".join(f'"{c}"' for c in pk_columns)
        pk_clause = f", PRIMARY KEY ({pk_cols})"

    statement = (
        f'CREATE TABLE "{schema}"."{table_spec.name}" (\n    '
        + ",\n    ".join(columns_sql)
        + pk_clause
        + "\n);"
    )
    cursor.execute(statement)


def create_indexes(cursor, schema: str, table_spec: TableSpec) -> List[str]:
    created = []
    for index in table_spec.indexes:
        index_sql = sql.SQL("CREATE {unique} INDEX IF NOT EXISTS {idx} ON {schema}.{table} ({cols});").format(
            unique=sql.SQL("UNIQUE") if index.unique else sql.SQL(""),
            idx=sql.Identifier(index.name),
            schema=sql.Identifier(schema),
            table=sql.Identifier(table_spec.name),
            cols=sql.SQL(", ").join(sql.Identifier(col) for col in index.columns),
        )
        cursor.execute(index_sql)
        created.append(index.name)
    return created


def truncate_table(cursor, schema: str, table: str) -> None:
    cursor.execute(
        sql.SQL('TRUNCATE TABLE {schema}.{table} RESTART IDENTITY CASCADE;').format(
            schema=sql.Identifier(schema),
            table=sql.Identifier(table),
        )
    )


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


# -------- 数据迁移主流程 -------- #

def migrate_table(
    cursor,
    schema: str,
    table_spec: TableSpec,
    sqlite_conn: sqlite3.Connection,
    converters: Dict[str, Tuple[str, Optional[Any]]],
    batch_size: int,
    dry_run: bool,
    mode: str,
    verbose: bool,
) -> TableReport:
    report = TableReport(name=table_spec.name)
    start = time.perf_counter()

    if dry_run:
        report.skipped = True
        report.warnings.append("dry-run 模式，仅分析不写入")
        return report

    if mode == "recreate":
        drop_table(cursor, schema, table_spec.name)
        create_table(cursor, schema, table_spec)
    else:
        truncate_table(cursor, schema, table_spec.name)

    query = f'SELECT * FROM {quote_identifier(table_spec.name)};'
    sqlite_cursor = sqlite_conn.execute(query)
    rows = []
    total_inserted = 0
    column_names = [col.name for col in table_spec.columns]
    converters_list = [converters[col.name][1] for col in table_spec.columns]

    while True:
        fetched = sqlite_cursor.fetchmany(batch_size)
        if not fetched:
            break
        rows.clear()
        for row in fetched:
            converted_row = []
            for idx, value in enumerate(row):
                converter = converters_list[idx]
                if converter:
                    converted_row.append(converter(value))
                else:
                    converted_row.append(value)
            rows.append(tuple(converted_row))

        insert_sql = sql.SQL("INSERT INTO {schema}.{table} ({columns}) VALUES %s").format(
            schema=sql.Identifier(schema),
            table=sql.Identifier(table_spec.name),
            columns=sql.SQL(", ").join(sql.Identifier(name) for name in column_names),
        )
        pg_extras.execute_values(cursor, insert_sql.as_string(cursor), rows, page_size=batch_size)
        total_inserted += len(rows)

    created_indexes = create_indexes(cursor, schema, table_spec)
    report.row_count = total_inserted
    report.duration_sec = time.perf_counter() - start
    report.created_indexes = created_indexes
    return report


def prepare_converters(
    sqlite_conn: sqlite3.Connection,
    table_spec: TableSpec,
    force_text: Sequence[str],
) -> Dict[str, Tuple[str, Optional[Any]]]:
    converters: Dict[str, Tuple[str, Optional[Any]]] = {}
    sample_rows = sqlite_conn.execute(
        f"SELECT * FROM {quote_identifier(table_spec.name)} LIMIT 200;"
    ).fetchall()
    columns = list(zip(*sample_rows)) if sample_rows else []

    for idx, column in enumerate(table_spec.columns):
        samples = [row[idx] for row in sample_rows] if sample_rows else []
        pg_type, converter = infer_pg_type(column, samples, force_text)
        column.pg_type = pg_type
        column.default = normalize_default(column.default, pg_type)
        converters[column.name] = (pg_type, converter)
        if converter:
            column.notes.append(f"converter={converter.__name__}")
    return converters


def perform_backup(args: argparse.Namespace, dsn: str, report: MigrationReport) -> None:
    if not args.backup_dir:
        return

    backup_dir = pathlib.Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    sqlite_backup = backup_dir / f"sqlite_backup_{timestamp}.sql"
    postgres_backup = backup_dir / f"postgres_backup_{timestamp}.sql"

    sqlite_cmd = ["sqlite3", args.sqlite_path, ".dump"]
    try:
        with sqlite_backup.open("w", encoding="utf-8") as fh:
            result = subprocess.run(
                sqlite_cmd,
                stdout=fh,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        if result.returncode == 0:
            report.backup_paths.append(str(sqlite_backup))
        else:
            report.warnings.append(f"sqlite3 .dump 失败，已跳过 SQLite 备份：{result.stderr.strip()}")
            sqlite_backup.unlink(missing_ok=True)
    except FileNotFoundError:
        report.warnings.append("未找到 sqlite3 命令，已跳过 SQLite 备份。")

    pg_dump_cmd = ["pg_dump", dsn_to_uri(dsn), "-f", str(postgres_backup)]
    try:
        result = subprocess.run(
            pg_dump_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            report.backup_paths.append(str(postgres_backup))
        else:
            report.warnings.append(f"pg_dump 执行失败，已跳过 PostgreSQL 备份：{result.stderr.strip()}")
            postgres_backup.unlink(missing_ok=True)
    except FileNotFoundError:
        report.warnings.append("未找到 pg_dump 命令，已跳过 PostgreSQL 备份。")


def dsn_to_uri(dsn: str) -> str:
    if dsn.startswith("postgresql://"):
        return dsn
    params = {}
    for entry in dsn.split():
        if "=" in entry:
            key, value = entry.split("=", 1)
            params[key] = value
    user = params.get("user")
    password = params.get("password")
    host = params.get("host", "localhost")
    port = params.get("port", "5432")
    dbname = params.get("dbname")
    auth = f"{user}:{password}@" if password else f"{user}@"
    return f"postgresql://{auth}{host}:{port}/{dbname}"


# -------- 主入口 -------- #

def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    report = MigrationReport(
        started_at=dt.datetime.utcnow(),
        dry_run=args.dry_run,
        mode=args.mode,
        sqlite_path=args.sqlite_path,
        postgres_schema=args.schema,
    )

    sqlite_conn = open_sqlite(args.sqlite_path)
    table_names = fetch_table_list(sqlite_conn)
    if args.verbose:
        print(f"[INFO] 检测到 {len(table_names)} 张表：{', '.join(table_names)}")
    specs = build_table_specs(sqlite_conn, table_names)
    ordering = topo_sort_tables(specs)

    dsn = load_postgres_dsn()
    report.postgres_dsn = dsn

    if args.dry_run:
        print("[INFO] Dry-run 模式：不会写入 PostgreSQL。")

    conn = open_postgres(dsn) if not args.dry_run else open_postgres(dsn)
    report.postgres_dsn = dsn

    with conn:
        with conn.cursor() as cursor:
            ensure_schema(cursor, args.schema)

    if args.backup_dir and not args.dry_run:
        perform_backup(args, dsn, report)

    try:
        with conn:
            with conn.cursor() as cursor:
                ensure_schema(cursor, args.schema)
                for table_name in ordering:
                    spec = specs[table_name]
                    table_report = TableReport(name=table_name)
                    try:
                        converters = prepare_converters(sqlite_conn, spec, args.force_text)
                        table_report = migrate_table(
                            cursor=cursor,
                            schema=args.schema,
                            table_spec=spec,
                            sqlite_conn=sqlite_conn,
                            converters=converters,
                            batch_size=args.batch_size,
                            dry_run=args.dry_run,
                            mode=args.mode,
                            verbose=args.verbose,
                        )
                    except Exception as exc:  # pragma: no cover - 记录错误并按策略处理
                        table_report.error = str(exc)
                        report.errors.append(f"{table_name}: {exc}")
                        if args.strict:
                            raise
                    finally:
                        report.add_table_report(table_report)
                        if args.verbose:
                            print(
                                f"[{table_name}] rows={table_report.row_count} "
                                f"duration={table_report.duration_sec:.2f}s "
                                f"status={'error' if table_report.error else 'ok'}"
                            )
            if args.dry_run:
                conn.rollback()
            else:
                conn.commit()
    except Exception as exc:  # pragma: no cover
        conn.rollback()
        report.errors.append(str(exc))
        raise
    finally:
        sqlite_conn.close()
        conn.close()

    report.finished_at = dt.datetime.utcnow()
    report_path = write_report(args, report)
    print(f"[INFO] 迁移报告生成：{report_path}")
    if report.errors:
        print("[WARN] 迁移过程中存在错误，请查看报告。")
        return 2
    return 0


def write_report(args: argparse.Namespace, report: MigrationReport) -> str:
    report_dir = pathlib.Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    if args.report_name:
        filename = args.report_name
    else:
        timestamp = report.finished_at.strftime("%Y%m%d_%H%M%S") if report.finished_at else "unknown"
        filename = f"migration_report_{timestamp}.md"
    report_path = report_dir / filename
    report_path.write_text(report.to_markdown(), encoding="utf-8")
    return str(report_path)


if __name__ == "__main__":  # pragma: no cover
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
