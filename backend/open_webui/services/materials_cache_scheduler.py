import asyncio
import logging
from typing import Optional

from redis.asyncio import Redis

from open_webui.env import (
    HSAI_MATERIALS_CACHE_ENABLED,
    HSAI_MATERIALS_CACHE_REFRESH_INTERVAL_SEC,
    SRC_LOG_LEVELS,
)
from open_webui.services.materials_cache_service import (
    ACTIVE_COMPANIES_SET_KEY,
    MaterialsCacheService,
    company_folders_cache_key,
    company_index_cache_key,
)
from open_webui.services.materials_oss_sync_service import MaterialsOssSyncService
from open_webui.services.materials_snapshot_service import (
    build_company_folders_snapshot,
    build_company_material_index_snapshot,
    pick_any_user_id_for_company,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


class MaterialsCacheScheduler:
    def __init__(self, redis: Optional[Redis]) -> None:
        self.redis = redis
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._syncer = MaterialsOssSyncService()
        self._cache = MaterialsCacheService(redis)

    async def start(self) -> None:
        if self._running:
            return
        if not HSAI_MATERIALS_CACHE_ENABLED or self.redis is None:
            log.info("Materials cache scheduler disabled (cache=%s redis=%s)", HSAI_MATERIALS_CACHE_ENABLED, bool(self.redis))
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        log.info("Materials cache scheduler started interval=%ss", HSAI_MATERIALS_CACHE_REFRESH_INTERVAL_SEC)

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        log.info("Materials cache scheduler stopped")

    async def _run_loop(self) -> None:
        interval = max(int(HSAI_MATERIALS_CACHE_REFRESH_INTERVAL_SEC), 30)
        while self._running:
            try:
                await self._refresh_once()
            except Exception as exc:  # noqa: BLE001
                log.warning("Materials cache scheduler loop error: %s", exc, exc_info=True)
            await asyncio.sleep(interval)

    async def _refresh_once(self) -> None:
        if self.redis is None:
            return
        company_ids = await self.redis.smembers(ACTIVE_COMPANIES_SET_KEY)
        if not company_ids:
            return

        for raw_company_id in company_ids:
            company_id = raw_company_id.decode("utf-8") if isinstance(raw_company_id, bytes) else str(raw_company_id)
            if not company_id:
                continue

            # 预热/刷新：OSS -> DB -> rebuild cache
            actor_user_id = await asyncio.to_thread(pick_any_user_id_for_company, company_id)
            if not actor_user_id:
                continue
            await asyncio.to_thread(self._syncer.sync_company, company_id=company_id, actor_user_id=actor_user_id)
            folders_snapshot = await asyncio.to_thread(build_company_folders_snapshot, company_id=company_id)
            index_snapshot = await asyncio.to_thread(build_company_material_index_snapshot, company_id=company_id)

            await self._cache.set_json(company_folders_cache_key(company_id), folders_snapshot)
            await self._cache.set_json(company_index_cache_key(company_id), index_snapshot)
