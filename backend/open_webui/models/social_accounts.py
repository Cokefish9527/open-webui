import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from threading import Lock

from open_webui.env import DATABASE_SCHEMA, SRC_LOG_LEVELS
from open_webui.internal.db import Base, get_db
from open_webui.internal.migrations import ensure_social_accounts_schema

from sqlalchemy import BigInteger, Column, String, Text, DateTime
from sqlalchemy import func

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", "INFO"))

_SCHEMA_LOCK = Lock()
_SCHEMA_READY = False


def _ensure_social_accounts_schema(session) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        ensure_social_accounts_schema(
            session.get_bind(),
            schema=DATABASE_SCHEMA,
            logger=log.debug,
        )
        _SCHEMA_READY = True


@contextmanager
def _schema_aware_db():
    with get_db() as db:
        _ensure_social_accounts_schema(db)
        yield db


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    account_url = Column(Text, nullable=True)
    # 绑定操作的 OwenAI 用户（可选）
    owner_user_id = Column(String, nullable=True)
    # OAuth 相关字段（TikTok 等平台使用）
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    scope = Column(Text, nullable=True)
    token_type = Column(String, nullable=True)
    open_id = Column(String, nullable=True)
    # 预留 JSON 文本，用于存储平台特有字段
    extra = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="active")
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class SocialAccountsTable:
    def get_account_by_id(self, account_id: int) -> Optional[SocialAccount]:
        """根据主键获取社交账号记录。"""
        with _schema_aware_db() as db:
            try:
                return db.get(SocialAccount, account_id)
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed getting social account id=%s err=%s", account_id, exc, exc_info=True)
                return None

    def get_accounts_by_company(
        self,
        company_id: Optional[str],
        platform: Optional[str] = None,
    ) -> List[SocialAccount]:
        """按公司与平台列出社交账号。"""
        if not company_id:
            return []
        with _schema_aware_db() as db:
            try:
                query = db.query(SocialAccount).filter(
                    SocialAccount.company_id == company_id,
                    SocialAccount.status == "active",
                )
                if platform:
                    query = query.filter(
                        func.lower(SocialAccount.platform) == func.lower(platform)
                    )
                return list(query.order_by(SocialAccount.id.asc()).all())
            except Exception as exc:  # pylint: disable=broad-except
                log.error(
                    "Failed listing social accounts company=%s platform=%s err=%s",
                    company_id,
                    platform,
                    exc,
                    exc_info=True,
                )
                return []

    def count_active_accounts(
        self,
        company_id: Optional[str],
        platform: Optional[str] = None,
    ) -> int:
        if not company_id:
            return 0
        with _schema_aware_db() as db:
            try:
                query = db.query(func.count(SocialAccount.id)).filter(
                    SocialAccount.company_id == company_id,
                    SocialAccount.status == "active",
                )
                if platform:
                    query = query.filter(
                        func.lower(SocialAccount.platform) == func.lower(platform)
                    )
                return query.scalar() or 0
            except Exception as exc:  # pylint: disable=broad-except
                try:
                    db.rollback()
                except Exception:  # pragma: no cover
                    pass
                log.error(
                    "Failed counting social accounts company=%s platform=%s err=%s",
                    company_id,
                    platform,
                    exc,
                    exc_info=True,
                )
                return 0

    # ---- TikTok 专用辅助方法 ----

    def upsert_tiktok_account(
        self,
        *,
        company_id: str,
        owner_user_id: Optional[str],
        account_name: str,
        account_id: str,
        account_url: Optional[str],
        token_data: Dict[str, Any],
        user_info: Dict[str, Any],
    ) -> Optional[SocialAccount]:
        """根据 TikTok OAuth token / user_info 创建或更新社交账号记录。"""
        if not company_id:
            return None

        platform = "tiktok"
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        scope = token_data.get("scope")
        token_type = token_data.get("token_type")
        open_id = token_data.get("open_id") or token_data.get("openId") or token_data.get("open_id_v2")
        expires_in = token_data.get("expires_in")

        token_expires_at: Optional[datetime] = None
        if isinstance(expires_in, (int, float)) and expires_in > 0:
            token_expires_at = datetime.fromtimestamp(
                datetime.now(tz=timezone.utc).timestamp() + float(expires_in),
                tz=timezone.utc,
            )

        display_name = user_info.get("display_name") or user_info.get("username") or account_name
        avatar_url = user_info.get("avatar_url") or ""

        now = datetime.now(tz=timezone.utc)

        with _schema_aware_db() as db:
            try:
                query = db.query(SocialAccount).filter(
                    SocialAccount.company_id == company_id,
                    func.lower(SocialAccount.platform) == func.lower(platform),
                )
                if open_id:
                    query = query.filter(SocialAccount.open_id == open_id)
                else:
                    query = query.filter(SocialAccount.account_id == account_id)

                existing: Optional[SocialAccount] = query.first()

                if existing:
                    existing.account_name = display_name or account_name
                    existing.account_id = account_id
                    existing.account_url = account_url
                    existing.owner_user_id = owner_user_id or existing.owner_user_id
                    existing.access_token = access_token or existing.access_token
                    existing.refresh_token = refresh_token or existing.refresh_token
                    existing.scope = scope or existing.scope
                    existing.token_type = token_type or existing.token_type
                    existing.open_id = open_id or existing.open_id
                    existing.status = "active"
                    existing.token_expires_at = token_expires_at or existing.token_expires_at
                    existing.updated_at = now
                    db.add(existing)
                    db.commit()
                    db.refresh(existing)
                    return existing

                account = SocialAccount(
                    company_id=company_id,
                    platform=platform,
                    account_name=display_name or account_name,
                    account_id=account_id,
                    account_url=account_url,
                    owner_user_id=owner_user_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    scope=scope,
                    token_type=token_type,
                    open_id=open_id,
                    status="active",
                    token_expires_at=token_expires_at,
                    created_at=now,
                    updated_at=now,
                )
                db.add(account)
                db.commit()
                db.refresh(account)
                return account
            except Exception as exc:  # pylint: disable=broad-except
                try:
                    db.rollback()
                except Exception:  # pragma: no cover
                    pass
                log.error(
                    "Failed upserting TikTok social account company=%s open_id=%s account_id=%s err=%s",
                    company_id,
                    open_id,
                    account_id,
                    exc,
                    exc_info=True,
                )
                return None

    def update_token(
        self,
        account_id: int,
        *,
        access_token: str,
        refresh_token: Optional[str],
        expires_in: Optional[int],
        scope: Optional[str] = None,
        token_type: Optional[str] = None,
    ) -> bool:
        """刷新已存在账号的 token。"""
        with _schema_aware_db() as db:
            try:
                account = db.get(SocialAccount, account_id)
                if not account:
                    return False

                account.access_token = access_token
                if refresh_token:
                    account.refresh_token = refresh_token
                if scope:
                    account.scope = scope
                if token_type:
                    account.token_type = token_type

                if isinstance(expires_in, (int, float)) and expires_in > 0:
                    account.token_expires_at = datetime.fromtimestamp(
                        datetime.now(tz=timezone.utc).timestamp() + float(expires_in),
                        tz=timezone.utc,
                    )

                account.updated_at = datetime.now(tz=timezone.utc)
                db.add(account)
                db.commit()
                return True
            except Exception as exc:  # pylint: disable=broad-except
                try:
                    db.rollback()
                except Exception:  # pragma: no cover
                    pass
                log.error("Failed updating token for social account %s err=%s", account_id, exc, exc_info=True)
                return False

    def get_active_tiktok_account_by_open_id(self, open_id: str) -> Optional[SocialAccount]:
        """
        按 TikTok open_id 查找已绑定的 active 账号。

        说明：
        - 现有实现中，TikTok 的 open_id 同时会写入 `open_id` 字段，
          且 `account_id` 通常也会保存 open_id（兼容老数据）。
        - 若存在多条匹配记录（理论上不应出现），返回最近更新的一条。
        """
        if not open_id:
            return None
        with _schema_aware_db() as db:
            try:
                query = (
                    db.query(SocialAccount)
                    .filter(
                        func.lower(SocialAccount.platform) == func.lower("tiktok"),
                        SocialAccount.status == "active",
                        (
                            (SocialAccount.open_id == open_id)
                            | (SocialAccount.account_id == open_id)
                        ),
                    )
                    .order_by(SocialAccount.updated_at.desc().nullslast(), SocialAccount.id.desc())
                )
                return query.first()
            except Exception as exc:  # pylint: disable=broad-except
                try:
                    db.rollback()
                except Exception:  # pragma: no cover
                    pass
                log.error("Failed getting TikTok account by open_id=%s err=%s", open_id, exc, exc_info=True)
                return None

    def set_owner_user_id(self, account_id: int, owner_user_id: Optional[str]) -> bool:
        """为社交账号记录设置 owner_user_id（用于 SSO 自动关联）。"""
        with _schema_aware_db() as db:
            try:
                updated = (
                    db.query(SocialAccount)
                    .filter(SocialAccount.id == account_id)
                    .update(
                        {
                            "owner_user_id": owner_user_id,
                            "updated_at": datetime.now(tz=timezone.utc),
                        }
                    )
                )
                db.commit()
                return True if updated == 1 else False
            except Exception as exc:  # pylint: disable=broad-except
                try:
                    db.rollback()
                except Exception:  # pragma: no cover
                    pass
                log.error(
                    "Failed setting owner_user_id for social account %s err=%s",
                    account_id,
                    exc,
                    exc_info=True,
                )
                return False


SocialAccounts = SocialAccountsTable()
