"""
n8n响应处理器

处理从n8n工作流返回的响应数据，进行结构化处理
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

log = logging.getLogger(__name__)

class ResponseStatus(str, Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    PROCESSING = "processing"

class ProcessedResponse(BaseModel):
    """处理后的响应模型"""
    status: ResponseStatus
    message: str
    data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    workflow_type: Optional[str] = None
    execution_id: Optional[str] = None

class N8NResponseProcessor:
    """n8n响应处理器"""
    
    def __init__(self):
        self.processors = {
            "main": self._process_main_workflow_response,
            "company_info": self._process_company_info_response,
            "viral_learning": self._process_viral_learning_response
        }
    
    async def process_response(
        self, 
        raw_response: Dict[str, Any], 
        workflow_type: str,
        execution_id: Optional[str] = None
    ) -> ProcessedResponse:
        """
        处理n8n工作流响应
        
        Args:
            raw_response: n8n返回的原始响应
            workflow_type: 工作流类型
            execution_id: 执行ID
            
        Returns:
            ProcessedResponse: 处理后的结构化响应
        """
        try:
            # 获取对应的处理器
            processor = self.processors.get(workflow_type, self._process_default_response)
            
            # 处理响应
            processed = await processor(raw_response)
            processed.workflow_type = workflow_type
            processed.execution_id = execution_id
            
            log.info(f"Processed {workflow_type} workflow response: {processed.status}")
            return processed
            
        except Exception as e:
            log.error(f"Error processing {workflow_type} response: {e}")
            return ProcessedResponse(
                status=ResponseStatus.ERROR,
                message=f"Response processing failed: {str(e)}",
                workflow_type=workflow_type,
                execution_id=execution_id,
                metadata={"error": str(e), "raw_response": raw_response}
            )
    
    async def _process_main_workflow_response(self, response: Dict[str, Any]) -> ProcessedResponse:
        """处理主工作流响应"""
        try:
            # 提取主要信息
            status = ResponseStatus.SUCCESS if response.get("success", True) else ResponseStatus.ERROR
            message = response.get("message", "Main workflow completed")
            
            # 提取数据
            data = {
                "result": response.get("result"),
                "output": response.get("output"),
                "steps_completed": response.get("steps_completed", 0)
            }
            
            # 提取元数据
            metadata = {
                "execution_time": response.get("execution_time"),
                "node_count": response.get("node_count"),
                "workflow_version": response.get("version")
            }
            
            return ProcessedResponse(
                status=status,
                message=message,
                data=data,
                metadata=metadata
            )
            
        except Exception as e:
            log.error(f"Error processing main workflow response: {e}")
            raise
    
    async def _process_company_info_response(self, response: Dict[str, Any]) -> ProcessedResponse:
        """处理公司信息收集工作流响应"""
        try:
            status = ResponseStatus.SUCCESS if response.get("success", True) else ResponseStatus.ERROR
            message = response.get("message", "Company information collection completed")
            
            # 提取公司信息数据
            data = {
                "company_info": response.get("company_info", {}),
                "battle_map": response.get("battle_map", {}),
                "competitors": response.get("competitors", []),
                "market_analysis": response.get("market_analysis", {})
            }
            
            metadata = {
                "sources_count": len(response.get("sources", [])),
                "confidence_score": response.get("confidence_score"),
                "collection_time": response.get("collection_time")
            }
            
            return ProcessedResponse(
                status=status,
                message=message,
                data=data,
                metadata=metadata
            )
            
        except Exception as e:
            log.error(f"Error processing company info response: {e}")
            raise
    
    async def _process_viral_learning_response(self, response: Dict[str, Any]) -> ProcessedResponse:
        """处理爆款学习工作流响应"""
        try:
            status = ResponseStatus.SUCCESS if response.get("success", True) else ResponseStatus.ERROR
            message = response.get("message", "Viral learning analysis completed")
            
            # 提取学习数据
            data = {
                "learning_insights": response.get("insights", []),
                "trending_topics": response.get("trending_topics", []),
                "recommendations": response.get("recommendations", []),
                "viral_patterns": response.get("viral_patterns", {})
            }
            
            metadata = {
                "analysis_count": len(response.get("analyzed_content", [])),
                "trend_score": response.get("trend_score"),
                "learning_cycle": response.get("cycle_number")
            }
            
            return ProcessedResponse(
                status=status,
                message=message,
                data=data,
                metadata=metadata
            )
            
        except Exception as e:
            log.error(f"Error processing viral learning response: {e}")
            raise
    
    async def _process_default_response(self, response: Dict[str, Any]) -> ProcessedResponse:
        """处理默认响应"""
        try:
            status = ResponseStatus.SUCCESS if response.get("success", True) else ResponseStatus.ERROR
            message = response.get("message", "Workflow completed")
            
            return ProcessedResponse(
                status=status,
                message=message,
                data=response.get("data", {}),
                metadata=response.get("metadata", {})
            )
            
        except Exception as e:
            log.error(f"Error processing default response: {e}")
            raise

# 全局响应处理器实例
response_processor = N8NResponseProcessor()