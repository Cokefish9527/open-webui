import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from open_webui.models.hsai_projects import (
    HSAIProjects,
    HSAIProjectForm,
    HSAIProjectUpdateForm,
    HSAIProjectResponse,
    PaginatedHSAIProjectResponse,
    PaginationData
)

from open_webui.models.hsai_tasks import (
    HSAITasks,
    HSAITaskForm,
    HSAITaskResponse,
    HSAITaskStatus,
    HSAIRecurringState,
    HSAITaskStateLogs
)
from open_webui.models.hsai_tasks import HSAITaskModel
from open_webui.models.hsai_blueprint_progress import (
    HSAIBlueprintProgressTable,
    BlueprintProgressState,
    HSAITaskBlueprintLinksTable
)

from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/projects", tags=["HSAI 项目管理"])


class BlueprintSummary(BaseModel):
    version: Optional[str] = None
    progress_state: Optional[BlueprintProgressState] = None
    last_synced_at: Optional[int] = None
    execution_duration_days: Optional[int] = None
    planned_total_posts: Optional[str] = None
    posting_frequency: Optional[str] = None
    required_tiktok_accounts: Optional[str] = None
    planned_end_at: Optional[int] = None
    daily_cycle_config: Optional[Dict[str, Any]] = None


class TaskStat(BaseModel):
    total: int
    completed: int


class RecurringTaskInfo(BaseModel):
    id: str
    title: str
    status: str
    recurring_state: Optional[str] = None
    next_run_at: Optional[int] = None
    last_run_at: Optional[int] = None


class RecurringLogEntry(BaseModel):
    id: str
    task_id: str
    from_state: Optional[str] = None
    to_state: str
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    source: Optional[str] = None
    message: Optional[str] = None
    created_at: int


class ProjectSummaryResponse(BaseModel):
    project: HSAIProjectResponse
    blueprint: Optional[BlueprintSummary] = None
    main_tasks: TaskStat
    recurring_tasks: TaskStat
    recurring_items: List[RecurringTaskInfo]
    recent_logs: List[RecurringLogEntry]
    blueprint_links: List[Dict[str, Any]]


# 项目模板定义
PROJECT_MAIN_TASK_TEMPLATES = {
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
                "公司成立于哪一年？"
            ],
            "completion_criteria": "用户提供了公司名称、行业、规模与成立年份等基础信息。",
            "success_message": "感谢提供企业资料，我们已完成记录。"
        }
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
                "当前是否存在需要重点关注的风险或依赖？"
            ],
            "completion_criteria": "用户补充了项目目标、产出、时间计划与关键风险。",
            "success_message": "感谢提供项目信息，我们会据此安排后续工作。"
        }
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
                "补充能够说明项目背景的文档、方案或案例。"
            ],
            "completion_criteria": "用户已经完成图片、视频及文档等核心素材的首次上传。",
            "success_message": "素材库初始化完成，后续可随时追加或更新。"
        }
    }
}

