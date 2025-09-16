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
    
    @staticmethod
    async def process_response(
        raw_response: Dict[str, Any], 
        workflow_type: str,
        execution_start_time: float,
        execution_id: Optional[str] = None
    ) -> ProcessedResponse:
        """
        处理n8n工作流响应
        
        Args:
            raw_response: n8n返回的原始响应
            workflow_type: 工作流类型
            execution_start_time: 执行开始时间
            execution_id: 执行ID
            
        Returns:
            ProcessedResponse: 处理后的结构化响应
        """
        try:
            log.info(f"[响应处理] 开始处理工作流 {workflow_type} 的响应 (执行ID: {execution_id})")
            log.info(f"[响应处理] 原始响应数据: {raw_response}")
            
            # 创建处理器实例
            processor = N8NResponseProcessor()
            
            # 获取对应的处理器
            handler = processor.processors.get(workflow_type, processor._process_default_response)
            log.info(f"[响应处理] 使用处理器: {handler.__name__}")
            
            # 处理响应
            processed = await handler(raw_response)
            processed.workflow_type = workflow_type
            processed.execution_id = execution_id
            
            log.info(f"[响应处理] 响应处理完成: status={processed.status}, message={processed.message}")
            log.info(f"[响应处理] 工作流 {workflow_type} 响应处理完成: {processed.status}")
            return processed
            
        except Exception as e:
            error_msg = f"处理工作流 {workflow_type} 响应时发生错误: {e}"
            log.error(f"[响应处理] {error_msg}", exc_info=True)
            error_response = ProcessedResponse(
                status=ResponseStatus.ERROR,
                message=f"响应处理失败: {str(e)}",
                workflow_type=workflow_type,
                execution_id=execution_id,
                metadata={"error": str(e), "raw_response": raw_response}
            )
            log.info(f"[响应处理] 返回错误响应: {error_response}")
            return error_response
    
    @staticmethod
    def format_for_client(processed_response: ProcessedResponse) -> Dict[str, Any]:
        """
        将处理后的响应格式化为客户端可用的格式
        
        Args:
            processed_response: 处理后的响应
            
        Returns:
            Dict: 客户端可用的响应格式
        """
        try:
            log.info(f"[客户端格式化] 开始格式化客户端响应: {processed_response}")
            
            # 根据对接文档规范格式化响应
            response_data = {
                "success": processed_response.status == ResponseStatus.SUCCESS,
                "messageType": 3,  # 默认使用Agent2Redis消息体的content_type=3 (text)
                "displayText": processed_response.message,
                "data": processed_response.data,
                "status": processed_response.status.value,
                "timestamp": int(processed_response.timestamp.timestamp()) if processed_response.timestamp else None
            }
            
            # 如果有执行ID，添加到响应中
            if processed_response.execution_id:
                response_data["execution_id"] = processed_response.execution_id
                
            log.info(f"[客户端格式化] 客户端响应格式化完成: {response_data}")
            return response_data
            
        except Exception as e:
            error_msg = f"格式化客户端响应时发生错误: {e}"
            log.error(f"[客户端格式化] {error_msg}", exc_info=True)
            error_response = {
                "success": False,
                "messageType": "error",
                "displayText": "响应格式化失败",
                "data": None,
                "status": "error",
                "error": str(e)
            }
            log.info(f"[客户端格式化] 返回错误响应: {error_response}")
            return error_response
    
    async def _process_main_workflow_response(self, response: Dict[str, Any]) -> ProcessedResponse:
        """处理主工作流响应"""
        try:
            log.info(f"[主工作流处理] 开始处理主工作流响应: {response}")
            # 提取主要信息
            status = ResponseStatus.SUCCESS if response.get("success", True) else ResponseStatus.ERROR
            # 优先使用displayText，其次是message，最后是output
            message = response.get("displayText", response.get("message", response.get("output", "主工作流执行完成")))
            
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
            
            processed = ProcessedResponse(
                status=status,
                message=message,
                data=data,
                metadata=metadata
            )
            log.info(f"[主工作流处理] 主工作流响应处理完成: {processed}")
            return processed
            
        except Exception as e:
            log.error(f"[主工作流处理] 处理主工作流响应时发生错误: {e}", exc_info=True)
            raise
    
    async def _process_company_info_response(self, response: Dict[str, Any]) -> ProcessedResponse:
        """处理公司信息收集工作流响应"""
        try:
            log.info(f"[公司信息处理] 开始处理公司信息工作流响应: {response}")
            status = ResponseStatus.SUCCESS if response.get("success", True) else ResponseStatus.ERROR
            # 优先使用displayText，其次是message，最后是output
            message = response.get("displayText", response.get("message", response.get("output", "公司信息收集完成")))
            
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
            
            processed = ProcessedResponse(
                status=status,
                message=message,
                data=data,
                metadata=metadata
            )
            log.info(f"[公司信息处理] 公司信息响应处理完成: {processed}")
            return processed
            
        except Exception as e:
            log.error(f"[公司信息处理] 处理公司信息响应时发生错误: {e}", exc_info=True)
            raise
    
    async def _process_viral_learning_response(self, response: Dict[str, Any]) -> ProcessedResponse:
        """处理爆款学习工作流响应"""
        try:
            log.info(f"[爆款学习处理] 开始处理爆款学习工作流响应: {response}")
            status = ResponseStatus.SUCCESS if response.get("success", True) else ResponseStatus.ERROR
            # 优先使用displayText，其次是message，最后是output
            message = response.get("displayText", response.get("message", response.get("output", "爆款学习分析完成")))
            
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
            
            processed = ProcessedResponse(
                status=status,
                message=message,
                data=data,
                metadata=metadata
            )
            log.info(f"[爆款学习处理] 爆款学习响应处理完成: {processed}")
            return processed
            
        except Exception as e:
            log.error(f"[爆款学习处理] 处理爆款学习响应时发生错误: {e}", exc_info=True)
            raise
    
    async def _process_default_response(self, response: Dict[str, Any]) -> ProcessedResponse:
        """处理默认响应"""
        try:
            log.info(f"[默认处理] 开始处理默认响应: {response}")
            status = ResponseStatus.SUCCESS if response.get("success", True) else ResponseStatus.ERROR
            # 优先使用displayText，其次是message，最后是output
            message = response.get("displayText", response.get("message", response.get("output", "工作流执行完成")))
            
            processed = ProcessedResponse(
                status=status,
                message=message,
                data=response.get("data", {}),
                metadata=response.get("metadata", {})
            )
            log.info(f"[默认处理] 默认响应处理完成: {processed}")
            return processed
            
        except Exception as e:
            log.error(f"[默认处理] 处理默认响应时发生错误: {e}", exc_info=True)
            raise

# 全局响应处理器实例
response_processor = N8NResponseProcessor()