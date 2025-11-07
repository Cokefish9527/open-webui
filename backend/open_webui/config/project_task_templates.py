PROJECT_MAIN_TASK_TEMPLATES = {
    "company_info_collection": {
        "title": "企业信息收集",
        "description": "在企业创建阶段收集法人主体、行业、规模等基础信息，为后续蓝图编排提供数据基线。",
        "task_type": "workflow_execution",
        "task_category": "main",
        "workflow_type": "company_info_collection",
        "priority": 95,
        "config": {
            "seed_default_project": True,
            "template_scope": "company_seed",
            "template_key": "company_info_collection",
            "auto_complete_on_blueprint": True,
            "checklist": [
                "确认企业工商主体、品牌名称与统一社会信用代码",
                "收集主营行业、成立年份、核心产品线",
                "确认联系人/企业负责人账号与可用渠道",
            ],
        },
        "prompt_config": {
            "system_prompt": (
                "You are an enterprise onboarding assistant. Collect required business facts "
                "so downstream workflows can trust the data."
            ),
            "initial_message": "您好！为了后续自动化编排，请先补充企业的基础信息。",
            "guidance_questions": [
                "企业法定名称和主要品牌名称是什么？",
                "企业主营行业与核心产品线有哪些？",
                "企业负责人/联系人是谁？请提供邮箱或电话。",
                "企业目前的社媒账号或内容渠道是否已经准备好？",
            ],
            "completion_criteria": "企业名称、行业、规模、联系人信息均已确认，并写入企业档案。",
            "success_message": "企业信息收集完毕，我们会据此继续配置蓝图与任务。",
        },
        "notifications": {
            "on_create": True,
            "on_update": True,
        },
    },
    "company_info": {
        "title": "完善企业信息",
        "description": "收集公司名称、行业、规模等基础资料，用于后续工作流初始化。",
        "task_type": "workflow_execution",
        "task_category": "main",
        "workflow_type": "company_info",
        "priority": 10,
        "prompt_config": {
            "system_prompt": "You are an onboarding assistant. Guide the user to provide the company's basic profile.",
            "initial_message": "您好！为了后续更好地推进项目，请先补充企业的基础信息。",
            "guidance_questions": [
                "公司的全称是什么？",
                "主营行业属于哪一类？",
                "目前团队大约有多少人？",
                "公司成立于哪一年？",
            ],
            "completion_criteria": "用户提供了公司名称、行业、规模与成立年份等基础信息。",
            "success_message": "感谢提供企业资料，我们已完成记录。",
        },
    },
    "project_info": {
        "title": "完善项目信息",
        "description": "明确项目目标、交付物、关键时间节点与依赖，为后续执行提供依据。",
        "task_type": "workflow_execution",
        "task_category": "main",
        "workflow_type": "project_info",
        "priority": 9,
        "prompt_config": {
            "system_prompt": "You are a project intake assistant. Collect the key information required to launch this initiative.",
            "initial_message": "为了明确项目目标与排期，请帮助我们确认项目的核心信息。",
            "guidance_questions": [
                "本项目希望达到的主要目标是什么？",
                "预期产出或交付物有哪些？",
                "计划的启动时间与结束时间分别是？",
                "当前是否存在需要重点关注的风险或依赖？",
            ],
            "completion_criteria": "用户补充了项目目标、产出、时间计划与关键风险。",
            "success_message": "感谢提供项目信息，我们会据此安排后续工作。",
        },
    },
    "material_init": {
        "title": "素材库初始化",
        "description": "收集图片、视频、文档等关键素材，建立项目专属资源库。",
        "task_type": "material_processing",
        "task_category": "main",
        "workflow_type": "material_init",
        "priority": 8,
        "prompt_config": {
            "system_prompt": "You are a content librarian. Help the user initialise the asset library required for this project.",
            "initial_message": "我们需要收集项目相关的素材，请根据提示上传现有内容。",
            "guidance_questions": [
                "请上传与项目相关的图片或品牌视觉素材。",
                "如果有既定的视频素材，请一并提供。",
                "补充能够说明项目背景的文档、方案或案例。",
            ],
            "completion_criteria": "用户已经完成图片、视频及文档等核心素材的首次上传。",
            "success_message": "素材库初始化完成，后续可随时追加或更新。",
        },
    },
}