@router.get("/", response_model=PaginatedHSAIProjectResponse, summary="获取项目列表")
async def get_projects(
    status: Optional[str] = Query(None, description="项目状态过滤"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引（从 1 开始）", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取用户的项目列表（分页）。
    
    Args:
        status (Optional[str]): 项目状态过滤
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAIProjectResponse: 分页的项目列表
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        projects = HSAIProjects.get_projects_by_user_id(
            user.id,
            status=status,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = HSAIProjects.get_projects_count(
            user.id,
            status=status
        )
        
        responses = [HSAIProjectResponse(**project.model_dump()) for project in projects]
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIProjectResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/", response_model=HSAIProjectResponse, summary="创建项目")
async def create_project(
    form_data: HSAIProjectForm,
    user=Depends(get_verified_user)
):
    """
    创建新的项目。
    
    创建项目后会自动创建主线任务。
    
    Args:
        form_data (HSAIProjectForm): 项目创建表单
        user: 已认证的用户对象
        
    Returns:
        HSAIProjectResponse: 创建的项目信息
    """
    try:
        project = HSAIProjects.insert_new_project(user.id, form_data)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create project"
            )
        
        # 创建主线任务
        main_tasks = []
        for template_key, template in PROJECT_MAIN_TASK_TEMPLATES.items():
            task_form = HSAITaskForm(
                title=template["title"],
                description=template["description"],
                task_type=template["task_type"],
                task_category=template["task_category"],
                project_id=project.id,
                priority=template["priority"],
                prompt_config=template["prompt_config"]
            )
            
            task = HSAITasks.insert_new_task(user.id, task_form)
            if task:
                main_tasks.append(task)
        
        log.info(f"Created {len(main_tasks)} main tasks for project {project.id}")
        
        return HSAIProjectResponse(**project.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{project_id}", response_model=HSAIProjectResponse, summary="获取项目详情")
async def get_project(
    project_id: str,
    user=Depends(get_verified_user)
):
    """获取单个项目详情"""
    try:
        project = HSAIProjects.get_project_by_id(project_id)
        if not project or project.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return HSAIProjectResponse(**project.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/{project_id}", response_model=HSAIProjectResponse, summary="更新项目")
async def update_project(
    project_id: str,
    form_data: HSAIProjectUpdateForm,
    user=Depends(get_verified_user)
):
    """更新项目。
    
    更新指定项目的详细信息。
    
    Args:
        project_id (str): 项目ID
        form_data (HSAIProjectUpdateForm): 项目更新表单
        user: 已认证的用户对象
        
    Returns:
        HSAIProjectResponse: 更新后的项目信息
        
    Raises:
        HTTPException: 404 - 项目未找到
        HTTPException: 400 - 项目更新失败
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 楠岃瘉椤圭洰鎵€鏈夋潈
        existing_project = HSAIProjects.get_project_by_id(project_id)
        if not existing_project or existing_project.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        project = HSAIProjects.update_project_by_id(project_id, form_data)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update project"
            )
        
        return HSAIProjectResponse(**project.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.delete("/{project_id}", response_model=bool, summary="删除项目")
async def delete_project(
    project_id: str,
    user=Depends(get_verified_user)
):
    """删除项目。
    
    删除指定项目及其关联的所有任务。
    
    Args:
        project_id (str): 项目ID
        user: 已认证的用户对象
        
    Returns:
        bool: 删除成功返回True
        
    Raises:
        HTTPException: 404 - 项目未找到
        HTTPException: 400 - 项目删除失败
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 楠岃瘉椤圭洰鎵€鏈夋潈
        existing_project = HSAIProjects.get_project_by_id(project_id)
        if not existing_project or existing_project.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        result = HSAIProjects.delete_project_by_id(project_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete project"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error deleting project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{project_id}/tasks", response_model=List[HSAITaskResponse], summary="获取项目任务列表")
async def get_project_tasks(
    project_id: str,
    user=Depends(get_verified_user)
):
    """获取指定项目关联的所有任务。
    
    Args:
        project_id (str): 项目ID
        user: 已认证的用户对象
        
    Returns:
        List[HSAITaskResponse]: 项目关联的任务列表
        
    Raises:
        HTTPException: 404 - 项目未找到
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 楠岃瘉椤圭洰鎵€鏈夋潈
        project = HSAIProjects.get_project_by_id(project_id)
        if not project or project.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # 鑾峰彇椤圭洰鍏宠仈鐨勪换鍔?
        tasks = HSAITasks.get_tasks_by_user_id(user.id, project_id=project_id)
        responses = [HSAITaskResponse(**task.model_dump()) for task in tasks]
        
        return responses
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting project tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse, summary="项目任务摘要")
async def get_project_summary(
    project_id: str,
    user=Depends(get_verified_user),
):
    """获取项目任务摘要信息。
    
    包括项目基本信息、蓝图进度、主要任务统计、循环任务统计、最近日志等。
    
    Args:
        project_id (str): 项目ID
        user: 已认证的用户对象
        
    Returns:
        ProjectSummaryResponse: 项目摘要信息
            - project: 项目基本信息
            - blueprint: 蓝图进度信息
            - main_tasks: 主要任务统计(总数和完成数)
            - recurring_tasks: 循环任务统计(总数和活跃数)
            - recurring_items: 循环任务列表
            - recent_logs: 最近的循环任务日志
            - blueprint_links: 蓝图链接信息
            
    Raises:
        HTTPException: 404 - 项目未找到
        HTTPException: 500 - 服务器内部错误
    """
    try:
        project = HSAIProjects.get_project_by_id(project_id)
        if not project or project.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        project_resp = HSAIProjectResponse(**project.model_dump())

        blueprint_summary: Optional[BlueprintSummary] = None
        blueprint_links: List[Dict[str, Any]] = []

        progress = HSAIBlueprintProgressTable.get_by_project(project_id)
        if progress:
            days = None
            try:
                if progress.execution_duration_days:
                    digits = "".join(c for c in progress.execution_duration_days if c.isdigit())
                    days = int(digits) if digits else None
            except ValueError:
                days = None

            planned_end_at = None
            if days and progress.last_synced_at:
                planned_end_at = int(
                    (
                        datetime.fromtimestamp(progress.last_synced_at, tz=timezone.utc)
                        + timedelta(days=days)
                    ).timestamp()
                )

            blueprint_summary = BlueprintSummary(
                version=progress.blueprint_version,
                progress_state=progress.progress_state,
                last_synced_at=progress.last_synced_at,
                execution_duration_days=days,
                planned_total_posts=progress.planned_total_posts,
                posting_frequency=progress.posting_frequency,
                required_tiktok_accounts=progress.required_tiktok_accounts,
                planned_end_at=planned_end_at,
                daily_cycle_config=progress.daily_cycle_config,
            )

            links = HSAITaskBlueprintLinksTable.get_by_progress(progress.id)
            for link in links:
                        blueprint_links.append(
                            {
                                "task_id": link.task_id,
                                "template_key": link.template_key,
                                "metadata": link.link_metadata or {},
                            }
                        )

        tasks: List[HSAITaskModel] = HSAITasks.get_tasks_by_user_id(
            user.id, project_id=project_id, limit=500
        )

        main_total = 0
        main_completed = 0
        recurring_total = 0
        recurring_active = 0
        recurring_items: List[RecurringTaskInfo] = []

        for task in tasks:
            if task.parent_task_id:
                continue
            category = (task.task_category or "").lower()
            is_recurring = task.is_recurring or category.startswith("blueprint_daily")
            if is_recurring:
                recurring_total += 1
                if (task.recurring_state or "").lower() == HSAIRecurringState.ACTIVE.value:
                    recurring_active += 1
                recurring_items.append(
                    RecurringTaskInfo(
                        id=task.id,
                        title=task.title,
                        status=task.status,
                        recurring_state=task.recurring_state,
                        next_run_at=task.next_run_at,
                        last_run_at=task.last_run_at,
                    )
                )
            else:
                main_total += 1
                if task.status == HSAITaskStatus.COMPLETED:
                    main_completed += 1

        recent_logs: List[RecurringLogEntry] = []
        for item in recurring_items:
            logs = HSAITaskStateLogs.list_logs(item.id, limit=5)
            for entry in logs:
                recent_logs.append(
                    RecurringLogEntry(
                        id=entry.id,
                        task_id=entry.task_id,
                        from_state=entry.from_state,
                        to_state=entry.to_state,
                        operator_id=entry.operator_id,
                        operator_name=entry.operator_name,
                        source=entry.source,
                        message=entry.message,
                        created_at=entry.created_at,
                    )
                )
        recent_logs.sort(key=lambda x: x.created_at, reverse=True)
        recent_logs = recent_logs[:20]

        return ProjectSummaryResponse(
            project=project_resp,
            blueprint=blueprint_summary,
            main_tasks=TaskStat(total=main_total, completed=main_completed),
            recurring_tasks=TaskStat(total=recurring_total, completed=recurring_active),
            recurring_items=recurring_items,
            recent_logs=recent_logs,
            blueprint_links=blueprint_links,
        )

    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Error generating project summary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )
