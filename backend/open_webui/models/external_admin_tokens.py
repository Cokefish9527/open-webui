import hashlib
import time
import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, String, BigInteger

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", "INFO"))


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class ExternalAdminToken(Base):
    __tablename__ = "external_admin_tokens"

    id = Column(String, primary_key=True)
    client_id = Column(String, nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(BigInteger, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    revoked = Column(Boolean, default=False)


class ExternalAdminTokenModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Token记录ID")
    client_id: str = Field(description="客户端标识")
    expires_at: int = Field(description="过期时间戳")
    created_at: int = Field(description="创建时间戳")
    revoked: bool = Field(description="是否已吊销")


class ExternalAdminTokenTable:
    def issue_token(self, client_id: str, raw_token: str, ttl_seconds: int) -> Optional[ExternalAdminTokenModel]:
        now = int(time.time())
        record = ExternalAdminToken(
            id=str(uuid.uuid4()),
            client_id=client_id,
            token_hash=_hash_token(raw_token),
            created_at=now,
            expires_at=now + ttl_seconds,
            revoked=False,
        )
        try:
            with get_db() as db:
                db.add(record)
                db.commit()
                db.refresh(record)
                return ExternalAdminTokenModel.model_validate(record)
        except Exception as exc:
            log.exception("Failed to persist external admin token: %s", exc)
            return None

    def get_valid_token(self, raw_token: str) -> Optional[ExternalAdminTokenModel]:
        hashed = _hash_token(raw_token)
        now = int(time.time())
        with get_db() as db:
            token = (
                db.query(ExternalAdminToken)
                .filter_by(token_hash=hashed, revoked=False)
                .filter(ExternalAdminToken.expires_at > now)
                .first()
            )
            return ExternalAdminTokenModel.model_validate(token) if token else None

    def revoke_token(self, raw_token: str) -> bool:
        hashed = _hash_token(raw_token)
        with get_db() as db:
            updated = (
                db.query(ExternalAdminToken)
                .filter_by(token_hash=hashed)
                .update({"revoked": True})
            )
            db.commit()
            return bool(updated)

    def cleanup_expired(self) -> int:
        now = int(time.time())
        with get_db() as db:
            deleted = (
                db.query(ExternalAdminToken)
                .filter(ExternalAdminToken.expires_at <= now)
                .delete()
            )
            db.commit()
            return int(deleted)


ExternalAdminTokens = ExternalAdminTokenTable()
