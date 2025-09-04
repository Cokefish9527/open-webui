"""
n8n工作流配置管理

基于实际的n8n工作流JSON文件配置webhook URL和路由规则
"""

import os
from typing import Dict, List, Any
from enum import Enum

class N8NWorkflowType(str, Enum):
    """n8n工作流类型 - 基于实际JSON文件"""
    MAIN = "main"  # 主工作流.json
    COMPANY_INFO = "company_info"  # 公司信息收集及作战地图梳理.json
    VIRAL_LEARNING = "viral_learning"  # 被动触发爆款学习.json（定时调用）

# n8n工作流webhook映射 - 基于实际的n8n工作流
# 更新为新的工作流地址
N8N_WORKFLOW_WEBHOOKS = {
    N8NWorkflowType.MAIN: os.getenv("N8N_MAIN_WORKFLOW_URL", "https://n8n.hsai.cc/webhook-test/n8n_chat"),
    N8NWorkflowType.COMPANY_INFO: os.getenv("N8N_COMPANY_INFO_WORKFLOW_URL", "https://n8n.hsai.cc/webhook-test/business_information_get"),
    N8NWorkflowType.VIRAL_LEARNING: os.getenv("N8N_VIRAL_LEARNING_WORKFLOW_URL", "https://n8n.hsai.cc/webhook-test/viral-learning")
}

# 对话入口类型配置 - 根据入口选择工作流
ENTRY_TYPE_WORKFLOW_MAPPING = {
    "chat": N8NWorkflowType.MAIN,           # 普通聊天入口 -> 主工作流
    "general": N8NWorkflowType.MAIN,        # 通用入口 -> 主工作流
    "default": N8NWorkflowType.MAIN,        # 默认入口 -> 主工作流
    "company": N8NWorkflowType.COMPANY_INFO,    # 公司信息入口 -> 收集信息工作流
    "business": N8NWorkflowType.COMPANY_INFO,   # 商业分析入口 -> 收集信息工作流
    "info_collection": N8NWorkflowType.COMPANY_INFO  # 信息收集入口 -> 收集信息工作流
}

# 工作流触发关键词配置（保留用于智能路由）
WORKFLOW_TRIGGER_KEYWORDS = {
    N8NWorkflowType.MAIN: [
        "帮助", "任务", "处理", "开始", "执行", "对话", "聊天", "问答"
    ],
    N8NWorkflowType.COMPANY_INFO: [
        "公司", "企业", "信息", "作战", "地图", "竞品", "分析", "调研", "情报", "收集"
    ],
    N8NWorkflowType.VIRAL_LEARNING: []  # 不通过关键词触发，仅定时调用
}

# 工作流超时配置（秒）
WORKFLOW_TIMEOUTS = {
    N8NWorkflowType.MAIN: 30,
    N8NWorkflowType.COMPANY_INFO: 60,
    N8NWorkflowType.VIRAL_LEARNING: 45
}

# 爆款学习工作流定时配置
VIRAL_LEARNING_SCHEDULE_CONFIG = {
    "enabled": True,
    "interval_minutes": 30,  # 每30分钟执行一次
    "max_daily_executions": 48,  # 每天最多48次
    "retry_attempts": 3,
    "retry_delay_seconds": 60,
    "execution_timeout": 300  # 5分钟超时
}

def get_workflow_config(workflow_type: N8NWorkflowType) -> Dict[str, Any]:
    """获取工作流配置"""
    return {
        "name": workflow_type.value,
        "webhook_url": N8N_WORKFLOW_WEBHOOKS.get(workflow_type),
        "timeout": WORKFLOW_TIMEOUTS.get(workflow_type, 30),
        "trigger_keywords": WORKFLOW_TRIGGER_KEYWORDS.get(workflow_type, []),
        "description": f"{workflow_type.value} workflow configuration"
    }

def get_all_workflow_configs() -> Dict[str, Dict[str, Any]]:
    """获取所有工作流配置"""
    return {
        workflow_type.value: get_workflow_config(workflow_type)
        for workflow_type in N8NWorkflowType
    }

