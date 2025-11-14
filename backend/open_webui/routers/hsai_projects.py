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
    HSAITaskStateLogs,
)
from open_webui.models.hsai_tasks import HSAITaskModel
from open_webui.models.hsai_blueprint_progress import (
    HSAIBlueprintProgressTable,
    BlueprintProgressState,
    HSAITaskBlueprintLinksTable,
)
from open_webui.services.task_template_registry import task_template_registry

from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/projects", tags=["HSAI 椤圭洰绠＄悊"])


def _is_super_admin(user) -> bool:
    return bool(getattr(user, "is_super_admin", False))


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


@router.get("", response_model=PaginatedHSAIProjectResponse, summary="鑾峰彇椤圭洰鍒楄〃")
async def get_projects(
    status: Optional[str] = Query(None, description="项目状态过滤"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引（从 1 开始）", ge=1),
    user=Depends(get_verified_user)
):
    """
    鑾峰彇鐢ㄦ埛鐨勯」鐩垪琛紙鍒嗛〉锛夈€?
    
    Args:
        status (Optional[str]): 椤圭洰鐘舵€佽繃婊?
        ps (int): 鍒嗛〉澶у皬锛岃寖鍥?-100
        pi (int): 鍒嗛〉绱㈠紩锛屼粠1寮€濮?
        user: 宸茶璇佺殑鐢ㄦ埛瀵硅薄
        
    Returns:
        PaginatedHSAIProjectResponse: 鍒嗛〉鐨勯」鐩垪琛?
    """
    try:
        # 璁＄畻offset
        offset = (pi - 1) * ps
        
        if _is_super_admin(user):
            projects = HSAIProjects.get_projects(
                status=status,
                limit=ps,
                offset=offset,
            )
            total = HSAIProjects.get_projects_count_all(status=status)
        else:
            projects = HSAIProjects.get_projects_by_user_id(
                user.id,
                status=status,
                limit=ps,
                offset=offset
            )
            total = HSAIProjects.get_projects_count(
                user.id,
                status=status
            )
        
        responses = [HSAIProjectResponse(**project.model_dump()) for project in projects]
        
        # 璁＄畻鍒嗛〉鏁版嵁
        total_pages = (total + ps - 1) // ps  # 鍚戜笂鍙栨暣
        
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


@router.post("", response_model=HSAIProjectResponse, summary="鍒涘缓椤圭洰")
async def create_project(
    form_data: HSAIProjectForm,
    user=Depends(get_verified_user)
):
    """
    鍒涘缓鏂扮殑椤圭洰銆?
    
    鍒涘缓椤圭洰鍚庝細鑷姩鍒涘缓涓荤嚎浠诲姟銆?
    
    Args:
        form_data (HSAIProjectForm): 椤圭洰鍒涘缓琛ㄥ崟
        user: 宸茶璇佺殑鐢ㄦ埛瀵硅薄
        
    Returns:
        HSAIProjectResponse: 鍒涘缓鐨勯」鐩俊鎭?
    """
    try:
        target_user_id = (
            form_data.user_id if (_is_super_admin(user) and form_data.user_id) else user.id
        )
        project = HSAIProjects.insert_new_project(target_user_id, form_data)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create project"
            )
        
        # 鍒涘缓涓荤嚎浠诲姟
        main_tasks = []
        try:
            seed_templates = list(task_template_registry.iter_project_seed_templates())
        except Exception as registry_exc:  # pylint: disable=broad-except
            log.error("Failed to load project seed templates: %s", registry_exc)
            seed_templates = []

        for template in seed_templates:
            task_config = dict(template.config or {})
            task_config.setdefault("template_key", template.key)
            task_config.setdefault("seed_default_project", True)

            task_form = HSAITaskForm(
                title=template.title,
                description=template.description,
                task_type=template.task_type,
                task_category=template.task_category or "main",
                project_id=project.id,
                priority=template.priority,
                config=task_config,
                prompt_config=template.prompt_config,
            )

            task = HSAITasks.insert_new_task(target_user_id, task_form)
            if task:
                main_tasks.append(task)

        log.info(
            "Created %s main tasks for project %s via template source=%s",
            len(main_tasks),
            project.id,
            task_template_registry.source,
        )

        return HSAIProjectResponse(**project.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{project_id}", response_model=HSAIProjectResponse, summary="鑾峰彇椤圭洰璇︽儏")
async def get_project(
    project_id: str,
    user=Depends(get_verified_user)
):
    """鑾峰彇鍗曚釜椤圭洰璇︽儏"""
    try:
        project = HSAIProjects.get_project_by_id(project_id)
        is_admin = _is_super_admin(user)
        if not project or (project.user_id != user.id and not is_admin):
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


@router.put("/{project_id}", response_model=HSAIProjectResponse, summary="鏇存柊椤圭洰")
async def update_project(
    project_id: str,
    form_data: HSAIProjectUpdateForm,
    user=Depends(get_verified_user)
):
    """鏇存柊椤圭洰銆?
    
    鏇存柊鎸囧畾椤圭洰鐨勮缁嗕俊鎭€?
    
    Args:
        project_id (str): 椤圭洰ID
        form_data (HSAIProjectUpdateForm): 椤圭洰鏇存柊琛ㄥ崟
        user: 宸茶璇佺殑鐢ㄦ埛瀵硅薄
        
    Returns:
        HSAIProjectResponse: 鏇存柊鍚庣殑椤圭洰淇℃伅
        
    Raises:
        HTTPException: 404 - 椤圭洰鏈壘鍒?
        HTTPException: 400 - 椤圭洰鏇存柊澶辫触
        HTTPException: 500 - 鏈嶅姟鍣ㄥ唴閮ㄩ敊璇?
    """
    try:
        # 妤犲矁鐦夋い鍦窗閹碘偓閺堝娼?
        existing_project = HSAIProjects.get_project_by_id(project_id)
        if not existing_project or (
            existing_project.user_id != user.id and not _is_super_admin(user)
        ):
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


@router.delete("/{project_id}", response_model=bool, summary="鍒犻櫎椤圭洰")
async def delete_project(
    project_id: str,
    user=Depends(get_verified_user)
):
    """鍒犻櫎椤圭洰銆?
    
    鍒犻櫎鎸囧畾椤圭洰鍙婂叾鍏宠仈鐨勬墍鏈変换鍔°€?
    
    Args:
        project_id (str): 椤圭洰ID
        user: 宸茶璇佺殑鐢ㄦ埛瀵硅薄
        
    Returns:
        bool: 鍒犻櫎鎴愬姛杩斿洖True
        
    Raises:
        HTTPException: 404 - 椤圭洰鏈壘鍒?
        HTTPException: 400 - 椤圭洰鍒犻櫎澶辫触
        HTTPException: 500 - 鏈嶅姟鍣ㄥ唴閮ㄩ敊璇?
    """
    try:
        # 妤犲矁鐦夋い鍦窗閹碘偓閺堝娼?
        existing_project = HSAIProjects.get_project_by_id(project_id)
        if not existing_project or (
            existing_project.user_id != user.id and not _is_super_admin(user)
        ):
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


@router.get("/{project_id}/tasks", response_model=List[HSAITaskResponse], summary="鑾峰彇椤圭洰浠诲姟鍒楄〃")
async def get_project_tasks(
    project_id: str,
    user=Depends(get_verified_user)
):
    """鑾峰彇鎸囧畾椤圭洰涓嬬殑浠诲姟鍒楄〃銆?

    鏉冮檺杈圭晫锛?
    - 浠呴」鐩墍灞炵敤鎴峰彲璁块棶锛涚鐞嗗憳闇€鍏峰鐩稿簲鍚庨棬寮€鍏虫柟鍙唬鏌ャ€?

    杩囨护椤癸細
    - 鏃犻澶栨煡璇㈠弬鏁帮紙濡傞渶鍒嗛〉/绛涢€夎鍦ㄤ笂灞傚垪琛ㄦ帴鍙ｅ畬鎴愬悗鍦ㄥ鎴风杩囨护锛夈€?

    杩斿洖瀛楁锛圚SAITaskResponse 鍒楄〃锛夛細
    - id锛氫换鍔D
    - title锛氭爣棰?
    - status锛氱姸鎬侊紙濡?pending/running/paused/done锛?
    - type锛氫换鍔＄被鍨嬶紙main/recurring锛?
    - project_id锛氶」鐩甀D
    - created_at/updated_at锛氭椂闂存埑锛堢锛?
    - metadata锛氶檮鍔犱俊鎭?
    """
    try:
        # 校验项目归属
        project = HSAIProjects.get_project_by_id(project_id)
        is_admin = _is_super_admin(user)
        if not project or (project.user_id != user.id and not is_admin):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # 获取项目任务列表
        if is_admin:
            tasks = HSAITasks.get_tasks_by_project_id(project_id=project_id)
        else:
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


@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse, summary="椤圭洰浠诲姟鎽樿")
async def get_project_summary(
    project_id: str,
    user=Depends(get_verified_user),
):
    """杩斿洖椤圭洰浠诲姟鎽樿淇℃伅銆?

    鏉冮檺杈圭晫锛?
    - 浠呴」鐩墍灞炵敤鎴峰彲璁块棶锛涚鐞嗗憳闇€鍏峰鐩稿簲鍚庨棬寮€鍏虫柟鍙唬鏌ャ€?

    杩斿洖瀛楁锛圥rojectSummaryResponse锛夛細
    - project锛氶」鐩熀鏈俊鎭?
    - blueprint锛氳摑鍥剧増鏈?鍚屾鐘舵€?鏈€鍚庡悓姝ユ椂闂?
    - main_tasks锛氫富瑕佷换鍔″畬鎴愬害缁熻
    - recurring_tasks锛氬惊鐜换鍔＄粺璁℃眹鎬?
    - recurring_items锛氬惊鐜换鍔℃潯鐩垪琛?
    - recent_logs锛氳繎鏈熺姸鎬佹棩蹇?
    - blueprint_links锛氳摑鍥惧叧鑱斾俊鎭?
    """
    try:
        project = HSAIProjects.get_project_by_id(project_id)
        is_admin = _is_super_admin(user)
        if not project or (project.user_id != user.id and not is_admin):
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

        if is_admin:
            tasks: List[HSAITaskModel] = HSAITasks.get_tasks_by_project_id(
                project_id=project_id, limit=500
            )
        else:
            tasks = HSAITasks.get_tasks_by_user_id(
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
