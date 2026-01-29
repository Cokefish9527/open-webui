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

    Final tables:
    - hsai_ugc_material_models
    - hsai_ugc_video_tasks
    - hsai_ugc_task_scenes

    Legacy tables (will be renamed during a planned downtime migration):
    - Material_Models -> hsai_ugc_material_models
    - Video_Tasks -> hsai_ugc_video_tasks
    - Task_Scenes -> hsai_ugc_task_scenes
    
    New tables (V3.3 Product Library):
    - hsai_ugc_products (Product Library)

    New tables (V3.3.1 Debugging):
    - hsai_ugc_callback_logs (Queue Logs)
    """

    executed_statements: List[str] = []

    with _connection_from(engine_or_connection) as connection:
        # Guard against pooled connections left in failed transactions.
        # This avoids "InFailedSqlTransaction" when running SET LOCAL.
        # Multi-layer defense: rollback at both connection and transaction level.
        try:
            connection.rollback()
        except Exception:
            pass
        
        # Additional safeguard: if connection is in a transaction, explicitly rollback.
        # This handles edge cases where connection.rollback() doesn't fully clear state.
        try:
            if connection.in_transaction():
                trans = connection.get_transaction()
                if trans is not None:
                    trans.rollback()
        except Exception:
            pass
        
        inspector = inspect(connection)
        effective_schema = schema or inspector.default_schema_name
        dialect = connection.dialect.name.lower()
        preparer = connection.dialect.identifier_preparer

        legacy_material_models = "Material_Models"
        legacy_video_tasks = "Video_Tasks"
        legacy_task_scenes = "Task_Scenes"

        material_models = "hsai_ugc_material_models"
        video_tasks = "hsai_ugc_video_tasks"
        task_scenes = "hsai_ugc_task_scenes"
        products = "hsai_ugc_products"
        callback_logs = "hsai_ugc_callback_logs"

        legacy_material_models_table = _qualified_name(legacy_material_models, effective_schema, connection=connection)
        legacy_video_tasks_table = _qualified_name(legacy_video_tasks, effective_schema, connection=connection)
        legacy_task_scenes_table = _qualified_name(legacy_task_scenes, effective_schema, connection=connection)

        material_models_table = _qualified_name(material_models, effective_schema, connection=connection)
        video_tasks_table = _qualified_name(video_tasks, effective_schema, connection=connection)
        task_scenes_table = _qualified_name(task_scenes, effective_schema, connection=connection)
        products_table = _qualified_name(products, effective_schema, connection=connection)
        callback_logs_table = _qualified_name(callback_logs, effective_schema, connection=connection)

        statements: List[str] = []

        legacy_material_models_exists = inspector.has_table(legacy_material_models, schema=effective_schema)
        legacy_video_tasks_exists = inspector.has_table(legacy_video_tasks, schema=effective_schema)
        legacy_task_scenes_exists = inspector.has_table(legacy_task_scenes, schema=effective_schema)

        material_models_exists = inspector.has_table(material_models, schema=effective_schema)
        video_tasks_exists = inspector.has_table(video_tasks, schema=effective_schema)
        task_scenes_exists = inspector.has_table(task_scenes, schema=effective_schema)
        products_exists = inspector.has_table(products, schema=effective_schema)
        callback_logs_exists = inspector.has_table(callback_logs, schema=effective_schema)


        def _rename_table(old_identifier: str, new_identifier: str) -> str:
            """
            Rename table within the same schema/database.

            - PostgreSQL/SQLite: ALTER TABLE <qualified old> RENAME TO <new_identifier>
            - MySQL: RENAME TABLE <qualified old> TO <qualified new>
            """
            old_qualified = _qualified_name(old_identifier, effective_schema, connection=connection)
            if dialect == "mysql":
                new_qualified = _qualified_name(new_identifier, effective_schema, connection=connection)
                return f"RENAME TABLE {old_qualified} TO {new_qualified}"
            new_quoted = preparer.quote_identifier(new_identifier)
            return f"ALTER TABLE {old_qualified} RENAME TO {new_quoted}"

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

        def _column_names(table_name: str) -> set[str]:
            try:
                cols = inspector.get_columns(table_name, schema=effective_schema)
            except Exception:
                return set()
            return {str(col.get("name") or "") for col in cols if col.get("name")}

        # Best-effort runtime schema alignment for PostgreSQL (safe cast to TEXT).
        # Important: we only *plan* these statements here; actual ALTERs are appended after potential renames,
        # so we don't try to ALTER a table name that doesn't exist yet.
        need_material_user_id_cast = False
        need_video_user_id_cast = False
        if dialect == "postgresql":
            material_inspect_name = material_models if material_models_exists else (
                legacy_material_models if legacy_material_models_exists else None
            )
            current = _column_type_name(material_inspect_name, "user_id") if material_inspect_name else None
            if current and "text" not in current:
                need_material_user_id_cast = True

            video_inspect_name = video_tasks if video_tasks_exists else (
                legacy_video_tasks if legacy_video_tasks_exists else None
            )
            current = _column_type_name(video_inspect_name, "user_id") if video_inspect_name else None
            if current and "text" not in current:
                need_video_user_id_cast = True

        # Planned downtime migration: rename legacy tables to final names.
        # Note: this is safe only when the service is stopped (no concurrent writes/reads).
        if legacy_material_models_exists and not material_models_exists:
            statements.append(_rename_table(legacy_material_models, material_models))
            material_models_exists = True
        if legacy_video_tasks_exists and not video_tasks_exists:
            statements.append(_rename_table(legacy_video_tasks, video_tasks))
            video_tasks_exists = True
        if legacy_task_scenes_exists and not task_scenes_exists:
            statements.append(_rename_table(legacy_task_scenes, task_scenes))
            task_scenes_exists = True

        if need_material_user_id_cast:
            statements.append(
                f"ALTER TABLE {material_models_table} ALTER COLUMN user_id TYPE TEXT USING user_id::text"
            )

        if need_video_user_id_cast:
            statements.append(
                f"ALTER TABLE {video_tasks_table} ALTER COLUMN user_id TYPE TEXT USING user_id::text"
            )

        # 1. hsai_ugc_material_models (数字人资产表)
        if not material_models_exists:
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
    minimax_account_id INTEGER,
    created_at {created_at_type} NOT NULL,
    deleted_at {created_at_type}
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
    minimax_account_id BIGINT,
    created_at {created_at_type} NOT NULL,
    deleted_at {created_at_type}
)
)
                    """.strip()
                )
        else:
            # Table exists, check if deleted_at column exists
            material_cols = _column_names(material_models)
            if "deleted_at" not in material_cols:
                created_at_type = _datetime_type()
                statements.append(
                    f"ALTER TABLE {material_models_table} ADD COLUMN deleted_at {created_at_type}"
                )


        # Add missing columns for existing hsai_ugc_material_models (or legacy before rename).
        inspect_material_table = material_models if material_models_exists else (
            legacy_material_models if legacy_material_models_exists else None
        )
        if inspect_material_table:
            existing_cols = _column_names(inspect_material_table)
            account_id_type = "BIGINT" if dialect in ("postgresql", "mysql") else "INTEGER"
            if "minimax_account_id" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {material_models_table} ADD COLUMN minimax_account_id {account_id_type}"
                )

        # 2. hsai_ugc_video_tasks (主任务表)
        if not video_tasks_exists:
            status_type = _tinyint_type()
            step_type = _tinyint_type()
            base_inputs_type = _json_type()
            dt_type = _datetime_type()
            progress_percent_type = _tinyint_type()
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
    billed_credits NUMERIC(12, 6),
    billed_at {dt_type},
    free_retry_until {dt_type},
    last_trigger_at {dt_type},
    progress_percent {progress_percent_type} NOT NULL DEFAULT 0,
    last_progress_at {dt_type},
    closed_at {dt_type},
    closed_reason TEXT,
    created_at {dt_type} NOT NULL,
    updated_at {dt_type} NOT NULL,
    FOREIGN KEY(model_id) REFERENCES {material_models_table}(id)
)
                """.strip()
            )

        # Add missing columns for existing hsai_ugc_video_tasks (or legacy before rename).
        # We inspect the currently-existing table (legacy or final), but always generate ALTERs against the final name.
        inspect_video_table = video_tasks if video_tasks_exists else (legacy_video_tasks if legacy_video_tasks_exists else None)
        if inspect_video_table:
            existing_cols = _column_names(inspect_video_table)
            dt_type = _datetime_type()
            progress_percent_type = _tinyint_type()

            # Billing / retry policy fields (UGC charging at script stage + cooldown/free-retry window).
            if "billed_credits" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {video_tasks_table} ADD COLUMN billed_credits NUMERIC(12, 6)"
                )
            if "billed_at" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {video_tasks_table} ADD COLUMN billed_at {dt_type}"
                )
            if "free_retry_until" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {video_tasks_table} ADD COLUMN free_retry_until {dt_type}"
                )
            if "last_trigger_at" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {video_tasks_table} ADD COLUMN last_trigger_at {dt_type}"
                )

            if "progress_percent" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {video_tasks_table} ADD COLUMN progress_percent {progress_percent_type} NOT NULL DEFAULT 0"
                )
            if "last_progress_at" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {video_tasks_table} ADD COLUMN last_progress_at {dt_type}"
                )
            if "closed_at" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {video_tasks_table} ADD COLUMN closed_at {dt_type}"
                )
            if "closed_reason" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {video_tasks_table} ADD COLUMN closed_reason TEXT"
                )

        # Add missing columns for existing hsai_ugc_task_scenes.
        inspect_scenes_table = task_scenes if task_scenes_exists else (legacy_task_scenes if legacy_task_scenes_exists else None)
        if inspect_scenes_table:
            existing_cols = _column_names(inspect_scenes_table)
            if "fragment_video_urls" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {task_scenes_table} ADD COLUMN fragment_video_urls TEXT"
                )
            if "retry_count" not in existing_cols:
                retry_count_type = "INTEGER"
                statements.append(
                    f"ALTER TABLE {task_scenes_table} ADD COLUMN retry_count {retry_count_type} NOT NULL DEFAULT 0"
                )
                statements.append(
                    f"ALTER TABLE {task_scenes_table} ADD COLUMN error_msg TEXT"
                )
            if "image_prompt" not in existing_cols:
                statements.append(
                    f"ALTER TABLE {task_scenes_table} ADD COLUMN image_prompt TEXT"
                )

        if inspect_video_table:
            # Backfill best-effort for older rows.
            def _has_rows(sql: str) -> bool:
                try:
                    return bool(connection.execute(text(sql)).first())
                except Exception:
                    return False

            if _has_rows(f"SELECT 1 FROM {video_tasks_table} WHERE last_progress_at IS NULL LIMIT 1"):
                statements.append(
                    f"""
