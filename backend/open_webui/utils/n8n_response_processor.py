"""
n8n响应处理器

专门处理不同类型的n8n工作流响应，进行结构化转换
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from open_webui.config.n8n_workflows import N8NWorkflowType

log = logging.getLogger(__name__)

class N8NResponseProcessor:
    """n8n响应处理器"""
    
    @staticmethod
    def process_response(
        raw_response: Dict[str, Any], 
        workflow_type: N8NWorkflowType,
        execution_start_time: float
    ) -> Dict[str, Any]:
        """
        处理n8n工作流响应
        
        Args:
            raw_response: n8n原始响应
            workflow_type: 工作流类型
            execution_start_time: 执行开始时间
            
        Returns:
            结构化的响应数据
        """
        try:
            execution_time = datetime.now().timestamp() - execution_start_time
            
            # 基础响应结构
            processed = {
                "success": raw_response.get("success", True),
                "content": raw_response.get("content", ""),
                "type": raw_response.get("type", "text"),
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "workflow_type": workflow_type.value,
                    "execution_time": execution_time,
                    "execution_id": raw_response.get("execution_id"),
                    "model": raw_response.get("model"),
                    "tokens": raw_response.get("tokens"),
                    "processing_time": raw_response.get("processing_time")
                }
            }
            
            # 根据工作流类型进行特殊处理
            if workflow_type == N8NWorkflowType.MAIN:
                processed.update(N8NResponseProcessor._process_main_workflow(raw_response))
            elif workflow_type == N8NWorkflowType.VIRAL_LEARNING:
                processed.update(N8NResponseProcessor._process_viral_learning(raw_response))
            elif workflow_type == N8NWorkflowType.COMPANY_INFO:
                processed.update(N8NResponseProcessor._process_company_info(raw_response))
            elif workflow_type == N8NWorkflowType.VIDEO_ANALYSIS:
                processed.update(N8NResponseProcessor._process_video_analysis(raw_response))
            
            # 通用字段处理
            processed["attachments"] = raw_response.get("attachments", [])
            processed["actions"] = raw_response.get("suggested_actions", [])
            processed["error_message"] = raw_response.get("error_message")
            
            return processed
            
        except Exception as e:
            log.error(f"Error processing n8n response: {e}")
            return {
                "success": False,
                "content": "响应处理失败",
                "type": "error",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    def _process_main_workflow(response: Dict[str, Any]) -> Dict[str, Any]:
        """处理主工作流响应"""
        return {
            "workflow_name": "主工作流",
            "task_result": response.get("task_result", {}),
            "next_actions": response.get("next_actions", []),
            "context": response.get("context", {})
        }
    
    @staticmethod
    def _process_viral_learning(response: Dict[str, Any]) -> Dict[str, Any]:
        """处理被动触发爆款学习工作流响应"""
        return {
            "workflow_name": "被动触发爆款学习",
            "learning_insights": response.get("learning_insights", {}),
            "viral_patterns": response.get("viral_patterns", []),
            "recommendations": response.get("recommendations", []),
            "analysis_data": {
                "engagement_metrics": response.get("engagement_metrics", {}),
                "content_features": response.get("content_features", {}),
                "trend_analysis": response.get("trend_analysis", {})
            }
        }
    
    @staticmethod
    def _process_company_info(response: Dict[str, Any]) -> Dict[str, Any]:
        """处理公司信息收集及作战地图梳理工作流响应"""
        return {
            "workflow_name": "公司信息收集及作战地图梳理",
            "company_profile": response.get("company_profile", {}),
            "battle_map": response.get("battle_map", {}),
            "competitive_analysis": response.get("competitive_analysis", {}),
            "strategic_insights": response.get("strategic_insights", []),
            "data_sources": response.get("data_sources", []),
            "collection_summary": {
                "total_sources": response.get("total_sources", 0),
                "data_quality": response.get("data_quality", "unknown"),
                "completeness": response.get("completeness", 0)
            }
        }
    
    @staticmethod
    def _process_video_analysis(response: Dict[str, Any]) -> Dict[str, Any]:
        """处理异步视频爬取关键词分析工作流响应"""
        return {
            "workflow_name": "异步视频爬取关键词分析",
            "video_metadata": response.get("video_metadata", {}),
            "keyword_analysis": response.get("keyword_analysis", {}),
            "content_summary": response.get("content_summary", ""),
            "extracted_keywords": response.get("extracted_keywords", []),
            "sentiment_analysis": response.get("sentiment_analysis", {}),
            "processing_status": {
                "crawl_status": response.get("crawl_status", "unknown"),
                "analysis_status": response.get("analysis_status", "unknown"),
                "total_videos": response.get("total_videos", 0),
                "processed_videos": response.get("processed_videos", 0)
            }
        }
    
    @staticmethod
    def format_for_client(processed_response: Dict[str, Any]) -> Dict[str, Any]:
        """格式化响应以适配客户端显示"""
        return {
            "type": "workflow_response",
            "success": processed_response.get("success", True),
            "message": processed_response.get("content", ""),
            "data": {
                "workflow": {
                    "name": processed_response.get("workflow_name", ""),
                    "type": processed_response.get("metadata", {}).get("workflow_type", ""),
                    "execution_time": processed_response.get("metadata", {}).get("execution_time", 0)
                },
                "result": {
                    key: value for key, value in processed_response.items()
                    if key not in ["success", "content", "type", "timestamp", "metadata", "error_message"]
                },
                "attachments": processed_response.get("attachments", []),
                "actions": processed_response.get("actions", [])
            },
            "timestamp": processed_response.get("timestamp"),
            "error": processed_response.get("error_message")
        }