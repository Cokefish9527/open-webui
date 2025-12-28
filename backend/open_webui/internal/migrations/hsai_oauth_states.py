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


def ensure_hsai_oauth_states_schema(
    engine_or_connection: Engine | Connection,
    *,
    schema: str | None = None,
    dry_run: bool = False,
    logger: Callable[[str], None] | None = None,
) -> dict:
    """
    Ensure `hsai_oauth_states` exists for OAuth state persistence.

    背景：TikTok OAuth 回调依赖 state 参数；若多进程/多实例/重启导致
    内存 state_storage 丢失，会触发 "Invalid or expired state parameter"。

    该运行期迁移创建一个轻量持久化表用于跨进程共享 state。
    """

    executed_statements: List[str] = []

    with _connection_from(engine_or_connection) as connection:
        inspector = inspect(connection)
        effective_schema = schema or inspector.default_schema_name
        dialect = connection.dialect.name.lower()

        table_name = "hsai_oauth_states"
        table_q = _qualified_name(table_name, effective_schema, connection=connection)
        statements: List[str] = []

        if not inspector.has_table(table_name, schema=effective_schema):
            if dialect == "postgresql":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {table_q} (
    state VARCHAR(255) PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL
)
                    """.strip()
                )
                statements.append(
                    f"CREATE INDEX IF NOT EXISTS idx_hsai_oauth_states_expires_at ON {table_q} (expires_at)"
                )
            else:
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {table_q} (
    state VARCHAR(255) PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL
)
                    """.strip()
                )
                statements.append(
                    f"CREATE INDEX IF NOT EXISTS idx_hsai_oauth_states_expires_at ON {table_q} (expires_at)"
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

