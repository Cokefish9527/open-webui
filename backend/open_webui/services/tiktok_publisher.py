import logging
from typing import Literal, Optional, Dict, Any

import requests

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.hsai_oauth_handler import hsai_oauth_handler, HSAIOAuthHandler

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))


class TikTokPublisher:
    """
    封装 TikTok Content Posting API（Inbox + Direct Post）调用。
    当前实现优先使用 PULL_FROM_URL 模式，减少本地带宽占用。
    """

    def __init__(self, oauth_handler: HSAIOAuthHandler) -> None:
        self._oauth = oauth_handler

    @property
    def _config(self) -> Dict[str, str]:
        cfg = self._oauth.platform_configs.get("tiktok") or {}
        return cfg

    def _build_headers(self, access_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def init_inbox_upload(
        self,
        *,
        access_token: str,
        open_id: str,
        video_url: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        使用 PULL_FROM_URL 将视频推送到 TikTok Inbox。
        """
        api_base = self._config.get("api_base", "https://open.tiktokapis.com").rstrip("/")
        url = f"{api_base}/v2/post/publish/inbox/video/init/?open_id={open_id}"

        payload: Dict[str, Any] = {
            "post_info": {
                "description": caption or "",
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        }

        resp = requests.post(url, json=payload, headers=self._build_headers(access_token), timeout=20)
        resp.raise_for_status()
        return resp.json()

    def init_direct_post(
        self,
        *,
        access_token: str,
        open_id: str,
        video_url: str,
        caption: Optional[str] = None,
        privacy_level: str = "PRIVATE",
    ) -> Dict[str, Any]:
        """
        使用 PULL_FROM_URL 直接发帖（Direct Post）。
        未审核应用一般只能发私密视频，因此默认 privacy_level=PRIVATE。
        """
        api_base = self._config.get("api_base", "https://open.tiktokapis.com").rstrip("/")
        url = f"{api_base}/v2/post/publish/video/init/?open_id={open_id}"

        payload: Dict[str, Any] = {
            "post_info": {
                "description": caption or "",
                "privacy_level": privacy_level,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        }

        resp = requests.post(url, json=payload, headers=self._build_headers(access_token), timeout=20)
        resp.raise_for_status()
        return resp.json()


# 全局 Publisher 实例，供路由层调用
tiktok_publisher = TikTokPublisher(oauth_handler=hsai_oauth_handler)
