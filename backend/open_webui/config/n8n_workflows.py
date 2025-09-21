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
    VIDEO_CRAWL = "video_crawl"  # 触发爆款抓取工作流
    VIRAL_LEARNING = "viral_learning"  # 爆款学习工作流

# n8n工作流webhook映射 - 基于实际的n8n工作流
# 更新为线上工作流地址
N8N_WORKFLOW_WEBHOOKS = {
    N8NWorkflowType.MAIN: os.getenv("N8N_MAIN_WORKFLOW_URL", "https://n8n.hsai.cc/webhook-test/n8n_chat"),
    N8NWorkflowType.COMPANY_INFO: os.getenv("N8N_COMPANY_INFO_WORKFLOW_URL", "https://webhook-n8n.hsai.cc/webhook/business_information_get"),
    N8NWorkflowType.VIDEO_CRAWL: os.getenv("N8N_VIDEO_CRAWL_WORKFLOW_URL", "https://webhook-n8n.hsai.cc/webhook/video_crawl"),
    N8NWorkflowType.VIRAL_LEARNING: os.getenv("N8N_VIRAL_LEARNING_WORKFLOW_URL", "https://webhook-n8n.hsai.cc/webhook/viral_learning")
}

# 对话入口类型配置 - 根据入口选择工作流
# 只保留四组映射：主工作流、公司信息收集工作流、触发爆款抓取工作流、爆款学习工作流
ENTRY_TYPE_WORKFLOW_MAPPING = {
    "chat": N8NWorkflowType.MAIN,              # 普通聊天入口 -> 主工作流
    "company": N8NWorkflowType.COMPANY_INFO,   # 公司信息入口 -> 公司信息收集工作流
    "video_crawl": N8NWorkflowType.VIDEO_CRAWL, # 视频抓取入口 -> 触发爆款抓取工作流
    "viral_learning": N8NWorkflowType.VIRAL_LEARNING  # 爆款学习入口 -> 爆款学习工作流
}

# 工作流触发关键词配置（保留用于智能路由）
WORKFLOW_TRIGGER_KEYWORDS = {
    N8NWorkflowType.MAIN: [
        "帮助", "任务", "处理", "开始", "执行", "对话", "聊天", "问答"
    ],
    N8NWorkflowType.COMPANY_INFO: [
        "公司", "企业", "信息", "作战", "地图", "竞品", "分析", "调研", "情报", "收集"
    ],
    N8NWorkflowType.VIDEO_CRAWL: [
        "视频", "抓取", "爬取", "爆款"
    ],
    N8NWorkflowType.VIRAL_LEARNING: [
        "学习", "爆款", "热门", "趋势"
    ]
}

# 工作流超时配置（秒）
WORKFLOW_TIMEOUTS = {
    N8NWorkflowType.MAIN: 30,
    N8NWorkflowType.COMPANY_INFO: 60,
    N8NWorkflowType.VIDEO_CRAWL: 120,
    N8NWorkflowType.VIRAL_LEARNING: 45
}

# N8N工作流超时配置（秒）
N8N_WORKFLOW_TIMEOUT = {
    N8NWorkflowType.MAIN: 30,
    N8NWorkflowType.COMPANY_INFO: 60,
    N8NWorkflowType.VIDEO_CRAWL: 120,
    N8NWorkflowType.VIRAL_LEARNING: 45
}

# 工作流描述
WORKFLOW_DESCRIPTIONS = {
    N8NWorkflowType.MAIN: "主工作流 - 处理通用对话和任务分发",
    N8NWorkflowType.COMPANY_INFO: "公司信息收集及作战地图梳理 - 收集公司信息并生成作战地图",
    N8NWorkflowType.VIDEO_CRAWL: "触发爆款抓取工作流 - 触发视频内容抓取任务",
    N8NWorkflowType.VIRAL_LEARNING: "爆款学习工作流 - 分析爆款内容并学习模式"
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

def get_viral_learning_schedule_config() -> Dict[str, Any]:
    """获取爆款学习工作流定时配置"""
    # 从环境变量读取配置，支持空值
    enabled_str = os.getenv("VIRAL_LEARNING_ENABLED")
    interval_minutes_str = os.getenv("VIRAL_LEARNING_INTERVAL_MINUTES")
    max_daily_calls_str = os.getenv("VIRAL_LEARNING_MAX_DAILY_CALLS")
    start_hour_str = os.getenv("VIRAL_LEARNING_START_HOUR")
    end_hour_str = os.getenv("VIRAL_LEARNING_END_HOUR")
    retry_attempts_str = os.getenv("VIRAL_LEARNING_RETRY_ATTEMPTS")
    retry_delay_minutes_str = os.getenv("VIRAL_LEARNING_RETRY_DELAY_MINUTES")
    
    # 如果enabled_str为空值或"false"，则禁用调度器
    enabled = True
    if enabled_str is None or enabled_str.lower() in ("", "false", "0", "no"):
        enabled = False
    
    # 解析其他配置项，如果为空则使用默认值
    interval_minutes = 30
    if interval_minutes_str and interval_minutes_str.strip():
        try:
            interval_minutes = int(interval_minutes_str)
        except ValueError:
            pass  # 使用默认值
    
    max_daily_calls = 48
    if max_daily_calls_str and max_daily_calls_str.strip():
        try:
            max_daily_calls = int(max_daily_calls_str)
        except ValueError:
            pass  # 使用默认值
    
    start_hour = 8
    if start_hour_str and start_hour_str.strip():
        try:
            start_hour = int(start_hour_str)
        except ValueError:
            pass  # 使用默认值
    
    end_hour = 22
    if end_hour_str and end_hour_str.strip():
        try:
            end_hour = int(end_hour_str)
        except ValueError:
            pass  # 使用默认值
    
    retry_attempts = 3
    if retry_attempts_str and retry_attempts_str.strip():
        try:
            retry_attempts = int(retry_attempts_str)
        except ValueError:
            pass  # 使用默认值
    
    retry_delay_minutes = 5
    if retry_delay_minutes_str and retry_delay_minutes_str.strip():
        try:
            retry_delay_minutes = int(retry_delay_minutes_str)
        except ValueError:
            pass  # 使用默认值
    
    return {
        "enabled": enabled,
        "interval_minutes": interval_minutes,
        "max_daily_calls": max_daily_calls,
        "start_hour": start_hour,
        "end_hour": end_hour,
        "retry_attempts": retry_attempts,
        "retry_delay_minutes": retry_delay_minutes
    }

def detect_entry_type(message_data: Dict[str, Any]) -> str:
    """检测对话入口类型"""
    # 从消息数据中提取入口类型
    entry_type = message_data.get("entry_type", "chat")
    
    # 如果没有明确的入口类型，尝试从消息内容推断
    if entry_type == "chat":
        content = message_data.get("content", "").lower()
        
        # 检查是否包含公司信息相关关键词
        company_keywords = ["公司", "企业", "信息", "作战", "地图", "竞品", "分析", "调研"]
        if any(keyword in content for keyword in company_keywords):
            entry_type = "company"
    
    return entry_type