import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Text, String, func

from open_webui.env import DATABASE_SCHEMA, SRC_LOG_LEVELS
from open_webui.internal.db import Base, get_db
from open_webui.internal.migrations.minimax_accounts import ensure_minimax_accounts_schema

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", "INFO"))

_SCHEMA_LOCK = Lock()
_SCHEMA_READY = False


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _ensure_schema(session) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        ensure_minimax_accounts_schema(
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


class HSAIMiniMaxAccount(Base):
    __tablename__ = "hsai_minimax_accounts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)
    api_key = Column(Text, nullable=True)
    group_id = Column(String(128), nullable=True)
    meta_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True, default=func.now())
    updated_at = Column(DateTime, nullable=True, default=func.now(), onupdate=func.now())


def _mask_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    s = str(value).strip()
    if len(s) <= 8:
        return "*" * len(s)
    return f"{s[:4]}****{s[-4:]}"


class MiniMaxAccountsTable:
    def list_accounts(self) -> List[HSAIMiniMaxAccount]:
        with _schema_aware_db() as db:
            return list(db.query(HSAIMiniMaxAccount).order_by(HSAIMiniMaxAccount.id.asc()).all())

    def get_account(self, account_id: int) -> Optional[HSAIMiniMaxAccount]:
        with _schema_aware_db() as db:
            try:
                return db.get(HSAIMiniMaxAccount, int(account_id))
            except Exception:  # pragma: no cover
                return None

    def get_default_account(self) -> Optional[HSAIMiniMaxAccount]:
        with _schema_aware_db() as db:
            return (
                db.query(HSAIMiniMaxAccount)
                .filter(HSAIMiniMaxAccount.enabled.is_(True))
                .filter(HSAIMiniMaxAccount.is_default.is_(True))
                .order_by(HSAIMiniMaxAccount.id.asc())
                .first()
            )

    def create_account(
        self,
        *,
        name: str,
        api_key: Optional[str],
        group_id: Optional[str],
        enabled: bool = True,
        is_default: bool = False,
        meta_json: Optional[str] = None,
    ) -> HSAIMiniMaxAccount:
        now = _utcnow()
        with _schema_aware_db() as db:
            if is_default:
                db.query(HSAIMiniMaxAccount).update({"is_default": False})
                db.commit()

            account = HSAIMiniMaxAccount(
                name=str(name).strip(),
                api_key=(str(api_key).strip() if api_key else None),
                group_id=(str(group_id).strip() if group_id else None),
                enabled=bool(enabled),
                is_default=bool(is_default),
                meta_json=meta_json,
                created_at=now,
                updated_at=now,
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            return account

    def update_account(
        self,
        account_id: int,
        *,
        name: Optional[str] = None,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None,
        enabled: Optional[bool] = None,
        is_default: Optional[bool] = None,
        meta_json: Optional[str] = None,
        clear_api_key: bool = False,
    ) -> Optional[HSAIMiniMaxAccount]:
        with _schema_aware_db() as db:
            account = db.get(HSAIMiniMaxAccount, int(account_id))
            if not account:
                return None

            if is_default is True:
                db.query(HSAIMiniMaxAccount).update({"is_default": False})
                db.commit()
                account.is_default = True
            elif is_default is False:
                account.is_default = False

            if name is not None:
                account.name = str(name).strip()
            if group_id is not None:
                account.group_id = str(group_id).strip() if str(group_id).strip() else None
            if enabled is not None:
                account.enabled = bool(enabled)

            if clear_api_key:
                account.api_key = None
            elif api_key is not None:
                account.api_key = str(api_key).strip() if str(api_key).strip() else None

            if meta_json is not None:
                account.meta_json = meta_json

            account.updated_at = _utcnow()
            db.add(account)
            db.commit()
            db.refresh(account)
            return account

    def delete_account(self, account_id: int) -> bool:
        with _schema_aware_db() as db:
            account = db.get(HSAIMiniMaxAccount, int(account_id))
            if not account:
                return False
            db.delete(account)
            db.commit()
            return True

    def to_safe_dict(self, account: HSAIMiniMaxAccount) -> Dict[str, Any]:
        return {
            "id": int(getattr(account, "id", 0) or 0),
            "name": getattr(account, "name", None),
            "enabled": bool(getattr(account, "enabled", False)),
            "is_default": bool(getattr(account, "is_default", False)),
            "group_id": getattr(account, "group_id", None),
            "has_api_key": bool(getattr(account, "api_key", None)),
            "api_key_masked": _mask_secret(getattr(account, "api_key", None)),
            "meta_json": getattr(account, "meta_json", None),
            "created_at": getattr(account, "created_at", None),
            "updated_at": getattr(account, "updated_at", None),
        }

    def resolve_credentials(
        self,
        *,
        account_id: Optional[int],
        allow_fallback_env: bool = False,
        env_api_key: Optional[str] = None,
        env_group_id: Optional[str] = None,
    ) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Returns (resolved_account_id, api_key, group_id).
        - If account_id is None: use default enabled account.
        - If not found/disabled and allow_fallback_env: use env credentials.
        """
        resolved: Optional[HSAIMiniMaxAccount] = None
        if account_id is None:
            resolved = self.get_default_account()
        else:
            resolved = self.get_account(int(account_id))
            if resolved and not bool(getattr(resolved, "enabled", False)):
                resolved = None

        if resolved and getattr(resolved, "api_key", None):
            return int(resolved.id), str(resolved.api_key), getattr(resolved, "group_id", None)

        if allow_fallback_env and env_api_key:
            return None, env_api_key, env_group_id

        return None, None, None


MiniMaxAccounts = MiniMaxAccountsTable()

