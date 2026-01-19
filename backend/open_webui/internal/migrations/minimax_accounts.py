from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator, List

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


def ensure_minimax_accounts_schema(
    engine_or_connection: Engine | Connection,
    *,
    schema: str | None = None,
    dry_run: bool = False,
    logger: Callable[[str], None] | None = None,
) -> dict:
    """
    Ensure hsai_minimax_accounts table exists.

    Note: This is an idempotent runtime migration helper.
    """

    executed_statements: List[str] = []

    with _connection_from(engine_or_connection) as connection:
        inspector = inspect(connection)
        effective_schema = schema or inspector.default_schema_name
        dialect = connection.dialect.name.lower()
        preparer = connection.dialect.identifier_preparer

        table_name = "hsai_minimax_accounts"
        table_q = _qualified_name(table_name, effective_schema, connection=connection)

        statements: List[str] = []

        if not inspector.has_table(table_name, schema=effective_schema):
            if dialect == "postgresql":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {table_q} (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    api_key TEXT,
    group_id VARCHAR(128),
    meta_json JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
                    """.strip()
                )
            elif dialect == "mysql":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {table_q} (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    enabled TINYINT NOT NULL DEFAULT 1,
    is_default TINYINT NOT NULL DEFAULT 0,
    api_key TEXT,
    group_id VARCHAR(128),
    meta_json JSON,
    created_at DATETIME,
    updated_at DATETIME
)
                    """.strip()
                )
            else:
                # sqlite
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {table_q} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(128) NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    is_default INTEGER NOT NULL DEFAULT 0,
    api_key TEXT,
    group_id VARCHAR(128),
    meta_json TEXT,
    created_at DATETIME,
    updated_at DATETIME
)
                    """.strip()
                )
        else:
            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name, schema=effective_schema)
            }

            def _add_column(col: str, ddl: str) -> None:
                if col not in existing_columns:
                    statements.append(f"ALTER TABLE {table_q} ADD COLUMN {preparer.quote_identifier(col)} {ddl}")

            _add_column("name", "VARCHAR(128)")
            if dialect == "postgresql":
                _add_column("enabled", "BOOLEAN NOT NULL DEFAULT TRUE")
                _add_column("is_default", "BOOLEAN NOT NULL DEFAULT FALSE")
                _add_column("meta_json", "JSONB")
                _add_column("created_at", "TIMESTAMPTZ")
                _add_column("updated_at", "TIMESTAMPTZ")
            else:
                _add_column("enabled", "INTEGER NOT NULL DEFAULT 1")
                _add_column("is_default", "INTEGER NOT NULL DEFAULT 0")
                _add_column("meta_json", "TEXT")
                _add_column("created_at", "DATETIME")
                _add_column("updated_at", "DATETIME")

            _add_column("api_key", "TEXT")
            _add_column("group_id", "VARCHAR(128)")

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

