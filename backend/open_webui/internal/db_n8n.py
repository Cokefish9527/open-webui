"""Secondary database access for the n8n_workflow database."""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool

from open_webui.env import (
    SRC_LOG_LEVELS,
    N8N_DATABASE_URL,
    N8N_DATABASE_SCHEMA,
    N8N_DATABASE_POOL_SIZE,
    N8N_DATABASE_POOL_MAX_OVERFLOW,
    N8N_DATABASE_POOL_TIMEOUT,
    N8N_DATABASE_POOL_RECYCLE,
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
