"""
N8N工作流配置管理模块
负责动态加载、解析和管理n8n工作流配置
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum
import aiofiles
import asyncio
from datetime import datetime

log = logging.getLogger(__name__)

class WorkflowType(str, Enum):
    """工作流类型枚举"""
    MAIN = "main"
    COMPANY_INFO = "company_info"
    VIRAL_LEARNING = "viral_learning"
    VIDEO_ANALYSIS = "video_analysis"

class WorkflowConfig(BaseModel):
    """工作流配置模型"""
    id: str
    name: str
    type: WorkflowType
    description: str
    webhook_url: str
    webhook_method: str = "POST"
    timeout: int = 30
    retry_count: int = 3
    keywords: List[str] = Field(default_factory=list)
    priority: int = 1
    enabled: bool = True
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class N8NWorkflowManager:
    """N8N工作流管理器"""
    
    def __init__(self, workflow_dir: str = None):
        self.workflow_dir = workflow_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
            "backend", "n8n_workflows"
        )
        self.workflows: Dict[str, WorkflowConfig] = {}
        self.workflow_mappings = {
            "主工作流.json": {
                "type": WorkflowType.MAIN,
                "webhook_url": "http://localhost:5678/webhook/n8n_chat",
                "keywords": ["视频", "创作", "文案", "脚本", "发布", "tiktok", "抖音"],
                "description": "B2B智能视频创作主工作流，处理从关键词到视频发布的完整流程"
            },
            "公司信息收集及作战地图梳理.json": {
                "type": WorkflowType.COMPANY_INFO,
                "webhook_url": "http://localhost:5678/webhook/company_info",
                "keywords": ["公司", "企业", "信息", "作战", "地图", "竞品", "分析", "调研"],
                "description": "公司信息收集和竞品分析工作流"
            },
            "被动触发爆款学习.json": {
                "type": WorkflowType.VIRAL_LEARNING,
                "webhook_url": "http://localhost:5678/webhook/viral_learning",
                "keywords": ["爆款", "学习", "热门", "趋势", "分析"],
                "description": "被动触发的爆款内容学习和分析工作流"
            },
            "异步视频爬取关键词分析.json": {
                "type": WorkflowType.VIDEO_ANALYSIS,
                "webhook_url": "http://localhost:5678/webhook/video_analysis",
                "keywords": ["视频", "爬取", "关键词", "分析", "数据"],
                "description": "异步视频内容爬取和关键词分析工作流"
            }
        }
        
    async def initialize(self):
        """初始化工作流管理器"""
        log.info("Initializing N8N Workflow Manager...")
        await self.load_workflows()
        log.info(f"Loaded {len(self.workflows)} workflows")
        
    async def load_workflows(self):
        """从目录加载所有工作流配置"""
        try:
            workflow_path = Path(self.workflow_dir)
            if not workflow_path.exists():
                log.warning(f"Workflow directory not found: {self.workflow_dir}")
                return
                
            json_files = list(workflow_path.glob("*.json"))
            log.info(f"Found {len(json_files)} JSON files in {self.workflow_dir}")
            
            for json_file in json_files:
                try:
                    await self._load_single_workflow(json_file)
                except Exception as e:
                    log.error(f"Failed to load workflow {json_file.name}: {e}")
                    
        except Exception as e:
            log.error(f"Failed to load workflows: {e}")
            
    async def _load_single_workflow(self, json_file: Path):
        """加载单个工作流文件"""
        filename = json_file.name
        
        # 获取预定义的映射配置
        mapping = self.workflow_mappings.get(filename)
        if not mapping:
            log.warning(f"No mapping found for {filename}, skipping")
            return
            
        try:
            async with aiofiles.open(json_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                workflow_data = json.loads(content)
                
            # 提取工作流基本信息
            workflow_name = workflow_data.get('name', filename.replace('.json', ''))
            
            # 创建工作流配置
            config = WorkflowConfig(
                id=f"workflow_{mapping['type'].value}",
                name=workflow_name,
                type=mapping['type'],
                description=mapping['description'],
                webhook_url=mapping['webhook_url'],
                keywords=mapping['keywords'],
                timeout=self._extract_timeout(workflow_data),
                input_schema=self._extract_input_schema(workflow_data),
                output_schema=self._extract_output_schema(workflow_data)
            )
            
            self.workflows[config.id] = config
            log.info(f"Loaded workflow: {config.name} ({config.type})")
            
        except Exception as e:
            log.error(f"Error loading workflow {filename}: {e}")
            
    def _extract_timeout(self, workflow_data: Dict) -> int:
        """从工作流数据中提取超时配置"""
        # 默认超时时间，可以根据工作流复杂度调整
        timeout_mapping = {
            WorkflowType.MAIN: 60,
            WorkflowType.COMPANY_INFO: 120,
            WorkflowType.VIRAL_LEARNING: 45,
            WorkflowType.VIDEO_ANALYSIS: 90
        }
        return 30  # 默认值
        
    def _extract_input_schema(self, workflow_data: Dict) -> Dict[str, Any]:
        """从工作流数据中提取输入模式"""
        # 分析webhook节点的参数结构
        nodes = workflow_data.get('nodes', [])
        webhook_node = None
        
        for node in nodes:
            if node.get('type') == 'n8n-nodes-base.webhook':
                webhook_node = node
                break
                
        if webhook_node:
            # 基于webhook配置推断输入模式
            return {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "用户输入消息"},
                    "session_id": {"type": "string", "description": "会话ID"},
                    "business_name": {"type": "string", "description": "业务名称"},
                    "user_id": {"type": "string", "description": "用户ID"}
                },
                "required": ["message"]
            }
        
        return {}
        
    def _extract_output_schema(self, workflow_data: Dict) -> Dict[str, Any]:
        """从工作流数据中提取输出模式"""
        # 分析响应节点的结构
        nodes = workflow_data.get('nodes', [])
        response_node = None
        
        for node in nodes:
            if node.get('type') == 'n8n-nodes-base.respondToWebhook':
                response_node = node
                break
                
        if response_node:
            return {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "messageType": {"type": "string"},
                    "session_id": {"type": "string"},
                    "business_name": {"type": "string"},
                    "displayText": {"type": "string"},
                    "data": {"type": "object"},
                    "file_preview": {"type": "integer"},
                    "create_ts": {"type": "string"}
                }
            }
            
        return {}
        
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowConfig]:
        """获取指定工作流配置"""
        return self.workflows.get(workflow_id)
        
    def get_workflows_by_type(self, workflow_type: WorkflowType) -> List[WorkflowConfig]:
        """根据类型获取工作流列表"""
        return [wf for wf in self.workflows.values() if wf.type == workflow_type]
        
    def get_all_workflows(self) -> List[WorkflowConfig]:
        """获取所有工作流配置"""
        return list(self.workflows.values())
        
    def search_workflows_by_keywords(self, keywords: List[str]) -> List[WorkflowConfig]:
        """根据关键词搜索匹配的工作流"""
        matched_workflows = []
        
        for workflow in self.workflows.values():
            if not workflow.enabled:
                continue
                
            # 计算关键词匹配度
            match_score = 0
            for keyword in keywords:
                keyword_lower = keyword.lower()
                for wf_keyword in workflow.keywords:
                    if keyword_lower in wf_keyword.lower() or wf_keyword.lower() in keyword_lower:
                        match_score += 1
                        
            if match_score > 0:
                matched_workflows.append((workflow, match_score))
                
        # 按匹配度和优先级排序
        matched_workflows.sort(key=lambda x: (x[1], x[0].priority), reverse=True)
        return [wf[0] for wf in matched_workflows]
        
    async def reload_workflows(self):
        """重新加载工作流配置"""
        log.info("Reloading workflows...")
        self.workflows.clear()
        await self.load_workflows()
        
    def get_workflow_stats(self) -> Dict[str, Any]:
        """获取工作流统计信息"""
        total = len(self.workflows)
        enabled = sum(1 for wf in self.workflows.values() if wf.enabled)
        by_type = {}
        
        for wf in self.workflows.values():
            wf_type = wf.type.value
            by_type[wf_type] = by_type.get(wf_type, 0) + 1
            
        return {
            "total_workflows": total,
            "enabled_workflows": enabled,
            "disabled_workflows": total - enabled,
            "workflows_by_type": by_type,
            "last_loaded": datetime.now().isoformat()
        }

# 全局工作流管理器实例
workflow_manager = N8NWorkflowManager()