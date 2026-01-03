"""
External Admin Authentication
用于验证hsai_admin后台调用的API认证
"""
import logging
import os
from typing import Dict, Any
from fastapi import Header, HTTPException, status

log = logging.getLogger(__name__)

# 从环境变量获取API Key
EXTERNAL_ADMIN_API_KEY = os.getenv("EXTERNAL_ADMIN_API_KEY") or os.getenv("MAIN_SYSTEM_API_KEY")


async def verify_external_request(
    authorization: str = Header(None, description="Bearer token")
) -> Dict[str, Any]:
    """
    验证外部管理请求
    
    检查请求是否携带有效的API Key。
    用于hsai_admin等管理后台访问素材等资源。
    
    Args:
        authorization: Authorization header (Bearer token)
    
    Returns:
        Dict包含验证信息
    
    Raises:
        HTTPException: 401 - 认证失败
    """
    if not EXTERNAL_ADMIN_API_KEY:
        log.warning("EXTERNAL_ADMIN_API_KEY not configured, external admin API is disabled")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External admin API is not configured"
        )
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    # 解析Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = parts[1]
    
    # 验证token
    if token != EXTERNAL_ADMIN_API_KEY:
        log.warning(f"Invalid external admin API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # 验证通过，返回认证信息
    return {
        "authenticated": True,
        "source": "external_admin"
    }
