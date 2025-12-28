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


def ensure_social_accounts_schema(
    engine_or_connection: Engine | Connection,
    *,
    schema: str | None = None,
    dry_run: bool = False,
    logger: Callable[[str], None] | None = None,
) -> dict:
    """
    Ensure social_accounts schema artifacts exist.

    背景：部分环境曾缺少 `social_accounts.company_id` 列，导致外部管理接口
    在统计 TikTok 账号矩阵时触发 `UndefinedColumn` 并中断请求。

    该函数是幂等的：可在启动期/运行期重复调用。
    """

    executed_statements: List[str] = []

    with _connection_from(engine_or_connection) as connection:
        inspector = inspect(connection)
        effective_schema = schema or inspector.default_schema_name
        dialect = connection.dialect.name.lower()
        preparer = connection.dialect.identifier_preparer

        table_name = "social_accounts"
        table_q = _qualified_name(table_name, effective_schema, connection=connection)

        statements: List[str] = []

        if not inspector.has_table(table_name, schema=effective_schema):
            if dialect == "postgresql":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {table_q} (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(255),
    platform VARCHAR(64) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    account_url TEXT,
    owner_user_id VARCHAR(64),
    access_token TEXT,
    refresh_token TEXT,
    scope TEXT,
    token_type VARCHAR(64),
    open_id VARCHAR(255),
    extra TEXT,
    status VARCHAR(64) NOT NULL DEFAULT 'active',
    token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
                    """.strip()
                )
            else:
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {table_q} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(255),
    platform VARCHAR(64) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    account_url TEXT,
    owner_user_id VARCHAR(64),
    access_token TEXT,
    refresh_token TEXT,
    scope TEXT,
    token_type VARCHAR(64),
    open_id VARCHAR(255),
    extra TEXT,
    status VARCHAR(64) NOT NULL DEFAULT 'active',
    token_expires_at DATETIME,
    created_at DATETIME,
    updated_at DATETIME
)
                    """.strip()
                )
        else:
            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name, schema=effective_schema)
            }
            if "company_id" not in existing_columns:
                statements.append(
                    f"ALTER TABLE {table_q} ADD COLUMN {preparer.quote_identifier('company_id')} VARCHAR(255)"
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