def get_workflow_by_entry_type(entry_type: str) -> N8NWorkflowType:
    """根据入口类型获取工作流"""
    return ENTRY_TYPE_WORKFLOW_MAPPING.get(entry_type, N8NWorkflowType.MAIN)

def is_scheduled_workflow(workflow_type: N8NWorkflowType) -> bool:
    """判断是否为定时调度工作流"""
    return workflow_type == N8NWorkflowType.VIRAL_LEARNING

def get_viral_learning_schedule_config() -> Dict[str, Any]:
    """获取爆款学习工作流定时配置"""
    return VIRAL_LEARNING_SCHEDULE_CONFIG.copy()

def detect_entry_type(message_data: Dict[str, Any]) -> str:
    """检测对话入口类型"""
    # 从消息数据中提取入口类型
    entry_type = message_data.get("entry_type", "default")
    
    # 如果没有明确的入口类型，尝试从消息内容推断
    if entry_type == "default":
        content = message_data.get("content", "").lower()
        
        # 检查是否包含公司信息相关关键词
        company_keywords = ["公司", "企业", "信息", "作战", "地图", "竞品", "分析", "调研"]
        if any(keyword in content for keyword in company_keywords):
            entry_type = "company"
    
    return entry_type


# N8N工作流超时配置（秒）
N8N_WORKFLOW_TIMEOUT = {
    N8NWorkflowType.MAIN: 30,
    N8NWorkflowType.COMPANY_INFO: 60,
    N8NWorkflowType.VIRAL_LEARNING: 45
}

# 工作流描述
WORKFLOW_DESCRIPTIONS = {
    N8NWorkflowType.MAIN: "主工作流 - 处理通用对话和任务分发",
    N8NWorkflowType.COMPANY_INFO: "公司信息收集及作战地图梳理 - 收集公司信息并生成作战地图",
    N8NWorkflowType.VIRAL_LEARNING: "被动触发爆款学习 - 分析爆款内容并学习模式（定时调用）"
}

# 爆款学习工作流定时配置
VIRAL_LEARNING_SCHEDULE_CONFIG = {
    "enabled": True,
    "interval_minutes": 30,      # 每30分钟执行一次
    "max_daily_calls": 48,       # 每天最多48次
    "start_hour": 8,             # 开始时间：8点
    "end_hour": 22,              # 结束时间：22点
    "retry_attempts": 3,         # 失败重试次数
    "retry_delay_minutes": 5     # 重试间隔（分钟）
}

def get_workflow_config(workflow_type: N8NWorkflowType) -> Dict:
    """获取工作流配置"""
    return {
        "type": workflow_type.value,
        "webhook_url": N8N_WORKFLOW_WEBHOOKS[workflow_type],
        "keywords": WORKFLOW_TRIGGER_KEYWORDS[workflow_type],
        "timeout": WORKFLOW_TIMEOUTS[workflow_type],
        "description": WORKFLOW_DESCRIPTIONS[workflow_type]
    }

def get_all_workflow_configs() -> Dict[str, Dict]:
    """获取所有工作流配置"""
    return {
        workflow_type.value: get_workflow_config(workflow_type)
        for workflow_type in N8NWorkflowType
    }

def get_workflow_by_entry_type(entry_type: str) -> N8NWorkflowType:
    """根据对话入口类型选择工作流"""
    return ENTRY_TYPE_WORKFLOW_MAPPING.get(entry_type, N8NWorkflowType.MAIN)

def is_scheduled_workflow(workflow_type: N8NWorkflowType) -> bool:
    """检查是否为定时调用的工作流"""
    return workflow_type == N8NWorkflowType.VIRAL_LEARNING

def get_viral_learning_schedule_config() -> Dict:
    """获取爆款学习工作流的定时配置"""
    return VIRAL_LEARNING_SCHEDULE_CONFIG.copy()