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


def remove_legacy_organization_schema(
    engine_or_connection: Engine | Connection,
    *,
    schema: str | None = None,
    dry_run: bool = False,
    logger: Callable[[str], None] | None = None,
) -> dict:
    """
    清理遗留的 organizations 表及相关字段。

    仅在 PostgreSQL 上执行实际的列/表删除；对于 SQLite，会记录提示并返回空执行列表。
    函数具备幂等性：若目标对象不存在，将不会抛出异常。
    """

    executed_statements: List[str] = []

    with _connection_from(engine_or_connection) as connection:
        inspector = inspect(connection)
        dialect = connection.dialect.name.lower()
        effective_schema = schema or inspector.default_schema_name

        if dialect not in {"postgresql", "sqlite"}:
            _log(f"Unsupported dialect '{dialect}', skipping legacy cleanup.", logger)
            return {"executed": executed_statements, "schema": effective_schema}

        statements: List[str] = []
        quote = connection.dialect.identifier_preparer.quote_identifier

        def qualified(table: str) -> str:
            if dialect == "postgresql" and effective_schema:
                return f"{quote(effective_schema)}.{quote(table)}"
            return quote(table)

        user_columns = {column["name"] for column in inspector.get_columns("user", schema=effective_schema)}

        group_table_name = "user_groups" if inspector.has_table("user_groups", schema=effective_schema) else "group"
        group_columns = set()
        if inspector.has_table(group_table_name, schema=effective_schema):
            group_columns = {
                column["name"]
                for column in inspector.get_columns(group_table_name, schema=effective_schema)
            }

        projects_columns = {
            column["name"] for column in inspector.get_columns("hsai_projects", schema=effective_schema)
        }

        if "organization_id" in user_columns:
            statements.append(
                f"ALTER TABLE {qualified('user')} DROP COLUMN IF EXISTS {quote('organization_id')}"
            )
        if "is_org_admin" in user_columns:
            statements.append(
                f"ALTER TABLE {qualified('user')} DROP COLUMN IF EXISTS {quote('is_org_admin')}"
            )

        renamed_to_user_groups = False
        renamed_company_column = False
        target_table = group_table_name

        if inspector.has_table("group", schema=effective_schema):
            if "organization_id" in group_columns:
                statements.append(
                    f"ALTER TABLE {qualified('group')} RENAME COLUMN {quote('organization_id')} TO {quote('company_id')}"
                )
                renamed_company_column = True
                group_columns.discard("organization_id")
                group_columns.add("company_id")
            if not inspector.has_table("user_groups", schema=effective_schema):
                statements.append(
                    f"ALTER TABLE {qualified('group')} RENAME TO {quote('user_groups')}"
                )
                renamed_to_user_groups = True
                target_table = "user_groups"

        if target_table != "user_groups":
            statements.append(
                f"ALTER TABLE {qualified(target_table)} RENAME TO {quote('user_groups')}"
            )
            target_table = "user_groups"

        if inspector.has_table("user_groups", schema=effective_schema):
            target_columns = {
                column["name"] for column in inspector.get_columns("user_groups", schema=effective_schema)
            }
        else:
            target_columns = set(group_columns)

        if "organization_id" in target_columns and not renamed_company_column:
            statements.append(
                f"ALTER TABLE {qualified('user_groups')} RENAME COLUMN {quote('organization_id')} TO {quote('company_id')}"
            )
            target_columns.discard("organization_id")
            target_columns.add("company_id")

        if "company_id" not in target_columns:
            statements.append(
                f"ALTER TABLE {qualified('user_groups')} ADD COLUMN IF NOT EXISTS {quote('company_id')} VARCHAR(255) REFERENCES {qualified('companies')}(id)"
            )

        if "organization_id" in projects_columns:
            statements.append(
                f"ALTER TABLE {qualified('hsai_projects')} DROP COLUMN IF EXISTS {quote('organization_id')}"
            )

        if inspector.has_table("organizations", schema=effective_schema):
            if dialect == "postgresql":
                statements.append(f"DROP TABLE IF EXISTS {qualified('organizations')} CASCADE")
            else:
                statements.append(f"DROP TABLE IF EXISTS {qualified('organizations')}")

        if not statements:
            return {"executed": executed_statements, "schema": effective_schema}

        if dry_run:
            for stmt in statements:
                _log(f"[dry-run] {stmt}", logger)
            executed_statements.extend(statements)
            return {"executed": executed_statements, "schema": effective_schema}

        if dialect != "postgresql":
            _log(
                f"Dialect '{dialect}' detected; automatic column drop is not supported. "
                "Please perform manual schema cleanup if必要。",
                logger,
            )
            return {"executed": executed_statements, "schema": effective_schema}

        trans = None
        try:
            if not connection.in_transaction():
                trans = connection.begin()
            for stmt in statements:
                _log(stmt, logger)
                connection.execute(text(stmt))
                executed_statements.append(stmt)
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
