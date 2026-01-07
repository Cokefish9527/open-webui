"""
External Admin Authentication
用于验证hsai_admin后台调用的API认证
"""
import logging
import os
from typing import Dict, Any, List
from fastapi import Request, HTTPException, status

from open_webui.models.external_admin_tokens import ExternalAdminTokens

log = logging.getLogger(__name__)

# 从环境变量获取配置
EXTERNAL_ADMIN_API_KEY = os.getenv("EXTERNAL_ADMIN_API_KEY") or os.getenv("MAIN_SYSTEM_API_KEY")
EXTERNAL_ADMIN_CLIENT_ID = os.environ.get("EXTERNAL_ADMIN_CLIENT_ID", "external-admin")

_auth_bypass_raw = os.environ.get("EXTERNAL_ADMIN_AUTH_BYPASS", "false").strip().lower()
EXTERNAL_ADMIN_AUTH_BYPASS = _auth_bypass_raw in {"1", "true", "yes", "on"}

EXTERNAL_ADMIN_IP_WHITELIST = [
    ip.strip() for ip in os.environ.get("EXTERNAL_ADMIN_IP_WHITELIST", "").split(",") if ip.strip()
]

_AUTH_BYPASS_WARNING_EMITTED = False


async def verify_external_request(request: Request) -> Dict[str, Any]:
    """
    验证外部管理请求
    
    检查请求是否携带有效的API Key或OAuth Token，并验证IP白名单。
    支持 EXTERNAL_ADMIN_AUTH_BYPASS 绕过鉴权。
    
    Args:
        request: FastAPI Request对象
    
    Returns:
        Dict包含验证信息
    
    Raises:
        HTTPException: 401/403 - 认证失败
    """
    global _AUTH_BYPASS_WARNING_EMITTED

    # 1. 检查 Bypass 开关
    if EXTERNAL_ADMIN_AUTH_BYPASS:
        if not _AUTH_BYPASS_WARNING_EMITTED:
            log.warning(
                "EXTERNAL_ADMIN_AUTH_BYPASS enabled; skipping external admin IP/token checks in utils. "
                "禁用该开关即可恢复鉴权。"
            )
            _AUTH_BYPASS_WARNING_EMITTED = True
        return {
            "authenticated": True,
            "source": "bypass",
            "client_id": EXTERNAL_ADMIN_CLIENT_ID
        }

    # 2. 检查 IP 白名单
    if EXTERNAL_ADMIN_IP_WHITELIST:
        if not request.client:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无法获取客户端IP",
            )
        client_ip = request.client.host
        if client_ip not in EXTERNAL_ADMIN_IP_WHITELIST:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP地址不在白名单中",
            )

    # 3. 检查 Authorization Header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        # 兼容旧逻辑：如果只配置了 API Key 且请求头缺失，尝试检查是否允许仅通过 IP（目前 strict 模式不允许）
        # 但这里若是没 Key，就无法认证
        if not EXTERNAL_ADMIN_API_KEY:
             log.warning("EXTERNAL_ADMIN_API_KEY not configured, external admin API is disabled")
             raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="External admin API is not configured"
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    raw_token = auth_header.split(" ", 1)[1].strip()
    
    # 4. Check against environment variable API Key first (Simple mode)
    if EXTERNAL_ADMIN_API_KEY and raw_token == EXTERNAL_ADMIN_API_KEY:
         return {
            "authenticated": True,
            "source": "env_api_key",
            "client_id": "env-key-client"
        }

    # 5. Check against OAuth Tokens (Database)
    token_record = ExternalAdminTokens.get_valid_token(raw_token)
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key or token"
        )
    
    return {
        "authenticated": True,
        "source": "oauth_token",
        "client_id": token_record.client_id
    }
