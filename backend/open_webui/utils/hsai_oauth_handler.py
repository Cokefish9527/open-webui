import logging
import time
import secrets
import hashlib
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse

import requests
from open_webui.models.hsai_matrix import HSAIPlatformAccounts, HSAIPlatformAccountForm, HSAIAccountStatus

log = logging.getLogger(__name__)


class HSAIOAuthHandler:
    """HSAI OAuth处理器，负责各大平台的OAuth认证流程"""
    
    def __init__(self):
        # 各平台OAuth配置
        self.platform_configs = {
            "tiktok": {
                "client_id": "YOUR_TIKTOK_CLIENT_ID",
                "client_secret": "YOUR_TIKTOK_CLIENT_SECRET",
                "scope": "user.info.basic,video.upload",
                "authorize_url": "https://open.tiktokapis.com/platform/oauth/connect/",
                "token_url": "https://open.tiktokapis.com/platform/oauth/token/",
                "api_base": "https://open.tiktokapis.com"
            },
            "instagram": {
                "client_id": "YOUR_INSTAGRAM_CLIENT_ID", 
                "client_secret": "YOUR_INSTAGRAM_CLIENT_SECRET",
                "scope": "user_profile,user_media",
                "authorize_url": "https://api.instagram.com/oauth/authorize",
                "token_url": "https://api.instagram.com/oauth/access_token",
                "api_base": "https://graph.instagram.com"
            },
            "youtube": {
                "client_id": "YOUR_YOUTUBE_CLIENT_ID",
                "client_secret": "YOUR_YOUTUBE_CLIENT_SECRET", 
                "scope": "https://www.googleapis.com/auth/youtube.upload",
                "authorize_url": "https://accounts.google.com/oauth2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "api_base": "https://www.googleapis.com/youtube/v3"
            },
            "weibo": {
                "client_id": "YOUR_WEIBO_CLIENT_ID",
                "client_secret": "YOUR_WEIBO_CLIENT_SECRET",
                "scope": "friendships_groups_read,statuses_to_me_read,write",
                "authorize_url": "https://api.weibo.com/oauth2/authorize",
                "token_url": "https://api.weibo.com/oauth2/access_token",
                "api_base": "https://api.weibo.com/2"
            }
        }
        
        # 存储state参数的临时字典（实际应用中应使用Redis）
        self.state_storage = {}
    
    def generate_oauth_url(
        self, 
        platform_type: str, 
        redirect_uri: str,
        user_id: str
    ) -> Dict[str, str]:
        """生成OAuth授权URL"""
        try:
            config = self.platform_configs.get(platform_type)
            if not config:
                raise ValueError(f"Unsupported platform: {platform_type}")
            
            # 生成state参数用于防CSRF
            state = secrets.token_urlsafe(32)
            
            # 存储state和用户信息
            self.state_storage[state] = {
                "user_id": user_id,
                "platform_type": platform_type,
                "redirect_uri": redirect_uri,
                "created_at": time.time()
            }
            
            # 构建授权URL参数
            auth_params = {
                "client_id": config["client_id"],
                "redirect_uri": redirect_uri,
                "scope": config["scope"],
                "response_type": "code",
                "state": state
            }
            
            # 特殊处理TikTok
            if platform_type == "tiktok":
                auth_params["client_key"] = config["client_id"]
                del auth_params["client_id"]
            
            authorization_url = f"{config['authorize_url']}?{urlencode(auth_params)}"
            
            return {
                "authorization_url": authorization_url,
                "state": state
            }
            
        except Exception as e:
            log.error(f"Error generating OAuth URL for {platform_type}: {e}")
            raise
    
    def handle_oauth_callback(
        self, 
        platform_type: str, 
        code: str, 
        state: str
    ) -> Dict[str, Any]:
        """处理OAuth回调，交换access token"""
        try:
            # 验证state参数
            state_data = self.state_storage.get(state)
            if not state_data:
                raise ValueError("Invalid or expired state parameter")
            
            # 检查state是否过期（10分钟）
            if time.time() - state_data["created_at"] > 600:
                del self.state_storage[state]
                raise ValueError("State parameter expired")
            
            config = self.platform_configs.get(platform_type)
            if not config:
                raise ValueError(f"Unsupported platform: {platform_type}")
            
            # 交换access token
            token_data = self._exchange_access_token(
                config, code, state_data["redirect_uri"]
            )
            
            # 获取用户信息
            user_info = self._get_user_info(config, token_data, platform_type)
            
            # 创建或更新账号记录
            account = self._create_or_update_account(
                state_data["user_id"],
                platform_type,
                token_data,
                user_info
            )
            
            # 清理state
            del self.state_storage[state]
            
            return {
                "success": True,
                "account_id": account.id,
                "user_info": user_info
            }
            
        except Exception as e:
            log.error(f"Error handling OAuth callback for {platform_type}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _exchange_access_token(
        self, 
        config: Dict[str, str], 
        code: str, 
        redirect_uri: str
    ) -> Dict[str, Any]:
        """交换access token"""
        token_params = {
            "grant_type": "authorization_code",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        response = requests.post(config["token_url"], data=token_params)
        response.raise_for_status()
        
        return response.json()
    
    def _get_user_info(
        self, 
        config: Dict[str, str], 
        token_data: Dict[str, Any], 
        platform_type: str
    ) -> Dict[str, Any]:
        """获取用户信息"""
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("No access token in response")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 根据平台构建用户信息API URL
        user_info_urls = {
            "tiktok": f"{config['api_base']}/v2/user/info/",
            "instagram": f"{config['api_base']}/me?fields=id,username,media_count",
            "youtube": f"{config['api_base']}/channels?part=snippet,statistics&mine=true",
            "weibo": f"{config['api_base']}/users/show.json"
        }
        
        url = user_info_urls.get(platform_type)
        if not url:
            return {"username": "unknown", "display_name": "Unknown User"}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            
            # 根据平台解析用户信息
            if platform_type == "tiktok":
                return {
                    "username": user_data.get("data", {}).get("display_name", ""),
                    "display_name": user_data.get("data", {}).get("display_name", ""),
                    "avatar_url": user_data.get("data", {}).get("avatar_url", ""),
                    "follower_count": 0,
                    "following_count": 0,
                    "posts_count": 0
                }
            elif platform_type == "instagram":
                return {
                    "username": user_data.get("username", ""),
                    "display_name": user_data.get("username", ""),
                    "avatar_url": "",
                    "follower_count": 0,
                    "following_count": 0,
                    "posts_count": user_data.get("media_count", 0)
                }
            elif platform_type == "youtube":
                if user_data.get("items"):
                    item = user_data["items"][0]
                    return {
                        "username": item.get("snippet", {}).get("title", ""),
                        "display_name": item.get("snippet", {}).get("title", ""),
                        "avatar_url": item.get("snippet", {}).get("thumbnails", {}).get("default", {}).get("url", ""),
                        "follower_count": item.get("statistics", {}).get("subscriberCount", 0),
                        "following_count": 0,
                        "posts_count": item.get("statistics", {}).get("videoCount", 0)
                    }
            elif platform_type == "weibo":
                return {
                    "username": user_data.get("screen_name", ""),
                    "display_name": user_data.get("name", ""),
                    "avatar_url": user_data.get("profile_image_url", ""),
                    "follower_count": user_data.get("followers_count", 0),
                    "following_count": user_data.get("friends_count", 0),
                    "posts_count": user_data.get("statuses_count", 0)
                }
            
            return {"username": "unknown", "display_name": "Unknown User"}
            
        except Exception as e:
            log.warning(f"Failed to get user info for {platform_type}: {e}")
            return {"username": "unknown", "display_name": "Unknown User"}
    
    def _create_or_update_account(
        self, 
        user_id: str, 
        platform_type: str, 
        token_data: Dict[str, Any], 
        user_info: Dict[str, Any]
    ) -> Any:
        """创建或更新账号记录"""
        
        # 检查是否已存在该平台账号
        existing_accounts = HSAIPlatformAccounts.get_accounts_by_user_id(
            user_id, platform_type=platform_type
        )
        
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")
        
        # 计算token过期时间
        token_expires_at = None
        if expires_in:
            token_expires_at = int(time.time()) + int(expires_in)
        
        account_data = HSAIPlatformAccountForm(
            name=f"{platform_type}_{user_info.get('username', 'account')}",
            platform_type=platform_type,
            username=user_info.get("username", ""),
            display_name=user_info.get("display_name", ""),
            avatar_url=user_info.get("avatar_url", ""),
            status=HSAIAccountStatus.ACTIVE,
            follower_count=int(user_info.get("follower_count", 0)),
            following_count=int(user_info.get("following_count", 0)),
            posts_count=int(user_info.get("posts_count", 0)),
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            last_sync_at=int(time.time())
        )
        
        if existing_accounts:
            # 更新现有账号
            account = existing_accounts[0]
            HSAIPlatformAccounts.update_account_by_id(account.id, account_data.model_dump())
            return HSAIPlatformAccounts.get_account_by_id(account.id)
        else:
            # 创建新账号
            return HSAIPlatformAccounts.insert_new_account(user_id, account_data)
    
    def refresh_access_token(self, account_id: str) -> bool:
        """刷新access token"""
        try:
            account = HSAIPlatformAccounts.get_account_by_id(account_id)
            if not account or not account.refresh_token:
                return False
            
            config = self.platform_configs.get(account.platform_type)
            if not config:
                return False
            
            # 使用refresh token获取新的access token
            refresh_params = {
                "grant_type": "refresh_token",
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "refresh_token": account.refresh_token
            }
            
            response = requests.post(config["token_url"], data=refresh_params)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token", account.refresh_token)
            expires_in = token_data.get("expires_in")
            
            # 计算新的过期时间
            token_expires_at = None
            if expires_in:
                token_expires_at = int(time.time()) + int(expires_in)
            
            # 更新账号token信息
            return HSAIPlatformAccounts.update_account_token(
                account_id, access_token, refresh_token, token_expires_at
            )
            
        except Exception as e:
            log.error(f"Error refreshing token for account {account_id}: {e}")
            return False


# 全局OAuth处理器实例
hsai_oauth_handler = HSAIOAuthHandler()