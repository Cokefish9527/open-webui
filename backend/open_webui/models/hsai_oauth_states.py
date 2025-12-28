import json
import logging
import time
from contextlib import contextmanager
from threading import Lock
from typing import Any, Dict, Optional

from sqlalchemy import Column, String, Text, BigInteger

from open_webui.env import DATABASE_SCHEMA, SRC_LOG_LEVELS
from open_webui.internal.db import Base, get_db
from open_webui.internal.migrations import ensure_hsai_oauth_states_schema

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", "INFO"))

_SCHEMA_LOCK = Lock()
_SCHEMA_READY = False


def _ensure_schema(session) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        ensure_hsai_oauth_states_schema(
            session.get_bind(),
            schema=DATABASE_SCHEMA,
            logger=log.debug,
        )
        _SCHEMA_READY = True


@contextmanager
def _schema_aware_db():
    with get_db() as db:
        _ensure_schema(db)
        yield db


class HSAIOAuthState(Base):
    __tablename__ = "hsai_oauth_states"

    state = Column(String, primary_key=True)
    payload_json = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    expires_at = Column(BigInteger, nullable=False)


class HSAIOAuthStatesTable:
    def _now(self) -> int:
        return int(time.time())

    def upsert_state(self, state: str, payload: Dict[str, Any], ttl_seconds: int = 600) -> bool:
        if not state:
            return False
        now = self._now()
        expires_at = now + max(1, int(ttl_seconds))

        with _schema_aware_db() as db:
            try:
                record = db.get(HSAIOAuthState, state)
                payload_str = json.dumps(payload, ensure_ascii=False)
                if record:
                    record.payload_json = payload_str
                    record.created_at = now
                    record.expires_at = expires_at
                    db.add(record)
                else:
                    db.add(
                        HSAIOAuthState(
                            state=state,
                            payload_json=payload_str,
                            created_at=now,
                            expires_at=expires_at,
                        )
                    )
                db.commit()
                return True
            except Exception as exc:  # pylint: disable=broad-except
                try:
                    db.rollback()
                except Exception:  # pragma: no cover
                    pass
                log.warning("Failed upserting oauth state=%s err=%s", state, exc, exc_info=True)
                return False

    def pop_state(self, state: str) -> Optional[Dict[str, Any]]:
        if not state:
            return None
        now = self._now()

        with _schema_aware_db() as db:
            try:
                record = db.get(HSAIOAuthState, state)
                if not record:
                    return None
                payload_str = record.payload_json
                expires_at = int(getattr(record, "expires_at", 0) or 0)

                db.delete(record)
                db.commit()

                if expires_at and expires_at < now:
                    return None
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    return payload if isinstance(payload, dict) else None
                except Exception:
                    return None
            except Exception as exc:  # pylint: disable=broad-except
                try:
                    db.rollback()
                except Exception:  # pragma: no cover
                    pass
                log.warning("Failed popping oauth state=%s err=%s", state, exc, exc_info=True)
                return None


HSAIOAuthStates = HSAIOAuthStatesTable()

