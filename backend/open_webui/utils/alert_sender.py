import logging
from typing import Dict, Any, Optional

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

# 告警服务可用性标志
ALERT_SERVICE_AVAILABLE = False

try:
    from open_webui.services.alert_service import send_alert_to_admin
    ALERT_SERVICE_AVAILABLE = True
except ImportError:
    ALERT_SERVICE_AVAILABLE = False

async def send_system_alert(
    title: str,
    content: str,
    level: str = "ERROR",
    source: str = "open-webui",
    category: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    发送系统告警的便捷函数
    
    Args:
        title: 告警标题
        content: 告警内容
        level: 告警级别 (INFO, WARNING, ERROR, CRITICAL)
        source: 告警来源
        category: 告警分类
        metadata: 附加元数据
        
    Returns:
        bool: 发送是否成功
    """
    if not ALERT_SERVICE_AVAILABLE:
        log.warning("告警服务不可用，无法发送告警")
        return False
        
    try:
        result = await send_alert_to_admin(
            title=title,
            content=content,
            level=level,
            source=source,
            category=category,
            metadata=metadata
        )
        return result
    except Exception as e:
        log.error(f"发送系统告警失败: {e}")
        return False

async def send_error_alert(
    error_message: str,
    error_details: Optional[str] = None,
    source: str = "open-webui",
    category: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    发送错误告警
    
    Args:
        error_message: 错误信息
        error_details: 错误详情
        source: 错误来源
        category: 错误分类
        metadata: 附加元数据
        
    Returns:
        bool: 发送是否成功
    """
    title = f"系统错误: {error_message}"
    content = error_details or error_message
    
    return await send_system_alert(
        title=title,
        content=content,
        level="ERROR",
        source=source,
        category=category,
        metadata=metadata
    )

async def send_warning_alert(
    warning_message: str,
    warning_details: Optional[str] = None,
    source: str = "open-webui",
    category: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    发送警告告警
    
    Args:
        warning_message: 警告信息
        warning_details: 警告详情
        source: 警告来源
        category: 警告分类
        metadata: 附加元数据
        
    Returns:
        bool: 发送是否成功
    """
    title = f"系统警告: {warning_message}"
    content = warning_details or warning_message
    
    return await send_system_alert(
        title=title,
        content=content,
        level="WARNING",
        source=source,
        category=category,
        metadata=metadata
    )

# 使用示例:
# await send_error_alert("数据库连接失败", "无法连接到PostgreSQL数据库", category="database")
# await send_warning_alert("Redis连接超时", "Redis连接超时，正在重试", category="redis")