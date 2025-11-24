import asyncio
import logging
import aiohttp
from typing import Dict, Any, Optional
from open_webui.env import ADMIN_DATABASE_URL, SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

class AlertService:
    """告警服务，用于向后台发送告警信息"""
    
    def __init__(self, admin_base_url: str, api_key: Optional[str] = None):
        self.admin_base_url = admin_base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
        
    async def init_session(self):
        """初始化HTTP会话"""
        if self.session is None:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
                
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
    async def close(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def send_alert(
        self, 
        title: str, 
        content: str, 
        level: str = "ERROR",
        source: str = "open-webui",
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送告警信息到后台
        
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
        if not self.session:
            await self.init_session()
            
        alert_data = {
            "title": title,
            "content": content,
            "level": level,
            "source": source,
            "category": category,
            "metadata": metadata or {}
        }
        
        try:
            url = f"{self.admin_base_url}/api/alerts/"
            async with self.session.post(url, json=alert_data) as response:
                if response.status in [200, 201]:
                    log.info(f"告警发送成功: {title}")
                    return True
                else:
                    error_text = await response.text()
                    log.error(f"告警发送失败: {response.status} - {error_text}")
                    return False
        except Exception as e:
            log.error(f"发送告警时发生异常: {e}")
            return False
            
    async def send_error_alert(
        self,
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
        
        return await self.send_alert(
            title=title,
            content=content,
            level="ERROR",
            source=source,
            category=category,
            metadata=metadata
        )
        
    async def send_warning_alert(
        self,
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
        
        return await self.send_alert(
            title=title,
            content=content,
            level="WARNING",
            source=source,
            category=category,
            metadata=metadata
        )

# 全局告警服务实例
alert_service: Optional[AlertService] = None

async def init_alert_service(admin_base_url: str, api_key: Optional[str] = None) -> AlertService:
    """初始化全局告警服务"""
    global alert_service
    if alert_service is None:
        alert_service = AlertService(admin_base_url, api_key)
        await alert_service.init_session()
    return alert_service

async def get_alert_service() -> Optional[AlertService]:
    """获取全局告警服务"""
    global alert_service
    return alert_service

async def send_alert_to_admin(
    title: str, 
    content: str, 
    level: str = "ERROR",
    source: str = "open-webui",
    category: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    发送告警到后台的便捷函数
    
    Args:
        title: 告警标题
        content: 告警内容
        level: 告警级别
        source: 告警来源
        category: 告警分类
        metadata: 附加元数据
        
    Returns:
        bool: 发送是否成功
    """
    service = await get_alert_service()
    if service:
        return await service.send_alert(title, content, level, source, category, metadata)
    return False

# 使用示例:
# async def example():
#     async with AlertService("http://localhost:5000") as service:
#         await service.send_alert(
#             title="测试告警",
#             content="这是一条测试告警信息",
#             level="WARNING"
#         )