UPDATE {video_tasks_table}
SET last_progress_at = COALESCE(last_progress_at, updated_at, created_at)
WHERE last_progress_at IS NULL
                    """.strip()
                )

            if _has_rows(f"SELECT 1 FROM {video_tasks_table} WHERE last_trigger_at IS NULL LIMIT 1"):
                statements.append(
                    f"""
UPDATE {video_tasks_table}
SET last_trigger_at = COALESCE(last_trigger_at, created_at, updated_at)
WHERE last_trigger_at IS NULL
                    """.strip()
                )

            if _has_rows(
                f"SELECT 1 FROM {video_tasks_table} WHERE COALESCE(progress_percent, 0) = 0 AND status IN (-2, -1, 0, 1, 2, 3, 4, 5, 6) LIMIT 1"
            ):
                statements.append(
                    f"""
UPDATE {video_tasks_table}
SET progress_percent = CASE
    WHEN status = 0 THEN 5
    WHEN status = 1 THEN 20
    WHEN status = 2 THEN 35
    WHEN status = 3 THEN 50
    WHEN status = 4 THEN 85
    WHEN status = 5 THEN 90
    WHEN status = 6 THEN 100
    ELSE 0
END
WHERE COALESCE(progress_percent, 0) = 0 AND status IN (-2, -1, 0, 1, 2, 3, 4, 5, 6)
                    """.strip()
                )

        # 3. hsai_ugc_task_scenes (分镜明细表)
        if not task_scenes_exists:
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
    fragment_video_urls TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_msg TEXT,
    image_prompt TEXT,
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
    fragment_video_urls TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_msg TEXT,
    image_prompt TEXT,
    UNIQUE(task_id, scene_index),
    FOREIGN KEY(task_id) REFERENCES {video_tasks_table}(id) ON DELETE CASCADE
)
                    """.strip()
                )

        # 4. hsai_ugc_products (产品库表)
        #
        # 方案B：产品库仅维护「产品名称/描述/产品图链接」三项业务属性。
        # 为可追溯与审计，仍保留 id/user_id/created_at/updated_at。
        desired_product_columns = {
            "id",
            "user_id",
            "name",
            "description",
            "cover_img",
            "created_at",
            "updated_at",
        }

        if not products_exists:
            id_type = _id_autoincrement_type()
            created_at_type = _datetime_type()
            user_id_type = _user_id_type()
            if dialect == "sqlite":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {products_table} (
    id {id_type} PRIMARY KEY AUTOINCREMENT,
    user_id {user_id_type} NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    cover_img VARCHAR(512),
    created_at {created_at_type} NOT NULL,
    updated_at {created_at_type} NOT NULL
)
                    """.strip()
                )
            else:
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {products_table} (
    id {id_type} PRIMARY KEY,
    user_id {user_id_type} NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    cover_img VARCHAR(512),
    created_at {created_at_type} NOT NULL,
    updated_at {created_at_type} NOT NULL
)
                    """.strip()
                )
        else:
            # 表已存在：对齐到精简后的列集合（删除多余字段）。
            existing_cols = _column_names(products)

            # 先补齐缺失列，保证后续 SQLite 重建表时可直接 SELECT。
            # For PostgreSQL, use ADD COLUMN IF NOT EXISTS to avoid duplicate column errors.
            if "description" not in existing_cols:
                if dialect == "postgresql":
                    statements.append(f"ALTER TABLE {products_table} ADD COLUMN IF NOT EXISTS description TEXT")
                else:
                    statements.append(f"ALTER TABLE {products_table} ADD COLUMN description TEXT")
                existing_cols.add("description")
            if "cover_img" not in existing_cols:
                if dialect == "postgresql":
                    statements.append(f"ALTER TABLE {products_table} ADD COLUMN IF NOT EXISTS cover_img VARCHAR(512)")
                else:
                    statements.append(f"ALTER TABLE {products_table} ADD COLUMN cover_img VARCHAR(512)")
                existing_cols.add("cover_img")

            extra_cols = sorted([c for c in existing_cols if c not in desired_product_columns])

            if extra_cols:
                if dialect == "sqlite":
                    # SQLite 不支持 DROP COLUMN：通过“重建表 + 迁移数据”实现删除多余列。
                    tmp_identifier = f"{products}__tmp_pruned"
                    tmp_table = _qualified_name(tmp_identifier, effective_schema, connection=connection)
                    id_type = _id_autoincrement_type()
                    created_at_type = _datetime_type()
                    user_id_type = _user_id_type()

                    statements.append(f"DROP TABLE IF EXISTS {tmp_table}")
                    statements.append(
                        f"""
CREATE TABLE IF NOT EXISTS {tmp_table} (
    id {id_type} PRIMARY KEY AUTOINCREMENT,
    user_id {user_id_type} NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    cover_img VARCHAR(512),
    created_at {created_at_type} NOT NULL,
    updated_at {created_at_type} NOT NULL
)
                        """.strip()
                    )
                    statements.append(
                        f"""
INSERT INTO {tmp_table} (id, user_id, name, description, cover_img, created_at, updated_at)
SELECT id, user_id, name, description, cover_img, created_at, updated_at
FROM {products_table}
                        """.strip()
                    )
                    statements.append(f"DROP TABLE {products_table}")
                    statements.append(_rename_table(tmp_identifier, products))
                else:
                    # PostgreSQL: DROP COLUMN IF EXISTS; MySQL: 仅在列存在时 DROP COLUMN。
                    for col in extra_cols:
                        quoted = preparer.quote_identifier(col)
                        if dialect == "postgresql":
                            statements.append(f"ALTER TABLE {products_table} DROP COLUMN IF EXISTS {quoted}")
                        elif dialect == "mysql":
                            statements.append(f"ALTER TABLE {products_table} DROP COLUMN {quoted}")
                        else:
                            # 兜底：尽力而为（若不支持会在执行时抛错，提示人工介入）
                            statements.append(f"ALTER TABLE {products_table} DROP COLUMN {quoted}")


        # 5. hsai_ugc_callback_logs (回调日志表)
        if not callback_logs_exists:
            id_type = _id_autoincrement_type()
            created_at_type = _datetime_type()
            json_type = "JSON"
            if dialect == "sqlite":
                # SQLite doesn't strictly enforce JSON type but supports it in newer versions via extension,
                # or we just store as TEXT. SQLAlchemy JSON type handles it.
                # But for raw SQL, we use TEXT or JSON. Let's use TEXT for compatibility if needed, 
                # but SQLAlchemy dialects usually map JSON to suitable type.
                # However, raw SQL string here needs specific type.
                json_type = "TEXT" 

            if dialect == "sqlite":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {callback_logs_table} (
    id {id_type} PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(36),
    msg_type VARCHAR(64),
    payload {json_type},
    error_msg TEXT,
    created_at {created_at_type} NOT NULL
)
                    """.strip()
                )
            else:
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {callback_logs_table} (
    id {id_type} PRIMARY KEY,
    task_id VARCHAR(36),
    msg_type VARCHAR(64),
    payload {json_type},
    error_msg TEXT,
    created_at {created_at_type} NOT NULL
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
                # Extra safeguard: verify transaction is not in failed state before SET LOCAL.
                # If in failed state, rollback and re-begin to get a clean transaction.
                try:
                    # Test query to detect failed transaction state
                    connection.execute(text("SELECT 1"))
                except Exception:
                    # Transaction is in failed state, force rollback
                    try:
                        if trans is not None:
                            trans.rollback()
                        else:
                            connection.rollback()
                    except Exception:
                        pass
                    # Re-begin transaction
                    if not connection.in_transaction():
                        trans = connection.begin()
                
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
