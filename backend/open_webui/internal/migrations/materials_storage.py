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


def _qualified_name(identifier: str, schema: str | None, *, connection: Connection) -> str:
    preparer = connection.dialect.identifier_preparer
    if schema and connection.dialect.name.lower() != "sqlite":
        return f"{preparer.quote_identifier(schema)}.{preparer.quote_identifier(identifier)}"
    return preparer.quote_identifier(identifier)


_PG_COLUMN_DEFS = {
    "oss_bucket": "VARCHAR(255)",
    "oss_key": "TEXT",
    "oss_object_path": "TEXT",
}

_GENERIC_COLUMN_DEFS = {
    "oss_bucket": "TEXT",
    "oss_key": "TEXT",
    "oss_object_path": "TEXT",
}


def _column_defs_for(dialect: str) -> dict[str, str]:
    if dialect == "postgresql":
        return _PG_COLUMN_DEFS
    return _GENERIC_COLUMN_DEFS


def ensure_materials_storage_schema(
    engine_or_connection: Engine | Connection,
    *,
    schema: str | None = None,
    dry_run: bool = False,
    logger: Callable[[str], None] | None = None,
) -> dict:
    """
    Ensure that hsai_materials has the OSS storage columns used by the runtime.

    The function is idempotent—rerunning it after the columns exist will perform
    no-op work. Use ``dry_run=True`` to preview the ALTER statements without
    mutating the database.
    """

    executed_statements: List[str] = []

    with _connection_from(engine_or_connection) as connection:
        inspector = inspect(connection)
        effective_schema = schema or inspector.default_schema_name
        dialect = connection.dialect.name.lower()

        tables = {name for name in inspector.get_table_names(schema=effective_schema)}
        if "hsai_materials" not in tables:
            raise RuntimeError("hsai_materials table is missing; cannot enforce storage schema.")

        materials_table = _qualified_name(
            "hsai_materials", effective_schema, connection=connection
        )
        materials_columns = {
            column["name"] for column in inspector.get_columns("hsai_materials", schema=effective_schema)
        }

        column_defs = _column_defs_for(dialect)
        statements: List[str] = []
        preparer = connection.dialect.identifier_preparer

        for column_name, ddl_fragment in column_defs.items():
            if column_name not in materials_columns:
                statements.append(
                    f"ALTER TABLE {materials_table} ADD COLUMN "
                    f"{preparer.quote_identifier(column_name)} {ddl_fragment}"
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
