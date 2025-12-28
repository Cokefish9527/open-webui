import logging
import os
from typing import Any, Dict, Optional, Tuple

import aiohttp

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

DEFAULT_N8N_UPDATE_HOT_VIDEO_META_URL = os.getenv(
    "N8N_UPDATE_HOT_VIDEO_META_URL",
    "https://webhook-n8n.hsai.cc/webhook/update_hot_video_meta",
)
DEFAULT_N8N_UPDATE_VIDEO_META_URL = os.getenv(
    "N8N_UPDATE_VIDEO_META_URL",
    "https://webhook-n8n.hsai.cc/webhook/update_video_meta",
)


async def post_json(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout_seconds: int = 15,
) -> Tuple[int, Optional[Dict[str, Any]], str]:
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
        async with session.post(url, json=payload) as resp:
            text = await resp.text()
            try:
                data = await resp.json()
            except Exception:
                data = None
            return resp.status, data, text

