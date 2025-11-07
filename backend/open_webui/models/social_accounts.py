import logging
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from sqlalchemy import BigInteger, Column, String, Text, DateTime
from sqlalchemy import func

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", "INFO"))


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    account_url = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="active")
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class SocialAccountsTable:
    def count_active_accounts(
        self,
        company_id: Optional[str],
        platform: Optional[str] = None,
    ) -> int:
        if not company_id:
            return 0
        with get_db() as db:
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
                log.error(
                    "Failed counting social accounts company=%s platform=%s err=%s",
                    company_id,
                    platform,
                    exc,
                    exc_info=True,
                )
                return 0


SocialAccounts = SocialAccountsTable()
