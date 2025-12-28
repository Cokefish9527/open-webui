import base64
import hashlib
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from urllib.parse import urlencode

import requests

from open_webui.models.social_accounts import SocialAccounts
from open_webui.models.hsai_oauth_states import HSAIOAuthStates

log = logging.getLogger(__name__)


class HSAIOAuthHandler:
    """
    HSAI OAuth 处理器：目前聚焦 TikTok Login Kit，用于绑定业务公司与 TikTok 账号。

    设计约束：
    - 仅在后端生成 OAuth URL 与处理回调；
    - 使用内存 state_storage 保存 state/code_verifier（生产可替换为 Redis）；
    - Tokens 持久化存入 social_accounts 表。
    """

    def __init__(self) -> None:
        self.platform_configs: Dict[str, Dict[str, str]] = {
            "tiktok": {
                # TikTok v2 Login Kit / Content Posting
                "client_key": os.getenv("TIKTOK_CLIENT_KEY", "").strip(),
                "client_secret": os.getenv("TIKTOK_CLIENT_SECRET", "").strip(),
                "scope": os.getenv(
                    "TIKTOK_SCOPES",
                    "user.info.basic,video.upload,video.publish",
                ),
                "authorize_url": "https://www.tiktok.com/v2/auth/authorize/",
                "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
                "api_base": "https://open.tiktokapis.com",
            },
        }

        # 存储 state 参数的临时字典（生产建议替换为 Redis）
        self.state_storage: Dict[str, Dict[str, Any]] = {}
        self.state_ttl_seconds = int(os.getenv("HSAI_OAUTH_STATE_TTL_SECONDS", "600"))

    # ------------------------------------------------------------------
    # OAuth URL 生成（带 PKCE）
    # ------------------------------------------------------------------
    def generate_oauth_url(
        self,
        platform_type: str,
        redirect_uri: str,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        purpose: str = "connect",
    ) -> Dict[str, str]:
        """
        生成 OAuth 授权 URL（TikTok Login Kit）。
        """
        config = self.platform_configs.get(platform_type)
        if not config:
            raise ValueError(f"Unsupported platform: {platform_type}")

        if platform_type == "tiktok" and (not config.get("client_key") or not config.get("client_secret")):
            raise ValueError("TikTok client_key/client_secret not configured")

        # state 防 CSRF
        state = self._generate_state()
        code_verifier, code_challenge = self._generate_pkce_pair()

        # 临时保存 state 对应的上下文
        state_payload = {
            "user_id": user_id,
            "company_id": company_id,
            "platform_type": platform_type,
            "purpose": purpose,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "created_at": time.time(),
        }
        self.state_storage[state] = state_payload
        try:
            HSAIOAuthStates.upsert_state(state, state_payload, ttl_seconds=self.state_ttl_seconds)
        except Exception:  # pragma: no cover
            pass

        if platform_type == "tiktok":
            auth_params = {
                "client_key": config["client_key"],
                "redirect_uri": redirect_uri,
                "scope": config["scope"],
                "response_type": "code",
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        else:
            raise ValueError(f"Unsupported platform for OAuth URL: {platform_type}")

        authorization_url = f"{config['authorize_url']}?{urlencode(auth_params)}"
        return {
            "authorization_url": authorization_url,
            "state": state,
        }

    # ------------------------------------------------------------------
    # OAuth Callback 处理
    # ------------------------------------------------------------------
    def handle_oauth_callback(
        self,
        platform_type: str,
        code: str,
        state: str,
    ) -> Dict[str, Any]:
        """
        处理 OAuth 回调，交换 access_token 并持久化账号信息。
        返回 token_data + user_info + account 元信息，用于调用方进一步处理。
        """
        state_data = self.state_storage.pop(state, None)
        if not state_data:
            state_data = HSAIOAuthStates.pop_state(state)
        if not state_data:
            raise ValueError("Invalid or expired state parameter")

        if time.time() - float(state_data.get("created_at", 0)) > float(self.state_ttl_seconds):
            raise ValueError("State parameter expired")

        if platform_type != state_data.get("platform_type"):
            raise ValueError("Platform mismatch in state")

        if platform_type == "tiktok":
            token_data = self._exchange_tiktok_token(code, state_data)
            user_info = self._get_tiktok_user_info(token_data)
            account = self._create_or_update_tiktok_account(
                state_data=state_data,
                token_data=token_data,
                user_info=user_info,
            )
        else:
            raise ValueError(f"Unsupported platform in callback: {platform_type}")

        return {
            "platform_type": platform_type,
            "token_data": token_data,
            "user_info": user_info,
            "account_id": getattr(account, "id", None) if account else None,
            "purpose": state_data.get("purpose"),
            "redirect_uri": state_data.get("redirect_uri"),
        }

    def handle_tiktok_sso_callback(self, *, code: str, state: str) -> Dict[str, Any]:
        """
        TikTok SSO 专用回调处理：
        - 仅交换 token 并拉取 user_info
        - 不落库 social_accounts（SSO 场景不一定具备 company_id）
        """
        state_data = self.state_storage.pop(state, None)
        if not state_data:
            state_data = HSAIOAuthStates.pop_state(state)
        if not state_data:
            raise ValueError("Invalid or expired state parameter")

        if time.time() - float(state_data.get("created_at", 0)) > float(self.state_ttl_seconds):
            raise ValueError("State parameter expired")

        if state_data.get("platform_type") != "tiktok":
            raise ValueError("Platform mismatch in state")

        token_data = self._exchange_tiktok_token(code, state_data)
        user_info = self._get_tiktok_user_info(token_data)
        return {
            "platform_type": "tiktok",
            "token_data": token_data,
            "user_info": user_info,
            "purpose": state_data.get("purpose") or "sso",
            "redirect_uri": state_data.get("redirect_uri"),
        }

    # ------------------------------------------------------------------
    # Token 刷新
    # ------------------------------------------------------------------
    def refresh_access_token(self, account_id: int) -> bool:
        """
        使用 refresh_token 刷新 TikTok access_token，
        并更新 social_accounts 表对应记录。
        """
        account = SocialAccounts.get_account_by_id(account_id)
        if not account or not account.refresh_token:
            return False

        platform = (account.platform or "").lower()
        if platform != "tiktok":
            log.warning("refresh_access_token called for unsupported platform=%s", platform)
            return False

        config = self.platform_configs.get("tiktok")
        if not config:
            return False

        data = {
            "client_key": config["client_key"],
            "client_secret": config["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": account.refresh_token,
        }
        try:
            resp = requests.post(
                config["token_url"],
                data=data,
                timeout=15,
            )
            resp.raise_for_status()
            token_data = resp.json()

            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token") or account.refresh_token
            expires_in = token_data.get("expires_in")
            scope = token_data.get("scope") or account.scope
            token_type = token_data.get("token_type") or account.token_type

            if not access_token:
                log.warning("TikTok refresh_token response missing access_token: %s", token_data)
                return False

            return SocialAccounts.update_token(
                account_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                scope=scope,
                token_type=token_type,
            )
        except Exception as exc:  # pylint: disable=broad-except
            log.error("Error refreshing token for account %s: %s", account_id, exc, exc_info=True)
            return False

    # ------------------------------------------------------------------
    # 内部工具：TikTok 交换 token 与拉取用户信息
    # ------------------------------------------------------------------
    def _exchange_tiktok_token(self, code: str, state_data: Dict[str, Any]) -> Dict[str, Any]:
        config = self.platform_configs["tiktok"]
        data = {
            "client_key": config["client_key"],
            "client_secret": config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": state_data.get("redirect_uri"),
            "code_verifier": state_data.get("code_verifier"),
        }
        resp = requests.post(
            config["token_url"],
            data=data,
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()
        if "access_token" not in token_data:
            log.warning("TikTok token response missing access_token: %s", token_data)
        return token_data

    def _get_tiktok_user_info(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 TikTok 用户信息接口获取用户名、头像等元数据。
        """
        access_token = token_data.get("access_token")
        open_id = token_data.get("open_id") or token_data.get("openId")
        if not access_token or not open_id:
            return {"username": "unknown", "display_name": "Unknown User"}

        config = self.platform_configs["tiktok"]
        url = f"{config['api_base'].rstrip('/')}/v2/user/info/"
        params = {
            "open_id": open_id,
            "fields": "display_name,username,avatar_url,follower_count,following_count,likes_count,video_count",
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            user = (data.get("data") or {}).get("user") or {}
        except Exception as exc:  # pylint: disable=broad-except
            log.warning("Failed to get TikTok user info: %s", exc, exc_info=True)
            return {"username": "unknown", "display_name": "Unknown User"}

        return {
            "username": user.get("username") or "",
            "display_name": user.get("display_name") or "",
            "avatar_url": user.get("avatar_url") or "",
            "follower_count": user.get("follower_count") or 0,
            "following_count": user.get("following_count") or 0,
            "posts_count": user.get("video_count") or 0,
            "open_id": open_id,
        }

    def _create_or_update_tiktok_account(
        self,
        *,
        state_data: Dict[str, Any],
        token_data: Dict[str, Any],
        user_info: Dict[str, Any],
    ):
        company_id = state_data.get("company_id")
        owner_user_id = state_data.get("user_id")

        username = user_info.get("username") or ""
        display_name = user_info.get("display_name") or username or "tiktok_account"
        open_id = user_info.get("open_id") or token_data.get("open_id")

        if username:
            account_url = f"https://www.tiktok.com/@{username}"
        else:
            account_url = ""

        account = SocialAccounts.upsert_tiktok_account(
            company_id=company_id,
            owner_user_id=owner_user_id,
            account_name=display_name,
            account_id=open_id or username or "",
            account_url=account_url,
            token_data=token_data,
            user_info=user_info,
        )
        return account

    # ------------------------------------------------------------------
    # 工具函数：state / PKCE
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_state() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def _generate_pkce_pair() -> tuple[str, str]:
        """
        生成 (code_verifier, code_challenge)。
        """
        code_verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode("ascii")
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return code_verifier, code_challenge


# 全局 OAuth 处理器实例
hsai_oauth_handler = HSAIOAuthHandler()
