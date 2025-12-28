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


def ensure_compose_trace_schema(
    engine_or_connection: Engine | Connection,
    *,
    schema: str | None = None,
    dry_run: bool = False,
    logger: Callable[[str], None] | None = None,
) -> dict:
    """
    Ensure compose trace tables exist (open-webui primary database).

    These tables store a normalized trace/step/artifact snapshot derived from
    n8n_workflow staff_main_flow_session_storage.stages (jsonb), without
    requiring n8n callbacks.
    """

    executed_statements: List[str] = []

    with _connection_from(engine_or_connection) as connection:
        inspector = inspect(connection)
        effective_schema = schema or inspector.default_schema_name
        dialect = connection.dialect.name.lower()
        preparer = connection.dialect.identifier_preparer

        traces_table = _qualified_name("hsai_compose_traces", effective_schema, connection=connection)
        steps_table = _qualified_name("hsai_compose_steps", effective_schema, connection=connection)
        artifacts_table = _qualified_name("hsai_compose_artifacts", effective_schema, connection=connection)

        statements: List[str] = []

        if not inspector.has_table("hsai_compose_traces", schema=effective_schema):
            if dialect == "postgresql":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {traces_table} (
    trace_id VARCHAR(64) PRIMARY KEY,
    n8n_session_id VARCHAR(64),
    company_id VARCHAR(64),
    project_id VARCHAR(64),
    user_id VARCHAR(64),
    business_name TEXT,
    source_learned_id BIGINT,
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    last_n8n_updated_at BIGINT,
    last_synced_at BIGINT,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
)
                    """.strip()
                )
            else:
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {traces_table} (
    trace_id VARCHAR(64) PRIMARY KEY,
    n8n_session_id VARCHAR(64),
    company_id VARCHAR(64),
    project_id VARCHAR(64),
    user_id VARCHAR(64),
    business_name TEXT,
    source_learned_id BIGINT,
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    last_n8n_updated_at BIGINT,
    last_synced_at BIGINT,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
)
                    """.strip()
                )

        if not inspector.has_table("hsai_compose_steps", schema=effective_schema):
            if dialect == "postgresql":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {steps_table} (
    id VARCHAR(64) PRIMARY KEY,
    trace_id VARCHAR(64) NOT NULL,
    step_key VARCHAR(64) NOT NULL,
    stage_name VARCHAR(128),
    status VARCHAR(32) NOT NULL DEFAULT 'captured',
    raw_stage_json JSONB,
    extracted_json JSONB,
    started_at BIGINT,
    finished_at BIGINT,
    updated_at BIGINT NOT NULL,
    UNIQUE(trace_id, step_key),
    FOREIGN KEY(trace_id) REFERENCES {traces_table}(trace_id) ON DELETE CASCADE
)
                    """.strip()
                )
            else:
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {steps_table} (
    id VARCHAR(64) PRIMARY KEY,
    trace_id VARCHAR(64) NOT NULL,
    step_key VARCHAR(64) NOT NULL,
    stage_name VARCHAR(128),
    status VARCHAR(32) NOT NULL DEFAULT 'captured',
    raw_stage_json TEXT,
    extracted_json TEXT,
    started_at BIGINT,
    finished_at BIGINT,
    updated_at BIGINT NOT NULL,
    UNIQUE(trace_id, step_key),
    FOREIGN KEY(trace_id) REFERENCES {traces_table}(trace_id) ON DELETE CASCADE
)
                    """.strip()
                )

        if not inspector.has_table("hsai_compose_artifacts", schema=effective_schema):
            if dialect == "postgresql":
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {artifacts_table} (
    id VARCHAR(64) PRIMARY KEY,
    trace_id VARCHAR(64) NOT NULL,
    step_id VARCHAR(64),
    artifact_type VARCHAR(64) NOT NULL,
    oss_url TEXT,
    metadata_json JSONB,
    created_at BIGINT NOT NULL,
    UNIQUE(trace_id, artifact_type, oss_url),
    FOREIGN KEY(trace_id) REFERENCES {traces_table}(trace_id) ON DELETE CASCADE
)
                    """.strip()
                )
            else:
                statements.append(
                    f"""
CREATE TABLE IF NOT EXISTS {artifacts_table} (
    id VARCHAR(64) PRIMARY KEY,
    trace_id VARCHAR(64) NOT NULL,
    step_id VARCHAR(64),
    artifact_type VARCHAR(64) NOT NULL,
    oss_url TEXT,
    metadata_json TEXT,
    created_at BIGINT NOT NULL,
    UNIQUE(trace_id, artifact_type, oss_url),
    FOREIGN KEY(trace_id) REFERENCES {traces_table}(trace_id) ON DELETE CASCADE
)
                    """.strip()
                )

        idx_traces_status = "idx_hsai_compose_traces_status"
        if idx_traces_status not in {
            idx["name"] for idx in inspector.get_indexes("hsai_compose_traces", schema=effective_schema)
        } if inspector.has_table("hsai_compose_traces", schema=effective_schema) else set():
            statements.append(
                f"CREATE INDEX IF NOT EXISTS {preparer.quote_identifier(idx_traces_status)} "
                f"ON {traces_table} ({preparer.quote_identifier('status')}, {preparer.quote_identifier('updated_at')})"
            )

        idx_steps_trace = "idx_hsai_compose_steps_trace"
        if idx_steps_trace not in {
            idx["name"] for idx in inspector.get_indexes("hsai_compose_steps", schema=effective_schema)
        } if inspector.has_table("hsai_compose_steps", schema=effective_schema) else set():
            statements.append(
                f"CREATE INDEX IF NOT EXISTS {preparer.quote_identifier(idx_steps_trace)} "
                f"ON {steps_table} ({preparer.quote_identifier('trace_id')}, {preparer.quote_identifier('updated_at')})"
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

