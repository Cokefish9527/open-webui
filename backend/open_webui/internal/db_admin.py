"""Secondary database access for the Owen Admin (task templates) database."""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool

from open_webui.env import (
    SRC_LOG_LEVELS,
    ADMIN_DATABASE_URL,
    ADMIN_DATABASE_SCHEMA,
    ADMIN_DATABASE_POOL_SIZE,
    ADMIN_DATABASE_POOL_MAX_OVERFLOW,
    ADMIN_DATABASE_POOL_TIMEOUT,
    ADMIN_DATABASE_POOL_RECYCLE,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("DB", "INFO"))


SQLALCHEMY_DATABASE_URL = ADMIN_DATABASE_URL

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

    admin_engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    if ADMIN_DATABASE_POOL_SIZE and ADMIN_DATABASE_POOL_SIZE > 0:
        admin_engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=ADMIN_DATABASE_POOL_SIZE,
            max_overflow=ADMIN_DATABASE_POOL_MAX_OVERFLOW,
            pool_timeout=ADMIN_DATABASE_POOL_TIMEOUT,
            pool_recycle=ADMIN_DATABASE_POOL_RECYCLE,
            pool_pre_ping=True,
            poolclass=QueuePool,
        )
    else:
        admin_engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_pre_ping=True,
            poolclass=NullPool,
        )


AdminSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=admin_engine,
    expire_on_commit=False,
)
admin_metadata = MetaData(schema=ADMIN_DATABASE_SCHEMA)
AdminBase = declarative_base(metadata=admin_metadata)
AdminSession = scoped_session(AdminSessionLocal)


def _get_session():
    db = AdminSessionLocal()
    try:
        yield db
    finally:
        db.close()


get_admin_db = contextmanager(_get_session)
