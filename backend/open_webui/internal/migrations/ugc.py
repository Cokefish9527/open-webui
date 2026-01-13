from __future__ import annotations

import os
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


def ensure_ugc_schema(
    engine_or_connection: Engine | Connection,
    *,
    schema: str | None = None,
    dry_run: bool = False,
    logger: Callable[[str], None] | None = None,
) -> dict:
    """
    Ensure UGC Video Generation tables exist (per design doc V3.2).

    Design tables:
    - Material_Models
    - Video_Tasks
    - Task_Scenes
    """

    executed_statements: List[str] = []

    with _connection_from(engine_or_connection) as connection:
        inspector = inspect(connection)
        effective_schema = schema or inspector.default_schema_name
        dialect = connection.dialect.name.lower()
        material_models_table = _qualified_name("Material_Models", effective_schema, connection=connection)
        video_tasks_table = _qualified_name("Video_Tasks", effective_schema, connection=connection)
        task_scenes_table = _qualified_name("Task_Scenes", effective_schema, connection=connection)

        statements: List[str] = []

        def _id_autoincrement_type() -> str:
            if dialect == "postgresql":
                return "BIGSERIAL"
            if dialect == "mysql":
                return "BIGINT AUTO_INCREMENT"
            # sqlite
            return "INTEGER"

        def _json_type() -> str:
            if dialect == "postgresql":
                return "JSONB"
            if dialect == "mysql":
                return "JSON"
            return "TEXT"

        def _datetime_type() -> str:
            if dialect == "postgresql":
                return "TIMESTAMP"
            return "DATETIME"

        def _tinyint_type() -> str:
            if dialect == "mysql":
                return "TINYINT"
            # postgresql/sqlite
            return "SMALLINT"

        def _user_id_type() -> str:
            """
            UGC 的 user_id 与 OpenWebUI 的 user.id 对齐，使用字符串类型。
            """
            if dialect == "mysql":
                return "VARCHAR(255)"
            # postgresql/sqlite
            return "TEXT"

        def _column_type_name(table_name: str, column_name: str) -> str | None:
            try:
                cols = inspector.get_columns(table_name, schema=effective_schema)
            except Exception:
                return None
            for col in cols:
                if col.get("name") == column_name:
                    t = col.get("type")
                    return str(t).lower() if t is not None else None
            return None

        # Best-effort runtime schema alignment for PostgreSQL (safe cast to TEXT).
        if dialect == "postgresql":
            current = _column_type_name("Material_Models", "user_id")
            if current and "text" not in current and inspector.has_table("Material_Models", schema=effective_schema):
                statements.append(
                    f"ALTER TABLE {material_models_table} ALTER COLUMN user_id TYPE TEXT USING user_id::text"
                )

            current = _column_type_name("Video_Tasks", "user_id")
            if current and "text" not in current and inspector.has_table("Video_Tasks", schema=effective_schema):
                statements.append(
                    f"ALTER TABLE {video_tasks_table} ALTER COLUMN user_id TYPE TEXT USING user_id::text"
                )

        # 1. Material_Models (数字人资产表)
        if not inspector.has_table("Material_Models", schema=effective_schema):
            id_type = _id_autoincrement_type()
            created_at_type = _datetime_type()
            user_id_type = _user_id_type()
            if dialect == "sqlite":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {material_models_table} (
    id {id_type} PRIMARY KEY AUTOINCREMENT,
    user_id {user_id_type} NOT NULL,
    model_name VARCHAR(128) NOT NULL,
    model_img_url VARCHAR(512) NOT NULL,
    voice_provider_id VARCHAR(128) NOT NULL,
    voice_preview_url VARCHAR(512) NOT NULL,
    created_at {created_at_type} NOT NULL
)
                    """.strip()
                )
            else:
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {material_models_table} (
    id {id_type} PRIMARY KEY,
    user_id {user_id_type} NOT NULL,
    model_name VARCHAR(128) NOT NULL,
    model_img_url VARCHAR(512) NOT NULL,
    voice_provider_id VARCHAR(128) NOT NULL,
    voice_preview_url VARCHAR(512) NOT NULL,
    created_at {created_at_type} NOT NULL
)
                    """.strip()
                )

        # 2. Video_Tasks (主任务表)
        if not inspector.has_table("Video_Tasks", schema=effective_schema):
            status_type = _tinyint_type()
            step_type = _tinyint_type()
            base_inputs_type = _json_type()
            dt_type = _datetime_type()
            user_id_type = _user_id_type()
            statements.append(
                f"""
CREATE TABLE IF NOT EXISTS {video_tasks_table} (
    id VARCHAR(36) PRIMARY KEY,
    user_id {user_id_type} NOT NULL,
    status {status_type} NOT NULL DEFAULT 0,
    step {step_type} NOT NULL DEFAULT 1,
    model_id BIGINT NOT NULL,
    base_inputs {base_inputs_type} NOT NULL,
    result_video_url VARCHAR(512),
    created_at {dt_type} NOT NULL,
    updated_at {dt_type} NOT NULL,
    FOREIGN KEY(model_id) REFERENCES {material_models_table}(id)
)
                """.strip()
            )

        # 3. Task_Scenes (分镜明细表)
        if not inspector.has_table("Task_Scenes", schema=effective_schema):
            id_type = _id_autoincrement_type()
            if dialect == "sqlite":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {task_scenes_table} (
    id {id_type} PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(36) NOT NULL,
    scene_index INT NOT NULL,
    subtitle TEXT,
    script_desc TEXT,
    reference_img_url VARCHAR(512),
    fragment_video_url VARCHAR(512),
    UNIQUE(task_id, scene_index),
    FOREIGN KEY(task_id) REFERENCES {video_tasks_table}(id) ON DELETE CASCADE
)
                    """.strip()
                )
            else:
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {task_scenes_table} (
    id {id_type} PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    scene_index INT NOT NULL,
    subtitle TEXT,
    script_desc TEXT,
    reference_img_url VARCHAR(512),
    fragment_video_url VARCHAR(512),
    UNIQUE(task_id, scene_index),
    FOREIGN KEY(task_id) REFERENCES {video_tasks_table}(id) ON DELETE CASCADE
)
                    """.strip()
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

            # Avoid long hangs on PostgreSQL when DDL waits for locks (e.g. concurrent schema init).
            # These settings apply only to the current transaction.
            if dialect == "postgresql":
                lock_timeout = int(os.environ.get("UGC_SCHEMA_LOCK_TIMEOUT_SECONDS", "5") or 5)
                statement_timeout = int(os.environ.get("UGC_SCHEMA_STATEMENT_TIMEOUT_SECONDS", "30") or 30)
                if lock_timeout > 0:
                    connection.execute(text(f"SET LOCAL lock_timeout = '{lock_timeout}s'"))
                if statement_timeout > 0:
                    connection.execute(text(f"SET LOCAL statement_timeout = '{statement_timeout}s'"))
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
