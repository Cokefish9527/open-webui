import asyncio
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
    timeout_seconds: int = 30,
    max_retries: int = 2,
) -> Tuple[int, Optional[Dict[str, Any]], str]:
    """
    向 n8n webhook 发送 JSON 请求,支持超时和重试。
    
    Args:
        url: webhook URL
        payload: JSON payload
        timeout_seconds: 请求超时时间(秒),默认 30 秒
        max_retries: 最大重试次数,默认 2 次
        
    Returns:
        (status_code, json_data, raw_text) 元组
        
    Raises:
        aiohttp.ClientError: 网络错误
        asyncio.TimeoutError: 超时错误
    """
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                log.info(f"POST {url} (attempt {attempt + 1}/{max_retries + 1}, timeout={timeout_seconds}s)")
                async with session.post(url, json=payload) as resp:
                    text = await resp.text()
                    try:
                        data = await resp.json()
                    except Exception:
                        data = None
                    
                    status = resp.status
                    
                    # 成功或客户端错误(4xx)不重试
                    if status < 500:
                        if status >= 400:
                            log.warning(f"n8n webhook returned {status}: {text[:200]}")
                        return status, data, text
                    
                    # 5xx 错误记录并重试
                    log.warning(f"n8n webhook returned {status}, will retry if attempts remain")
                    last_error = Exception(f"HTTP {status}: {text[:200]}")
                    
        except asyncio.TimeoutError as e:
            log.warning(f"n8n webhook timeout after {timeout_seconds}s (attempt {attempt + 1}/{max_retries + 1})")
            last_error = e
            
        except aiohttp.ClientError as e:
            log.warning(f"n8n webhook client error: {e} (attempt {attempt + 1}/{max_retries + 1})")
            last_error = e
        
        # 如果还有重试机会,等待后重试(指数退避)
        if attempt < max_retries:
            wait_time = 2 ** attempt  # 1s, 2s, 4s...
            log.info(f"Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
    
    # 所有重试都失败,抛出最后一个错误
    log.error(f"n8n webhook failed after {max_retries + 1} attempts")
    raise last_error

