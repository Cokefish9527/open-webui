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


# 椤圭洰妯℃澘瀹氫箟PROJECT_MAIN_TASK_TEMPLATES = {
    "company_info": {
        "title": "瀹屽杽浼佷笟淇℃伅",
        "description": "璇锋彁渚涙偍浼佷笟鐨勫熀鏈俊鎭紝鍖呮嫭浼佷笟鍚嶇О銆佽涓氥€佽妯＄瓑",
        "task_type": "workflow_execution",
        "task_category": "main",
        "workflow_type": "company_info",
        "priority": 10,
        "prompt_config": {
            "system_prompt": "鎮ㄦ槸涓€涓紒涓氫俊鎭敹闆嗗姪鎵嬶紝璇峰紩瀵肩敤鎴峰畬鍠勪紒涓氬熀鏈俊鎭?,
            "initial_message": "鎮ㄥソ锛佷负浜嗘洿濂藉湴涓烘偍鏈嶅姟锛屾垜浠渶瑕佹敹闆嗕竴浜涙偍浼佷笟鐨勫熀鏈俊鎭€?,
            "guidance_questions": [
                "璇峰憡璇夋垜鎮ㄧ殑浼佷笟鍚嶇О鏄粈涔堬紵",
                "鎮ㄧ殑浼佷笟灞炰簬鍝釜琛屼笟锛?,
                "浼佷笟澶ф鏈夊灏戝憳宸ワ紵",
                "浼佷笟鎴愮珛澶氶暱鏃堕棿浜嗭紵"
            ],
            "completion_criteria": "鐢ㄦ埛鎻愪緵浜嗗畬鏁寸殑浼佷笟鍩烘湰淇℃伅",
            "success_message": "鎰熻阿鎮ㄦ彁渚涚殑浼佷笟淇℃伅锛屾垜浠凡缁忚褰曞畬姣曘€?
        }
    },
    "project_info": {
        "title": "瀹屽杽椤圭洰淇℃伅",
        "description": "璇锋彁渚涢」鐩殑鍩烘湰淇℃伅锛屽寘鎷」鐩洰鏍囥€侀鏈熸垚鏋溿€佹椂闂磋鍒掔瓑",
        "task_type": "workflow_execution",
        "task_category": "main",
        "workflow_type": "project_info",
        "priority": 9,
        "prompt_config": {
            "system_prompt": "鎮ㄦ槸涓€涓」鐩俊鎭敹闆嗗姪鎵嬶紝璇峰紩瀵肩敤鎴峰畬鍠勯」鐩熀鏈俊鎭?,
            "initial_message": "鎺ヤ笅鏉ユ垜浠渶瑕佷簡瑙ｆ偍鐨勯」鐩熀鏈俊鎭紝浠ヤ究涓烘偍鎻愪緵鏇村ソ鐨勬湇鍔°€?,
            "guidance_questions": [
                "璇锋弿杩颁竴涓嬫偍鐨勯」鐩洰鏍囨槸浠€涔堬紵",
                "鎮ㄦ湡鏈涢€氳繃杩欎釜椤圭洰杈炬垚浠€涔堟垚鏋滐紵",
                "椤圭洰鐨勬椂闂磋鍒掓槸鎬庢牱鐨勶紵",
                "椤圭洰鐨勪富瑕佹寫鎴樻湁鍝簺锛?
            ],
            "completion_criteria": "鐢ㄦ埛鎻愪緵浜嗗畬鏁寸殑椤圭洰鍩烘湰淇℃伅",
            "success_message": "鎰熻阿鎮ㄦ彁渚涚殑椤圭洰淇℃伅锛屾垜浠凡缁忚褰曞畬姣曘€?
        }
    },
    "material_init": {
        "title": "绱犳潗搴撳垵濮嬪寲",
        "description": "鍒濆鍖栭」鐩礌鏉愬簱锛屼笂浼犵浉鍏崇礌鏉愭枃浠?,
        "task_type": "material_processing",
        "task_category": "main",
        "workflow_type": "material_init",
        "priority": 8,
        "prompt_config": {
            "system_prompt": "鎮ㄦ槸涓€涓礌鏉愮鐞嗗姪鎵嬶紝璇峰紩瀵肩敤鎴峰畬鎴愮礌鏉愬簱鍒濆鍖?,
            "initial_message": "鐜板湪璁╂垜浠垵濮嬪寲鎮ㄧ殑椤圭洰绱犳潗搴擄紝璇蜂笂浼犵浉鍏崇礌鏉愭枃浠躲€?,
            "guidance_questions": [
                "璇蜂笂浼犻」鐩浉鍏崇殑鍥剧墖绱犳潗",
                "璇蜂笂浼犻」鐩浉鍏崇殑瑙嗛绱犳潗",
                "璇蜂笂浼犻」鐩浉鍏崇殑鏂囨。绱犳潗"
            ],
            "completion_criteria": "鐢ㄦ埛瀹屾垚浜嗙礌鏉愬簱鐨勫垵濮嬪寲涓婁紶",
            "success_message": "绱犳潗搴撳垵濮嬪寲瀹屾垚锛屾偍鍙互闅忔椂娣诲姞鏇村绱犳潗銆?
        }
    }
}

@router.get("/", response_model=PaginatedHSAIProjectResponse, summary="鑾峰彇椤圭洰鍒楄〃")
async def get_projects(
    status: Optional[str] = Query(None, description="椤圭洰鐘舵€佽繃婊?),
    ps: int = Query(20, description="鍒嗛〉澶у皬", ge=1, le=100),
    pi: int = Query(1, description="鍒嗛〉绱㈠紩锛屼粠1寮€濮?, ge=1),
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
        
        projects = HSAIProjects.get_projects_by_user_id(
            user.id,
            status=status,
            limit=ps,
            offset=offset
        )
        
        # 鑾峰彇鎬绘暟
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


@router.post("/", response_model=HSAIProjectResponse, summary="鍒涘缓椤圭洰")
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
        project = HSAIProjects.insert_new_project(user.id, form_data)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create project"
            )
        
        # 鍒涘缓涓荤嚎浠诲姟
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


@router.get("/{project_id}", response_model=HSAIProjectResponse, summary="鑾峰彇椤圭洰璇︽儏")
async def get_project(
    project_id: str,
    user=Depends(get_verified_user)
):
    """鑾峰彇鍗曚釜椤圭洰璇︽儏"""
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


@router.put("/{project_id}", response_model=HSAIProjectResponse, summary="鏇存柊椤圭洰")
async def update_project(
    project_id: str,
    form_data: HSAIProjectUpdateForm,
    user=Depends(get_verified_user)
):
    """鏇存柊椤圭洰"""
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


@router.delete("/{project_id}", response_model=bool, summary="鍒犻櫎椤圭洰")
async def delete_project(
    project_id: str,
    user=Depends(get_verified_user)
):
    """鍒犻櫎椤圭洰"""
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


@router.get("/{project_id}/tasks", response_model=List[HSAITaskResponse], summary="鑾峰彇椤圭洰浠诲姟鍒楄〃")
async def get_project_tasks(
    project_id: str,
    user=Depends(get_verified_user)
):
    """鑾峰彇椤圭洰鍏宠仈鐨勪换鍔″垪琛?""
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
                        "metadata": link.metadata or {},
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
