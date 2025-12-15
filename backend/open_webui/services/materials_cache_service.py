import json
import logging
from typing import Any, Optional

from redis.asyncio import Redis

from open_webui.env import (
    HSAI_MATERIALS_CACHE_ENABLED,
    HSAI_MATERIALS_CACHE_TTL_SEC,
    SRC_LOG_LEVELS,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


_CACHE_VERSION = "v2"


def company_folders_cache_key(company_id: str) -> str:
    return f"open-webui:materials:{_CACHE_VERSION}:folders:company:{company_id}"


def company_index_cache_key(company_id: str) -> str:
    return f"open-webui:materials:{_CACHE_VERSION}:index:company:{company_id}"


ACTIVE_COMPANIES_SET_KEY = f"open-webui:materials:{_CACHE_VERSION}:active_companies"


class MaterialsCacheService:
    def __init__(self, redis: Optional[Redis]) -> None:
        self.redis = redis

    def enabled(self) -> bool:
        return bool(HSAI_MATERIALS_CACHE_ENABLED) and self.redis is not None

    async def mark_company_active(self, company_id: str) -> None:
        if not self.enabled():
            return
        try:
            assert self.redis is not None
            pipe = self.redis.pipeline()
            pipe.sadd(ACTIVE_COMPANIES_SET_KEY, company_id)
            pipe.expire(ACTIVE_COMPANIES_SET_KEY, 7 * 24 * 3600)
            await pipe.execute()
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to mark company active for materials cache: %s", exc)

    async def get_json(self, key: str) -> Optional[Any]:
        if not self.enabled():
            return None
        try:
            assert self.redis is not None
            raw = await self.redis.get(key)
            if not raw:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to read materials cache key=%s err=%s", key, exc)
            return None

    async def set_json(self, key: str, value: Any, *, ttl_sec: Optional[int] = None) -> None:
        if not self.enabled():
            return
        ttl = int(ttl_sec or HSAI_MATERIALS_CACHE_TTL_SEC)
        try:
            assert self.redis is not None
            payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            await self.redis.set(key, payload, ex=ttl)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to write materials cache key=%s err=%s", key, exc)

    async def invalidate_company(self, company_id: str) -> None:
        if not self.enabled():
            return
        try:
            assert self.redis is not None
            await self.redis.delete(
                company_folders_cache_key(company_id),
                company_index_cache_key(company_id),
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to invalidate materials cache company=%s err=%s", company_id, exc)
