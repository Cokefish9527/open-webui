"""
消息结构化处理器
将n8n返回结果转换为标准格式，支持多种数据格式转换
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import html
import markdown
from urllib.parse import urlparse

log = logging.getLogger(__name__)

class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    RICH_TEXT = "rich_text"
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"
    LINK = "link"
    STRUCTURED_DATA = "structured_data"
    ERROR = "error"
    STATUS = "status"

class ProcessingStatus(str, Enum):
    """处理状态枚举"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    INVALID_FORMAT = "invalid_format"

@dataclass
class ProcessedMessage:
    """处理后的消息"""
    message_type: MessageType
    content: str
    structured_data: Optional[Dict[str, Any]] = None
    media_urls: List[str] = None
    metadata: Dict[str, Any] = None
    processing_status: ProcessingStatus = ProcessingStatus.SUCCESS
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.media_urls is None:
            self.media_urls = []
        if self.metadata is None:
            self.metadata = {}

class MessageProcessor:
    """消息处理器"""
    
    def __init__(self):
        # URL正则表达式
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # 视频文件扩展名
        self.video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'}
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
        self.audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}
        
        # 支持的n8n响应格式
        self.n8n_response_schemas = {
            'main_workflow': {
                'success': bool,
                'messageType': str,
                'session_id': str,
                'business_name': str,
                'displayText': str,
                'data': dict,
                'file_preview': int,
                'create_ts': str
            },
            'company_info': {
                'success': bool,
                'company_data': dict,
                'analysis_result': dict,
                'recommendations': list
            },
            'viral_learning': {
                'success': bool,
                'trending_content': list,
                'insights': dict,
                'recommendations': list
            }
        }
        
    async def process_n8n_response(self, raw_response: Dict[str, Any], 
                                 workflow_type: str = None) -> ProcessedMessage:
        """处理n8n工作流响应"""
        try:
            log.info(f"Processing n8n response for workflow type: {workflow_type}")
            
            # 验证响应格式
            if not isinstance(raw_response, dict):
                return self._create_error_message("Invalid response format: not a dictionary")
                
            # 检查是否成功
            success = raw_response.get('success', False)
            if not success:
                error_msg = raw_response.get('error', 'Unknown error from n8n workflow')
                return self._create_error_message(error_msg)
                
            # 根据工作流类型处理响应
            if workflow_type == 'main':
                return await self._process_main_workflow_response(raw_response)
            elif workflow_type == 'company_info':
                return await self._process_company_info_response(raw_response)
            elif workflow_type == 'viral_learning':
                return await self._process_viral_learning_response(raw_response)
            elif workflow_type == 'video_analysis':
                return await self._process_video_analysis_response(raw_response)
            else:
                return await self._process_generic_response(raw_response)
                
        except Exception as e:
            log.error(f"Error processing n8n response: {e}")
            return self._create_error_message(f"Processing error: {str(e)}")
            
    async def _process_main_workflow_response(self, response: Dict[str, Any]) -> ProcessedMessage:
        """处理主工作流响应"""
        display_text = response.get('displayText', '')
        data = response.get('data', {})
        file_preview = response.get('file_preview', 0)
        
        # 提取媒体URL
        media_urls = []
        url_list = data.get('url_list')
        if url_list:
            if isinstance(url_list, str):
                # 单个URL
                if self._is_valid_url(url_list):
                    media_urls.append(url_list)
            elif isinstance(url_list, list):
                # URL列表
                for url in url_list:
                    if isinstance(url, str) and self._is_valid_url(url):
                        media_urls.append(url)
                        
        # 确定消息类型
        message_type = MessageType.TEXT
        if media_urls:
            # 根据URL判断媒体类型
            for url in media_urls:
                if self._is_video_url(url):
                    message_type = MessageType.VIDEO
                    break
                elif self._is_image_url(url):
                    message_type = MessageType.IMAGE
                    break
                    
        # 处理显示文本
        processed_text = self._process_display_text(display_text)
        
        return ProcessedMessage(
            message_type=message_type,
            content=processed_text,
            media_urls=media_urls,
            structured_data={
                'session_id': response.get('session_id'),
                'business_name': response.get('business_name'),
                'message_type': response.get('messageType'),
                'has_preview': bool(file_preview),
                'original_data': data
            },
            metadata={
                'workflow_type': 'main',
                'create_timestamp': response.get('create_ts'),
                'media_count': len(media_urls)
            }
        )
        
    async def _process_company_info_response(self, response: Dict[str, Any]) -> ProcessedMessage:
        """处理公司信息工作流响应"""
        company_data = response.get('company_data', {})
        analysis_result = response.get('analysis_result', {})
        recommendations = response.get('recommendations', [])
        
        # 构建结构化内容
        content_parts = []
        
        if company_data:
            content_parts.append("## 公司信息")
            for key, value in company_data.items():
                if value:
                    content_parts.append(f"**{key}**: {value}")
                    
        if analysis_result:
            content_parts.append("\n## 分析结果")
            for key, value in analysis_result.items():
                if value:
                    content_parts.append(f"**{key}**: {value}")
                    
        if recommendations:
            content_parts.append("\n## 建议")
            for i, rec in enumerate(recommendations, 1):
                content_parts.append(f"{i}. {rec}")
                
        content = "\n".join(content_parts) if content_parts else "未获取到公司信息"
        
        return ProcessedMessage(
            message_type=MessageType.STRUCTURED_DATA,
            content=content,
            structured_data={
                'company_data': company_data,
                'analysis_result': analysis_result,
                'recommendations': recommendations
            },
            metadata={
                'workflow_type': 'company_info',
                'data_completeness': self._calculate_data_completeness(response)
            }
        )
        
    async def _process_viral_learning_response(self, response: Dict[str, Any]) -> ProcessedMessage:
        """处理爆款学习工作流响应"""
        trending_content = response.get('trending_content', [])
        insights = response.get('insights', {})
        recommendations = response.get('recommendations', [])
        
        content_parts = []
        
        if trending_content:
            content_parts.append("## 热门内容分析")
            for i, content in enumerate(trending_content[:5], 1):  # 只显示前5个
                title = content.get('title', f'内容 {i}')
                description = content.get('description', '')
                content_parts.append(f"**{i}. {title}**")
                if description:
                    content_parts.append(f"   {description}")
                    
        if insights:
            content_parts.append("\n## 关键洞察")
            for key, value in insights.items():
                if value:
                    content_parts.append(f"**{key}**: {value}")
                    
        if recommendations:
            content_parts.append("\n## 创作建议")
            for i, rec in enumerate(recommendations, 1):
                content_parts.append(f"{i}. {rec}")
                
        content = "\n".join(content_parts) if content_parts else "未发现相关热门内容"
        
        return ProcessedMessage(
            message_type=MessageType.STRUCTURED_DATA,
            content=content,
            structured_data={
                'trending_content': trending_content,
                'insights': insights,
                'recommendations': recommendations
            },
            metadata={
                'workflow_type': 'viral_learning',
                'content_count': len(trending_content),
                'insight_count': len(insights)
            }
        )
        
    async def _process_video_analysis_response(self, response: Dict[str, Any]) -> ProcessedMessage:
        """处理视频分析工作流响应"""
        analysis_data = response.get('analysis_data', {})
        keywords = response.get('keywords', [])
        metrics = response.get('metrics', {})
        
        content_parts = []
        
        if keywords:
            content_parts.append("## 关键词分析")
            for keyword in keywords[:10]:  # 显示前10个关键词
                if isinstance(keyword, dict):
                    word = keyword.get('word', '')
                    weight = keyword.get('weight', 0)
                    content_parts.append(f"- {word} (权重: {weight})")
                else:
                    content_parts.append(f"- {keyword}")
                    
        if metrics:
            content_parts.append("\n## 数据指标")
            for key, value in metrics.items():
                content_parts.append(f"**{key}**: {value}")
                
        if analysis_data:
            content_parts.append("\n## 详细分析")
            for key, value in analysis_data.items():
                if isinstance(value, (str, int, float)):
                    content_parts.append(f"**{key}**: {value}")
                    
        content = "\n".join(content_parts) if content_parts else "视频分析完成，未获取到详细数据"
        
        return ProcessedMessage(
            message_type=MessageType.STRUCTURED_DATA,
            content=content,
            structured_data={
                'analysis_data': analysis_data,
                'keywords': keywords,
                'metrics': metrics
            },
            metadata={
                'workflow_type': 'video_analysis',
                'keyword_count': len(keywords),
                'metrics_count': len(metrics)
            }
        )
        
    async def _process_generic_response(self, response: Dict[str, Any]) -> ProcessedMessage:
        """处理通用响应格式"""
        # 尝试提取常见字段
        content = ""
        structured_data = {}
        media_urls = []
        
        # 查找可能的内容字段
        content_fields = ['content', 'message', 'text', 'result', 'output', 'displayText']
        for field in content_fields:
            if field in response and response[field]:
                content = str(response[field])
                break
                
        # 查找媒体URL
        url_fields = ['url', 'urls', 'media_url', 'file_url', 'video_url', 'image_url']
        for field in url_fields:
            if field in response:
                urls = response[field]
                if isinstance(urls, str) and self._is_valid_url(urls):
                    media_urls.append(urls)
                elif isinstance(urls, list):
                    for url in urls:
                        if isinstance(url, str) and self._is_valid_url(url):
                            media_urls.append(url)
                            
        # 提取结构化数据
        for key, value in response.items():
            if key not in ['content', 'message', 'text'] and value is not None:
                structured_data[key] = value
                
        # 确定消息类型
        message_type = MessageType.TEXT
        if media_urls:
            if any(self._is_video_url(url) for url in media_urls):
                message_type = MessageType.VIDEO
            elif any(self._is_image_url(url) for url in media_urls):
                message_type = MessageType.IMAGE
                
        return ProcessedMessage(
            message_type=message_type,
            content=content or "处理完成",
            media_urls=media_urls,
            structured_data=structured_data,
            metadata={
                'workflow_type': 'generic',
                'response_keys': list(response.keys())
            }
        )
        
    def _process_display_text(self, text: str) -> str:
        """处理显示文本"""
        if not text:
            return ""
            
        # HTML解码
        text = html.unescape(text)
        
        # 处理换行符
        text = text.replace('\\n', '\n').replace('\\\\n', '\n')
        
        # 处理引号
        text = text.replace('\\"', '"').replace("\\'", "'")
        
        # 清理多余的空白字符
        text = re.sub(r'\n\s*\n', '\n\n', text)  # 多个空行合并为两个
        text = text.strip()
        
        return text
        
    def _is_valid_url(self, url: str) -> bool:
        """验证URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
            
    def _is_video_url(self, url: str) -> bool:
        """判断是否为视频URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            return any(path.endswith(ext) for ext in self.video_extensions)
        except:
            return False
            
    def _is_image_url(self, url: str) -> bool:
        """判断是否为图片URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            return any(path.endswith(ext) for ext in self.image_extensions)
        except:
            return False
            
    def _calculate_data_completeness(self, response: Dict[str, Any]) -> float:
        """计算数据完整性"""
        total_fields = len(response)
        non_empty_fields = sum(1 for value in response.values() if value)
        return non_empty_fields / total_fields if total_fields > 0 else 0.0
        
    def _create_error_message(self, error_text: str) -> ProcessedMessage:
        """创建错误消息"""
        return ProcessedMessage(
            message_type=MessageType.ERROR,
            content=f"处理失败: {error_text}",
            processing_status=ProcessingStatus.FAILED,
            error_message=error_text,
            metadata={'error_type': 'processing_error'}
        )
        
    async def format_for_websocket(self, processed_message: ProcessedMessage, 
                                 session_id: str, user_id: str) -> Dict[str, Any]:
        """格式化为WebSocket消息"""
        return {
            "type": "workflow_response",
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": processed_message.timestamp.isoformat(),
            "data": {
                "message_type": processed_message.message_type.value,
                "content": processed_message.content,
                "media_urls": processed_message.media_urls,
                "structured_data": processed_message.structured_data,
                "metadata": processed_message.metadata,
                "processing_status": processed_message.processing_status.value,
                "error_message": processed_message.error_message
            }
        }

# 全局消息处理器实例
message_processor = MessageProcessor()