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


def ensure_coupon_schema(
    engine_or_connection: Engine | Connection,
    *,
    schema: str | None = None,
    dry_run: bool = False,
    logger: Callable[[str], None] | None = None,
) -> dict:
    """
    Ensure coupon recharge tables exist.

    Tables:
    - hsai_coupon_batches
    - hsai_coupons
    - hsai_coupon_redeem_txns
    """

    executed_statements: List[str] = []

    with _connection_from(engine_or_connection) as connection:
        inspector = inspect(connection)
        effective_schema = schema or inspector.default_schema_name
        dialect = connection.dialect.name.lower()

        batches = "hsai_coupon_batches"
        coupons = "hsai_coupons"
        redeem_txns = "hsai_coupon_redeem_txns"

        batches_table = _qualified_name(batches, effective_schema, connection=connection)
        coupons_table = _qualified_name(coupons, effective_schema, connection=connection)
        redeem_txns_table = _qualified_name(redeem_txns, effective_schema, connection=connection)

        def _datetime_type() -> str:
            if dialect == "mysql":
                return "DATETIME(6)"
            if dialect == "sqlite":
                return "DATETIME"
            return "TIMESTAMP WITH TIME ZONE"

        def _id_type() -> str:
            if dialect == "mysql":
                return "VARCHAR(64)"
            return "TEXT"

        def _decimal_type() -> str:
            if dialect == "mysql":
                return "DECIMAL(24,12)"
            # postgresql/sqlite
            return "NUMERIC(24,12)"

        statements: List[str] = []

        batches_exists = inspector.has_table(batches, schema=effective_schema)
        coupons_exists = inspector.has_table(coupons, schema=effective_schema)
        redeem_txns_exists = inspector.has_table(redeem_txns, schema=effective_schema)

        dt = _datetime_type()
        id_type = _id_type()
        dec = _decimal_type()

        if not batches_exists:
            statements.append(
                f"""
CREATE TABLE IF NOT EXISTS {batches_table} (
    id {id_type} PRIMARY KEY,
    channel VARCHAR(255) NOT NULL,
    face_value {dec} NOT NULL,
    valid_from {dt},
    expires_at {dt},
    quantity INTEGER NOT NULL,
    code_prefix VARCHAR(64),
    created_by_user_id {id_type},
    remark TEXT,
    created_at {dt} NOT NULL,
    updated_at {dt} NOT NULL
)
                """.strip()
            )

        if not coupons_exists:
            statements.append(
                f"""
CREATE TABLE IF NOT EXISTS {coupons_table} (
    id {id_type} PRIMARY KEY,
    batch_id {id_type},
    code VARCHAR(64) NOT NULL,
    channel VARCHAR(255) NOT NULL,
    face_value {dec} NOT NULL,
    valid_from {dt},
    expires_at {dt},
    status VARCHAR(16) NOT NULL,
    used_by_user_id {id_type},
    used_at {dt},
    destroyed_by_user_id {id_type},
    destroyed_at {dt},
    destroy_reason TEXT,
    created_at {dt} NOT NULL,
    updated_at {dt} NOT NULL
)
                """.strip()
            )

            # indexes
            if dialect == "mysql":
                statements.append(f"CREATE UNIQUE INDEX idx_hsai_coupons_code ON {coupons_table} (code)")
                statements.append(f"CREATE INDEX idx_hsai_coupons_status ON {coupons_table} (status)")
                statements.append(f"CREATE INDEX idx_hsai_coupons_channel ON {coupons_table} (channel)")
                statements.append(f"CREATE INDEX idx_hsai_coupons_expires_at ON {coupons_table} (expires_at)")
            else:
                statements.append(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_hsai_coupons_code ON {coupons_table} (code)"
                )
                statements.append(
                    f"CREATE INDEX IF NOT EXISTS idx_hsai_coupons_status ON {coupons_table} (status)"
                )
                statements.append(
                    f"CREATE INDEX IF NOT EXISTS idx_hsai_coupons_channel ON {coupons_table} (channel)"
                )
                statements.append(
                    f"CREATE INDEX IF NOT EXISTS idx_hsai_coupons_expires_at ON {coupons_table} (expires_at)"
                )

        if not redeem_txns_exists:
            statements.append(
                f"""
CREATE TABLE IF NOT EXISTS {redeem_txns_table} (
    id {id_type} PRIMARY KEY,
    user_id {id_type} NOT NULL,
    total_face_value {dec} NOT NULL,
    total_count INTEGER NOT NULL,
    success_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    request_fingerprint VARCHAR(128),
    client_ip VARCHAR(64),
    created_at {dt} NOT NULL
)
                """.strip()
            )

            if dialect == "mysql":
                statements.append(f"CREATE INDEX idx_hsai_coupon_redeem_txns_user_id ON {redeem_txns_table} (user_id)")
                statements.append(f"CREATE INDEX idx_hsai_coupon_redeem_txns_created_at ON {redeem_txns_table} (created_at)")
            else:
                statements.append(
                    f"CREATE INDEX IF NOT EXISTS idx_hsai_coupon_redeem_txns_user_id ON {redeem_txns_table} (user_id)"
                )
                statements.append(
                    f"CREATE INDEX IF NOT EXISTS idx_hsai_coupon_redeem_txns_created_at ON {redeem_txns_table} (created_at)"
                )

        for statement in statements:
            normalized = " ".join(statement.split())
            if normalized:
                _log(f"[coupon schema] {normalized}", logger)
            if dry_run:
                executed_statements.append(statement)
                continue
            connection.execute(text(statement))
            executed_statements.append(statement)

        if executed_statements and not dry_run:
            connection.commit()

    return {"executed": executed_statements}

