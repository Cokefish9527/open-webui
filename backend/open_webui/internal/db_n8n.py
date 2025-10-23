"""Secondary database access for the n8n_workflow database."""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import SQLAlchemyError

from open_webui.env import (
    SRC_LOG_LEVELS,
    N8N_DATABASE_URL,
    N8N_DATABASE_SCHEMA,
    N8N_DATABASE_POOL_SIZE,
    N8N_DATABASE_POOL_MAX_OVERFLOW,
    N8N_DATABASE_POOL_TIMEOUT,
    N8N_DATABASE_POOL_RECYCLE,
    ENV_REQUIRE_N8N,
    N8N_REQUIRED_TABLES,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


SQLALCHEMY_DATABASE_URL = N8N_DATABASE_URL

if "sqlite" in SQLALCHEMY_DATABASE_URL.lower():
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            dsn = str(dbapi_connection)
            if "sqlite" in dsn.lower():
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        except Exception:
            pass

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    if N8N_DATABASE_POOL_SIZE > 0:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=N8N_DATABASE_POOL_SIZE,
            max_overflow=N8N_DATABASE_POOL_MAX_OVERFLOW,
            pool_timeout=N8N_DATABASE_POOL_TIMEOUT,
            pool_recycle=N8N_DATABASE_POOL_RECYCLE,
            pool_pre_ping=True,
            poolclass=QueuePool,
        )
    else:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_pre_ping=True,
            poolclass=NullPool,
        )


def _validate_required_tables() -> None:
    if not ENV_REQUIRE_N8N:
        log.debug("ENV_REQUIRE_N8N is false; skipping n8n schema validation.")
        return
    if "sqlite" in SQLALCHEMY_DATABASE_URL.lower():
        log.debug("Detected sqlite n8n backend; skipping schema validation.")
        return
    required_tables = [table for table in N8N_REQUIRED_TABLES if table]
    if not required_tables:
        log.debug("No required tables configured for n8n; skipping validation.")
        return
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            available_tables = set(
                inspector.get_table_names(schema=N8N_DATABASE_SCHEMA)
            )
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "无法连接到 n8n_workflow 数据库，请检查 N8N_DATABASE_URL / N8N_DATABASE_SCHEMA 配置。"
        ) from exc

    missing = [
        table for table in required_tables if table not in available_tables
    ]
    if missing:
        raise RuntimeError(
            "n8n_workflow 数据库缺少必要数据表："
            f"{', '.join(missing)}（schema={N8N_DATABASE_SCHEMA or '默认'}）。"
            "请确认已经在目标库中创建这些表，或通过 ENV_REQUIRE_N8N=false 临时跳过校验。"
        )
    log.info(
        "n8n_workflow 数据库校验通过，已检测到数据表：%s",
        ", ".join(sorted(required_tables)),
    )


_validate_required_tables()


SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)
metadata_obj = MetaData(schema=N8N_DATABASE_SCHEMA)
N8NBase = declarative_base(metadata=metadata_obj)
N8NSession = scoped_session(SessionLocal)


def _get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


get_n8n_db = contextmanager(_get_session)
