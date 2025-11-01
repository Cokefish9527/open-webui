from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator, List, Sequence, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine


def _log(message: str, logger: Callable[[str], None] | None) -> None:
    if logger:
        logger(message)


@contextmanager
def _connection_from(engine_or_connection: Engine | Connection) -> Iterator[Connection]:
    if isinstance(engine_or_connection, Engine):
        connection = engine_or_connection.connect()
        should_close = True
    else:
        connection = engine_or_connection
        should_close = False

    try:
        yield connection
    finally:
        if should_close:
            connection.close()


def _qualified_name(
    identifier: str,
    schema: str | None,
    *,
    connection: Connection,
) -> str:
    preparer = connection.dialect.identifier_preparer
    if schema and connection.dialect.name.lower() != "sqlite":
        return f"{preparer.quote_identifier(schema)}.{preparer.quote_identifier(identifier)}"
    return preparer.quote_identifier(identifier)


def _column_definitions(dialect: str) -> Sequence[Tuple[str, str]]:
    if dialect == "postgresql":
        return (
            ("is_recurring", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("recurring_state", "VARCHAR(64)"),
            ("last_run_at", "BIGINT"),
            ("next_run_at", "BIGINT"),
            ("external_controller", "VARCHAR(255)"),
            ("recurring_meta", "JSONB"),
        )

    # Default branch covers SQLite and other SQLAlchemy-supported dialects
    return (
        ("is_recurring", "INTEGER NOT NULL DEFAULT 0"),
        ("recurring_state", "VARCHAR(64)"),
        ("last_run_at", "BIGINT"),
        ("next_run_at", "BIGINT"),
        ("external_controller", "VARCHAR(255)"),
        ("recurring_meta", "TEXT"),
    )


def ensure_recurring_task_schema(
    engine_or_connection: Engine | Connection,
    *,
    schema: str | None = None,
    dry_run: bool = False,
    logger: Callable[[str], None] | None = None,
) -> dict:
    """
    Ensure the recurring-task related schema artifacts exist.

    The function is idempotent—re-running it will not raise errors once the
    expected columns, table, and indexes are present.

    Returns:
        dict: diagnostic payload containing the executed SQL statements and
              resolved schema name.
    """

    executed_statements: List[str] = []

    with _connection_from(engine_or_connection) as connection:
        inspector = inspect(connection)
        effective_schema = schema or inspector.default_schema_name
        dialect = connection.dialect.name.lower()
        tasks_columns = {
            column["name"] for column in inspector.get_columns("hsai_tasks", schema=effective_schema)
        }

        if "hsai_tasks" not in inspector.get_table_names(schema=effective_schema):
            raise RuntimeError("hsai_tasks table is missing; cannot apply recurring task migration.")

        tasks_table = _qualified_name("hsai_tasks", effective_schema, connection=connection)
        logs_table = _qualified_name("hsai_task_state_logs", effective_schema, connection=connection)
        indexes_tasks = {
            index["name"]
            for index in inspector.get_indexes("hsai_tasks", schema=effective_schema)
        }
        indexes_logs = set()
        if inspector.has_table("hsai_task_state_logs", schema=effective_schema):
            indexes_logs = {
                index["name"]
                for index in inspector.get_indexes("hsai_task_state_logs", schema=effective_schema)
            }

        statements: List[str] = []
        column_defs = _column_definitions(dialect)
        preparer = connection.dialect.identifier_preparer

        for column_name, ddl_fragment in column_defs:
            if column_name not in tasks_columns:
                statements.append(
                    f"ALTER TABLE {tasks_table} ADD COLUMN {preparer.quote_identifier(column_name)} {ddl_fragment}"
                )

        if not inspector.has_table("hsai_task_state_logs", schema=effective_schema):
            if dialect == "postgresql":
                create_logs_sql = f"""
CREATE TABLE IF NOT EXISTS {logs_table} (
    id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL REFERENCES {tasks_table}(id) ON DELETE CASCADE,
    from_state VARCHAR(64),
    to_state VARCHAR(64) NOT NULL,
    operator_id VARCHAR(64),
    operator_name VARCHAR(128),
    source VARCHAR(64),
    message TEXT,
    snapshot_json JSONB,
    created_at BIGINT NOT NULL
)
                """.strip()
            else:
                create_logs_sql = f"""
CREATE TABLE IF NOT EXISTS {logs_table} (
    id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    from_state VARCHAR(64),
    to_state VARCHAR(64) NOT NULL,
    operator_id VARCHAR(64),
    operator_name VARCHAR(128),
    source VARCHAR(64),
    message TEXT,
    snapshot_json TEXT,
    created_at BIGINT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES {tasks_table}(id) ON DELETE CASCADE
)
                """.strip()
            statements.append(create_logs_sql)

        idx_tasks_recurring = "idx_hsai_tasks_recurring_state"
        if idx_tasks_recurring not in indexes_tasks:
            columns_expr = f"{preparer.quote_identifier('is_recurring')}, {preparer.quote_identifier('recurring_state')}"
            statements.append(
                f"CREATE INDEX IF NOT EXISTS {preparer.quote_identifier(idx_tasks_recurring)} "
                f"ON {tasks_table} ({columns_expr})"
            )

        idx_logs_task = "idx_hsai_task_state_logs_task"
        if idx_logs_task not in indexes_logs:
            statements.append(
                f"CREATE INDEX IF NOT EXISTS {preparer.quote_identifier(idx_logs_task)} "
                f"ON {logs_table} ({preparer.quote_identifier('task_id')}, {preparer.quote_identifier('created_at')})"
            )

        if dry_run:
            for statement in statements:
                _log(f"[dry-run] {statement}", logger)
            executed_statements.extend(statements)
            return {"executed": executed_statements, "schema": effective_schema}

        if not statements:
            return {"executed": executed_statements, "schema": effective_schema}

        trans = None
        try:
            if not connection.in_transaction():
                trans = connection.begin()
            for statement in statements:
                _log(statement, logger)
                connection.execute(text(statement))
                executed_statements.append(statement)
            if trans is not None:
                trans.commit()
            else:
                connection.commit()
        except Exception:
            if trans is not None:
                trans.rollback()
            else:
                connection.rollback()
            raise

    return {"executed": executed_statements, "schema": effective_schema}
