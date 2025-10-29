"""
Strategic blueprint task templates.

These templates are used when syncing blueprint progress to generate
or update the main tasks that drive project execution. Each template
describes a canonical task with metadata that can be extended later
without changing the sync orchestration logic.
"""

from __future__ import annotations

from typing import Dict, Any


BLUEPRINT_MAIN_TASK_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "social_matrix_setup": {
        "title": "社媒矩阵创建",
        "description": "根据战略蓝图规划完成主要社媒账号的初始化、配置与权限校验。",
        "task_type": "workflow_execution",
        "task_category": "blueprint_main",
        "priority": 90,
        "config": {
            "blueprint_section": "social_matrix",
            "checklist": [
                "确认目标平台账号是否齐备",
                "完成品牌素材与简介配置",
                "同步权限与安全策略"
            ],
        },
        "notifications": {
            "on_create": True,
            "on_update": True,
        },
    },
    "material_enrichment": {
        "title": "素材补充",
        "description": "依照蓝图素材策略准备与补充视频/图文素材，并完成分类入库。",
        "task_type": "material_processing",
        "task_category": "blueprint_main",
        "priority": 80,
        "config": {
            "blueprint_section": "materials",
            "checklist": [
                "汇总蓝图列出的高优先级素材类型",
                "补充缺失的模板素材与字幕脚本",
                "登记素材元数据以便检索"
            ],
        },
        "notifications": {
            "on_create": True,
            "on_update": True,
        },
    },
    "video_learning": {
        "title": "视频学习",
        "description": "依据蓝图指定的竞品与案例完成视频学习记录与心得总结。",
        "task_type": "content_analysis",
        "task_category": "blueprint_main",
        "priority": 70,
        "config": {
            "blueprint_section": "video_learning",
            "checklist": [
                "完成指定竞品案例学习打卡",
                "记录学习笔记与可复用套路",
                "输出关键洞察到知识库"
            ],
        },
        "notifications": {
            "on_create": True,
            "on_update": True,
        },
    },
    "daily_publish_cycle": {
        "title": "每日视频发布循环",
        "description": "在满足蓝图先决条件后，按计划每日生成并下发视频发布子任务。",
        "task_type": "platform_publishing",
        "task_category": "blueprint_main",
        "priority": 60,
        "config": {
            "blueprint_section": "daily_publish",
            "recurring": True,
            "default_window": {
                "hour": 9,
                "minute": 0,
                "timezone": "Asia/Shanghai",
            },
            "dependencies": [
                "social_matrix_setup",
                "material_enrichment",
                "video_learning",
            ],
        },
        "notifications": {
            "on_create": True,
            "on_update": True,
        },
    },
}


def get_template(template_key: str) -> Dict[str, Any]:
    """Helper to fetch a template definition by key."""
    return BLUEPRINT_MAIN_TASK_TEMPLATES.get(template_key, {})
