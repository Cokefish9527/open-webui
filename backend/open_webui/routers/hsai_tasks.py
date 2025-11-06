import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel, Field

from open_webui.models.hsai_tasks import (
    HSAITask,
    HSAIWorkflow,
    HSAICard,
    HSAITasks,
    HSAICards,
    HSAITaskForm,
    HSAIWorkflowForm,
    HSAICardForm,
    HSAITaskUpdateForm,
    HSAITaskResponse,
    HSAICardResponse,
    HSAITaskStatus,
    HSAITaskType,
    HSAICardType,
    HSAIRecurringState,
    HSAITaskStateLogs,
    HSAITaskModel,
    # 添加分页相关的导入
    PaginationData,
    PaginatedHSAITaskResponse,
    PaginatedHSAICardResponse
)
from open_webui.models.hsai_companies import Companies
from open_webui.models.hsai_projects import HSAIProjects

from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.socket.main import get_event_emitter

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/tasks", tags=["HSAI 任务管理"])

############################
# 任务统计
############################

class TaskStatsResponse(BaseModel):
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    failed_tasks: int
    tasks_by_type: dict
    avg_completion_time: Optional[float] = None


class RecurringActivateForm(BaseModel):
    next_run_at: Optional[int] = None
    message: Optional[str] = None


class RecurringPauseForm(BaseModel):
    reason: Optional[str] = None
    message: Optional[str] = None


class RecurringResumeForm(BaseModel):
    message: Optional[str] = None


class RecurringHandoverForm(BaseModel):
    controller: str = Field(description="外部控制方标识")
    note: Optional[str] = None


class RecurringSyncForm(BaseModel):
    state: str = Field(description="循环任务状态")
    next_run_at: Optional[int] = None
    last_run_at: Optional[int] = None
    message: Optional[str] = None


class SimulateSchedulerForm(BaseModel):
    schedule_date: str = Field(description="YYYY-MM-DD")

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


def _get_task_for_user(task_id: str, user_id: str) -> HSAITaskModel:
    task = HSAITasks.get_task_by_id(task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


def _is_recurring_task(task: HSAITaskModel) -> bool:
    category = (task.task_category or "").lower()
    return task.is_recurring or category.startswith("blueprint_daily")


def _append_state_log(
    task_id: str,
    from_state: Optional[str],
    to_state: str,
    user,
    source: str,
    message: Optional[str],
    snapshot: Optional[Dict[str, Any]] = None,
):
    operator_id = getattr(user, "id", None)
    operator_name = getattr(user, "name", None) or getattr(user, "email", None)
    try:
        return HSAITaskStateLogs.append_log(
            task_id=task_id,
            from_state=from_state,
            to_state=to_state,
            operator_id=operator_id,
            operator_name=operator_name,
            source=source,
            message=message,
            snapshot_json=snapshot,
        )
    except Exception as exc:
        log.warning("Failed to append recurring task log for %s: %s", task_id, exc)
        return None


def _emit_task_event(task: HSAITaskModel, event: str, message: Optional[str], context: Optional[Dict[str, Any]] = None):
    emitter = get_event_emitter()
    if not emitter:
        return
    payload = {
        "task_id": task.id,
        "status": task.status,
        "recurring_state": task.recurring_state,
        "message": message,
        "context": context or {},
    }
    try:
        emitter.emit(event, payload)
    except Exception as exc:
        log.warning("Failed to emit task event %s for %s: %s", event, task.id, exc)


@router.get("/statistics", response_model=TaskStatsResponse, summary="获取任务统计")
async def get_task_stats(user=Depends(get_verified_user)):
    """
    获取任务统计信息。
    
    提供用户任务的详细统计数据，用于仪表板展示和性能分析。
    
    Args:
        user: 已认证的用户对象
        
    Returns:
        TaskStatsResponse: 统计信息
        - total_tasks: 任务总数量
        - pending_tasks: 待执行任务数量
        - in_progress_tasks: 执行中任务数量
        - completed_tasks: 已完成任务数量
        - failed_tasks: 失败任务数量
        - tasks_by_type: 按类型分组的任务数量
          - video_creation: 视频创作任务数量
          - content_analysis: 内容分析任务数量
          - image_generation: 图像生成任务数量
          - text_processing: 文本处理任务数量
        - avg_completion_time: 平均完成时间（秒）
        
    Raises:
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 统计数据仅包含当前用户的任务
        - 平均完成时间基于已完成任务计算
        - 用于性能监控和用户行为分析
    """
    try:
        log.info(f"Getting task stats for user_id: {user.id}")
        tasks = HSAITasks.get_tasks_by_user_id(user.id)
        log.info(f"Retrieved {len(tasks)} tasks for user_id: {user.id}")
        
        # 统计各状态任务数量
        stats = {
            "total_tasks": len(tasks),
            "pending_tasks": 0,
            "in_progress_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "tasks_by_type": {}
        }
        
        completion_times = []
        
        for task in tasks:
            # 按状态统计
            if task.status == HSAITaskStatus.PENDING:
                stats["pending_tasks"] += 1
            elif task.status == HSAITaskStatus.IN_PROGRESS:
                stats["in_progress_tasks"] += 1
            elif task.status == HSAITaskStatus.COMPLETED:
                stats["completed_tasks"] += 1
                # 计算完成时间
                if task.started_at and task.completed_at:
                    completion_times.append(task.completed_at - task.started_at)
            elif task.status == HSAITaskStatus.FAILED:
                stats["failed_tasks"] += 1
            
            # 按类型统计
            if task.task_type not in stats["tasks_by_type"]:
                stats["tasks_by_type"][task.task_type] = 0
            stats["tasks_by_type"][task.task_type] += 1
        
        # 计算平均完成时间
        if completion_times:
            stats["avg_completion_time"] = sum(completion_times) / len(completion_times)
        
        log.info(f"Task stats for user_id {user.id}: {stats}")
        return TaskStatsResponse(**stats)
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        log.exception(f"Error getting task stats for user {user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/by-company/{company_name}", response_model=PaginatedHSAITaskResponse, summary="通过企业名称获取任务列表")
async def get_tasks_by_company_name(
    company_name: str,
    status: Optional[str] = Query(None, description="任务状态过滤：pending(待执行)、in_progress(执行中)、completed(已完成)、failed(执行失败)、cancelled(已取消)"),
    task_type: Optional[str] = Query(None, description="任务类型过滤：video_creation(视频创作)、content_analysis(内容分析)、image_generation(图像生成)、text_processing(文本处理)"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    通过企业名称获取任务列表（分页）。
    
    支持按状态和类型进行过滤，返回企业关联项目下的所有任务。
    
    Args:
        company_name (str): 企业名称
        status (Optional[str]): 任务状态过滤
        - "pending": 待执行
        - "in_progress": 执行中
        - "completed": 已完成
        - "failed": 执行失败
        - "cancelled": 已取消
        task_type (Optional[str]): 任务类型过滤
        - "video_creation": 视频创作
        - "content_analysis": 内容分析
        - "image_generation": 图像生成
        - "text_processing": 文本处理
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAITaskResponse: 分页的任务列表
        - data: 任务列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
        
    Raises:
        HTTPException: 404 - 企业未找到
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 先根据企业名称查找企业
        company = Companies.get_company_by_name(company_name)
        if not company:
            raise HTTPException(
                status_code=404,
                detail="Company not found"
            )
        
        # 检查用户是否有权限访问该企业
        if company.owner_user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        # 计算offset
        offset = (pi - 1) * ps
        
        # 获取企业关联的所有项目下的任务
        tasks = HSAITasks.get_tasks_by_company_id(
            company.id,
            status=status,
            task_type=task_type,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        # 先获取企业关联的所有项目
        projects = HSAIProjects.get_projects_by_company_id(company.id)
        project_ids = [project.id for project in projects]
        total = 0
        if project_ids:
            total = HSAITasks.get_tasks_count(
                user.id,  # 这里使用user_id作为过滤条件，但实际会通过project_ids过滤
                status=status,
                task_type=task_type,
                project_id=project_ids[0] if len(project_ids) == 1 else None
            )
            # 如果有多个项目，需要分别统计每个项目的任务数
            if len(project_ids) > 1:
                total = 0
                for project_id in project_ids:
                    total += HSAITasks.get_tasks_count(
                        user.id,
                        status=status,
                        task_type=task_type,
                        project_id=project_id
                    )
        
        responses = []
        for task in tasks:
            # 计算预估耗时（简化版本）
            estimated_duration = None
            if task.task_type == HSAITaskType.VIDEO_CREATION:
                estimated_duration = 300  # 5分钟
            elif task.task_type == HSAITaskType.CONTENT_ANALYSIS:
                estimated_duration = 60   # 1分钟
            
            response = HSAITaskResponse(
                **task.model_dump(),
                estimated_duration=estimated_duration
            )
            responses.append(response)
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAITaskResponse(
            data=responses,
            pagination=pagination
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting tasks by company name: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )
    """
    获取任务统计信息。
    
    提供用户任务的详细统计数据，用于仪表板展示和性能分析。
    
    Args:
        user: 已认证的用户对象
        
    Returns:
        TaskStatsResponse: 统计信息
        - total_tasks: 任务总数量
        - pending_tasks: 待执行任务数量
        - in_progress_tasks: 执行中任务数量
        - completed_tasks: 已完成任务数量
        - failed_tasks: 失败任务数量
        - tasks_by_type: 按类型分组的任务数量
          - video_creation: 视频创作任务数量
          - content_analysis: 内容分析任务数量
          - image_generation: 图像生成任务数量
          - text_processing: 文本处理任务数量
        - avg_completion_time: 平均完成时间（秒）
        
    Raises:
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 统计数据仅包含当前用户的任务
        - 平均完成时间基于已完成任务计算
        - 用于性能监控和用户行为分析
    """
    try:
        log.info(f"Getting task stats for user_id: {user.id}")
        tasks = HSAITasks.get_tasks_by_user_id(user.id)
        log.info(f"Retrieved {len(tasks)} tasks for user_id: {user.id}")
        
        # 统计各状态任务数量
        stats = {
            "total_tasks": len(tasks),
            "pending_tasks": 0,
            "in_progress_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "tasks_by_type": {}
        }
        
        completion_times = []
        
        for task in tasks:
            # 按状态统计
            if task.status == HSAITaskStatus.PENDING:
                stats["pending_tasks"] += 1
            elif task.status == HSAITaskStatus.IN_PROGRESS:
                stats["in_progress_tasks"] += 1
            elif task.status == HSAITaskStatus.COMPLETED:
                stats["completed_tasks"] += 1
                # 计算完成时间
                if task.started_at and task.completed_at:
                    completion_times.append(task.completed_at - task.started_at)
            elif task.status == HSAITaskStatus.FAILED:
                stats["failed_tasks"] += 1
            
            # 按类型统计
            if task.task_type not in stats["tasks_by_type"]:
                stats["tasks_by_type"][task.task_type] = 0
            stats["tasks_by_type"][task.task_type] += 1
        
        # 计算平均完成时间
        if completion_times:
            stats["avg_completion_time"] = sum(completion_times) / len(completion_times)
        
        log.info(f"Task stats for user_id {user.id}: {stats}")
        return TaskStatsResponse(**stats)
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        log.exception(f"Error getting task stats for user {user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 任务管理
############################

@router.get("/", response_model=PaginatedHSAITaskResponse, summary="获取任务列表")
async def get_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤：pending(待执行)、in_progress(执行中)、completed(已完成)、failed(执行失败)、cancelled(已取消)"),
    task_type: Optional[str] = Query(None, description="任务类型过滤：video_creation(视频创作)、content_analysis(内容分析)、image_generation(图像生成)、text_processing(文本处理)"),
    assignee_id: Optional[str] = Query(None, description="指派人ID过滤"),
    chat_id: Optional[str] = Query(None, description="聊天会话ID，用于过滤特定会话的任务"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取用户的任务列表（分页）。
    
    支持按状态、类型、指派人和聊天会话进行过滤，返回任务的详细信息和预估执行时间。
    
    Args:
        status (Optional[str]): 任务状态过滤
        - "pending": 待执行
        - "in_progress": 执行中
        - "completed": 已完成
        - "failed": 执行失败
        - "cancelled": 已取消
        task_type (Optional[str]): 任务类型过滤
        - "video_creation": 视频创作
        - "content_analysis": 内容分析
        - "image_generation": 图像生成
        - "text_processing": 文本处理
        assignee_id (Optional[str]): 指派人ID过滤
        chat_id (Optional[str]): 聊天会话ID过滤
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAITaskResponse: 分页的任务列表
        - data: 任务列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        tasks = HSAITasks.get_tasks_by_user_id(
            user.id,
            status=status,
            task_type=task_type,
            assignee_id=assignee_id,
            chat_id=chat_id,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = HSAITasks.get_tasks_count(
            user.id,
            status=status,
            task_type=task_type,
            assignee_id=assignee_id,
            chat_id=chat_id
        )
        
        responses = []
        for task in tasks:
            # 计算预估耗时（简化版本）
            estimated_duration = None
            if task.task_type == HSAITaskType.VIDEO_CREATION:
                estimated_duration = 300  # 5分钟
            elif task.task_type == HSAITaskType.CONTENT_ANALYSIS:
                estimated_duration = 60   # 1分钟
            
            response = HSAITaskResponse(
                **task.model_dump(),
                estimated_duration=estimated_duration
            )
            responses.append(response)
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAITaskResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting tasks: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/", response_model=HSAITaskResponse, summary="创建任务")
async def create_task(
    form_data: HSAITaskForm,
    user=Depends(get_verified_user)
):
    """
    创建新的AI任务。
    
    创建任务后会自动生成对应的聊天卡片，并通过WebSocket通知前端。
    
    Args:
        form_data (HSAITaskForm): 任务创建表单
        - title: 任务标题（必填）
        - description: 任务描述（可选）
        - task_type: 任务类型（必填）
        - chat_id: 关联的聊天会话ID（可选）
        - parameters: 任务参数（JSON格式）
        - priority: 任务优先级（1-10，默认5）
        user: 已认证的用户对象
        
    Returns:
        HSAITaskResponse: 创建的任务信息
        
    Raises:
        HTTPException: 400 - 创建失败
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 如果指定了chat_id，会自动创建任务卡片
        - 创建成功后会通过WebSocket发送通知
        - 任务初始状态为"pending"
    """
    try:
        task = HSAITasks.insert_new_task(user.id, form_data)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create task"
            )
        
        # 创建对应的卡片
        if form_data.chat_id:
            card_form = HSAICardForm(
                title=task.title,
                description=task.description,
                card_type=HSAICardType.TASK_CARD,
                chat_id=form_data.chat_id,
                task_id=task.id,
                content={
                    "task_type": task.task_type,
                    "status": task.status,
                    "progress": task.progress
                },
                actions={
                    "start": {"label": "开始执行", "enabled": True},
                    "pause": {"label": "暂停", "enabled": False},
                    "cancel": {"label": "取消", "enabled": True}
                }
            )
            
            card = HSAICards.insert_new_card(user.id, card_form)
            
            # 移除了WebSocket通知，改为HTTP轮询方式
        
        return HSAITaskResponse(**task.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating task: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{task_id}", response_model=HSAITaskResponse, summary="获取任务详情")
async def get_task(
    task_id: str,
    user=Depends(get_verified_user)
):
    """获取单个任务详情"""
    try:
        task = HSAITasks.get_task_by_id(task_id)
        if not task or task.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return HSAITaskResponse(**task.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting task: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/{task_id}", response_model=HSAITaskResponse, summary="更新任务")
async def update_task(
    task_id: str,
    form_data: HSAITaskUpdateForm,
    user=Depends(get_verified_user)
):
    """更新任务"""
    try:
        # 验证任务所有权
        existing_task = HSAITasks.get_task_by_id(task_id)
        if not existing_task or existing_task.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        task = HSAITasks.update_task_by_id(task_id, form_data)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update task"
            )
        
        # 更新相关卡片
        if existing_task.chat_id:
            cards = HSAICards.get_cards_by_chat_id(existing_task.chat_id)
            for card in cards:
                if card.task_id == task_id:
                    updated_content = {
                        **card.content,
                        "status": task.status,
                        "progress": task.progress
                    }
                    HSAICards.update_card_by_id(card.id, {"content": updated_content})
        
        return HSAITaskResponse(**task.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating task: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )




@router.post("/{task_id}/recurring/activate", response_model=HSAITaskResponse, summary="启动循环任务")
async def activate_recurring_task(
    task_id: str,
    form: RecurringActivateForm,
    user=Depends(get_verified_user),
):
    """
    启动循环任务。
    
    将处于空闲或暂停状态的循环任务激活，使其进入活跃状态并准备执行。
    
    Args:
        task_id (str): 循环任务ID
        form (RecurringActivateForm): 激活表单
            - next_run_at (Optional[int]): 下次运行时间戳（可选）
            - message (Optional[str]): 操作消息（可选）
        user: 已认证的用户对象
        
    Returns:
        HSAITaskResponse: 更新后的任务信息
        
    Raises:
        HTTPException: 400 - 任务不是循环任务或状态不允许激活
        HTTPException: 500 - 激活失败
        
    Note:
        - 仅空闲(IDLE)或暂停(PAUSED)状态的循环任务可以被激活
        - 激活后任务状态变为活跃(ACTIVE)
        - 会记录状态变更日志
    """
    task = _get_task_for_user(task_id, user.id)
    if not _is_recurring_task(task):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not recurring")

    if task.project_id and not HSAITasks.all_main_tasks_completed(task.project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Main tasks must be completed before activating recurring tasks",
        )

    previous_state = (task.recurring_state or HSAIRecurringState.IDLE.value).lower()
    if previous_state not in {"", HSAIRecurringState.IDLE.value, HSAIRecurringState.PAUSED.value}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task cannot be activated")

    update_form = HSAITaskUpdateForm(
        is_recurring=True,
        recurring_state=HSAIRecurringState.ACTIVE.value,
        next_run_at=form.next_run_at,
    )
    updated = HSAITasks.update_task_by_id(task_id, update_form)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT())

    log_entry = _append_state_log(
        task_id=task_id,
        from_state=task.recurring_state,
        to_state=HSAIRecurringState.ACTIVE.value,
        user=user,
        source="admin_api",
        message=form.message or "激活循环任务",
        snapshot=updated.model_dump(),
    )
    context = {"log_id": log_entry.id} if log_entry else None
    _emit_task_event(updated, "task_status_updated", form.message, context)
    return HSAITaskResponse(**updated.model_dump())


@router.post("/{task_id}/recurring/pause", response_model=HSAITaskResponse, summary="暂停循环任务")
async def pause_recurring_task(
    task_id: str,
    form: RecurringPauseForm,
    user=Depends(get_verified_user),
):
    """
    暂停循环任务。
    
    将活跃状态的循环任务暂停，使其暂时停止执行。
    
    Args:
        task_id (str): 循环任务ID
        form (RecurringPauseForm): 暂停表单
            - reason (Optional[str]): 暂停原因（可选）
            - message (Optional[str]): 操作消息（可选）
        user: 已认证的用户对象
        
    Returns:
        HSAITaskResponse: 更新后的任务信息
        
    Raises:
        HTTPException: 400 - 任务不是循环任务或未处于活跃状态
        HTTPException: 500 - 暂停失败
        
    Note:
        - 仅活跃(ACTIVE)状态的循环任务可以被暂停
        - 暂停后任务状态变为暂停(PAUSED)
        - 会记录状态变更日志
    """
    task = _get_task_for_user(task_id, user.id)
    if not _is_recurring_task(task):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not recurring")
    if (task.recurring_state or "").lower() != HSAIRecurringState.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not active")

    update_form = HSAITaskUpdateForm(recurring_state=HSAIRecurringState.PAUSED.value)
    updated = HSAITasks.update_task_by_id(task_id, update_form)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT())

    log_entry = _append_state_log(
        task_id=task_id,
        from_state=task.recurring_state,
        to_state=HSAIRecurringState.PAUSED.value,
        user=user,
        source="admin_api",
        message=form.message or form.reason or "暂停循环任务",
        snapshot=updated.model_dump(),
    )
    context = {"log_id": log_entry.id} if log_entry else None
    _emit_task_event(updated, "task_status_updated", form.message, context)
    return HSAITaskResponse(**updated.model_dump())


@router.post("/{task_id}/recurring/resume", response_model=HSAITaskResponse, summary="恢复循环任务")
async def resume_recurring_task(
    task_id: str,
    form: RecurringResumeForm,
    user=Depends(get_verified_user),
):
    """
    恢复循环任务。
    
    将暂停或外部控制状态的循环任务恢复为活跃状态，继续执行。
    
    Args:
        task_id (str): 循环任务ID
        form (RecurringResumeForm): 恢复表单
            - message (Optional[str]): 操作消息（可选）
        user: 已认证的用户对象
        
    Returns:
        HSAITaskResponse: 更新后的任务信息
        
    Raises:
        HTTPException: 400 - 任务不是循环任务或状态不允许恢复
        HTTPException: 500 - 恢复失败
        
    Note:
        - 仅暂停(PAUSED)或外部控制(EXTERNAL_CONTROLLED)状态的循环任务可以被恢复
        - 恢复后任务状态变为活跃(ACTIVE)
        - 会记录状态变更日志
    """
    task = _get_task_for_user(task_id, user.id)
    if not _is_recurring_task(task):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not recurring")
    if (task.recurring_state or "").lower() not in {HSAIRecurringState.PAUSED.value, HSAIRecurringState.EXTERNAL_CONTROLLED.value}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task cannot be resumed")

    update_form = HSAITaskUpdateForm(recurring_state=HSAIRecurringState.ACTIVE.value)
    updated = HSAITasks.update_task_by_id(task_id, update_form)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT())

    log_entry = _append_state_log(
        task_id=task_id,
        from_state=task.recurring_state,
        to_state=HSAIRecurringState.ACTIVE.value,
        user=user,
        source="admin_api",
        message=form.message or "恢复循环任务",
        snapshot=updated.model_dump(),
    )
    context = {"log_id": log_entry.id} if log_entry else None
    _emit_task_event(updated, "task_status_updated", form.message, context)
    return HSAITaskResponse(**updated.model_dump())


@router.post("/{task_id}/recurring/handover", response_model=HSAITaskResponse, summary="循环任务交接外部控制")
async def handover_recurring_task(
    task_id: str,
    form: RecurringHandoverForm,
    user=Depends(get_verified_user),
):
    """
    循环任务交接外部控制。
    
    将循环任务的控制权交接给外部系统，任务将由外部系统控制执行。
    
    Args:
        task_id (str): 循环任务ID
        form (RecurringHandoverForm): 交接表单
            - controller (str): 外部控制方标识
            - note (Optional[str]): 交接备注（可选）
        user: 已认证的用户对象
        
    Returns:
        HSAITaskResponse: 更新后的任务信息
        
    Raises:
        HTTPException: 400 - 任务不是循环任务
        HTTPException: 500 - 交接失败
        
    Note:
        - 交接后任务状态变为外部控制(EXTERNAL_CONTROLLED)
        - 会记录状态变更日志
        - 外部系统可以通过API控制任务的执行
    """
    task = _get_task_for_user(task_id, user.id)
    if not _is_recurring_task(task):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not recurring")

    update_form = HSAITaskUpdateForm(
        recurring_state=HSAIRecurringState.EXTERNAL_CONTROLLED.value,
        external_controller=form.controller,
    )
    updated = HSAITasks.update_task_by_id(task_id, update_form)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT())

    log_entry = _append_state_log(
        task_id=task_id,
        from_state=task.recurring_state,
        to_state=HSAIRecurringState.EXTERNAL_CONTROLLED.value,
        user=user,
        source="admin_api",
        message=form.note or "循环任务交接外部控制",
        snapshot=updated.model_dump(),
    )
    context = {"log_id": log_entry.id} if log_entry else None
    _emit_task_event(updated, "task_status_updated", form.note, context)
    return HSAITaskResponse(**updated.model_dump())


@router.post("/{task_id}/recurring/sync", response_model=HSAITaskResponse, summary="同步循环任务状态")
async def sync_recurring_task(
    task_id: str,
    form: RecurringSyncForm,
    user=Depends(get_verified_user),
):
    """
    同步循环任务状态。
    
    同步循环任务的状态信息，包括状态、下次运行时间和上次运行时间。
    
    Args:
        task_id (str): 循环任务ID
        form (RecurringSyncForm): 同步表单
            - state (str): 目标状态
            - next_run_at (Optional[int]): 下次运行时间戳（可选）
            - last_run_at (Optional[int]): 上次运行时间戳（可选）
            - message (Optional[str]): 操作消息（可选）
        user: 已认证的用户对象
        
    Returns:
        HSAITaskResponse: 更新后的任务信息
        
    Raises:
        HTTPException: 400 - 任务不是循环任务或状态不支持
        HTTPException: 500 - 同步失败
        
    Note:
        - 支持的状态包括：空闲(IDLE)、活跃(ACTIVE)、暂停(PAUSED)、外部控制(EXTERNAL_CONTROLLED)
        - 会记录状态变更日志
        - 通常由外部系统调用以同步任务状态
    """
    task = _get_task_for_user(task_id, user.id)
    if not _is_recurring_task(task):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not recurring")

    target_state = form.state.lower()
    if target_state not in {
        HSAIRecurringState.IDLE.value,
        HSAIRecurringState.ACTIVE.value,
        HSAIRecurringState.PAUSED.value,
        HSAIRecurringState.EXTERNAL_CONTROLLED.value,
    }:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported recurring state")

    update_form = HSAITaskUpdateForm(
        recurring_state=target_state,
        next_run_at=form.next_run_at,
        last_run_at=form.last_run_at,
        is_recurring=True,
    )
    updated = HSAITasks.update_task_by_id(task_id, update_form)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT())

    log_entry = _append_state_log(
        task_id=task_id,
        from_state=task.recurring_state,
        to_state=target_state,
        user=user,
        source="admin_api",
        message=form.message or "循环任务状态同步",
        snapshot=updated.model_dump(),
    )
    context = {"log_id": log_entry.id} if log_entry else None
    _emit_task_event(updated, "task_status_updated", form.message, context)
    return HSAITaskResponse(**updated.model_dump())


@router.get("/{task_id}/recurring/logs", response_model=List[RecurringLogEntry], summary="循环任务状态日志")
async def get_recurring_logs(
    task_id: str,
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_verified_user),
):
    """
    获取循环任务状态日志。
    
    返回循环任务的状态变更历史记录。
    
    Args:
        task_id (str): 循环任务ID
        limit (int): 返回记录数量限制，范围1-100，默认20
        user: 已认证的用户对象
        
    Returns:
        List[RecurringLogEntry]: 状态日志列表
        - id (str): 日志ID
        - task_id (str): 任务ID
        - from_state (Optional[str]): 变更前状态
        - to_state (str): 变更后状态
        - operator_id (Optional[str]): 操作者ID
        - operator_name (Optional[str]): 操作者名称
        - source (Optional[str]): 操作来源
        - message (Optional[str]): 操作消息
        - created_at (int): 创建时间戳
        
    Raises:
        HTTPException: 400 - 任务不是循环任务
        
    Note:
        - 按时间倒序返回最新的状态变更记录
        - 用于审计和调试任务状态变更历史
    """
    task = _get_task_for_user(task_id, user.id)
    if not _is_recurring_task(task):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not recurring")

    logs = HSAITaskStateLogs.list_logs(task_id, limit=limit)
    return [
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
        for entry in logs
    ]
@router.post("/{task_id}/start", response_model=HSAITaskResponse, summary="启动任务")
async def start_task(
    task_id: str,
    user=Depends(get_verified_user)
):
    """
    启动任务执行。
    
    将待执行状态的任务启动，开始实际的AI处理流程。
    
    Args:
        task_id (str): 要启动的任务ID
        user: 已认证的用户对象
        
    Returns:
        HSAITaskResponse: 更新后的任务信息
        
    Raises:
        HTTPException: 404 - 任务不存在或无权限访问
        HTTPException: 400 - 任务状态不允许启动
        HTTPException: 500 - 启动失败
        
    Note:
        - 只有"pending"状态的任务可以启动
        - 启动后任务状态变为"in_progress"
        - 客户端需要主动轮询获取任务状态
    """
    try:
        # 验证任务所有权和状态
        existing_task = HSAITasks.get_task_by_id(task_id)
        if not existing_task or existing_task.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if existing_task.status != HSAITaskStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is not in pending status"
            )
        
        # 更新任务状态
        update_form = HSAITaskUpdateForm(
            status=HSAITaskStatus.IN_PROGRESS,
            progress=0
        )
        
        task = HSAITasks.update_task_by_id(task_id, update_form)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start task"
            )

        log_entry = _append_state_log(
            task_id=task_id,
            from_state=existing_task.status,
            to_state=HSAITaskStatus.IN_PROGRESS.value,
            user=user,
            source="admin_api",
            message="启动任务",
            snapshot=task.model_dump(),
        )
        context = {"log_id": log_entry.id} if log_entry else None
        _emit_task_event(task, "task_status_updated", "启动任务", context)
        
        # 在这里可以添加异步任务执行逻辑
        # 例如：通过Celery或其他队列系统执行实际的AI处理
        
        return HSAITaskResponse(**task.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error starting task: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )




@router.post("/{task_id}/simulate", response_model=HSAITaskResponse, summary="模拟循环任务调度")
async def simulate_recurring_schedule(
    task_id: str,
    form: SimulateSchedulerForm,
    user=Depends(get_verified_user),
):
    """
    模拟循环任务调度。
    
    为指定日期创建模拟的循环任务子任务，用于测试和预览任务调度效果。
    
    Args:
        task_id (str): 循环任务ID
        form (SimulateSchedulerForm): 调度表单
            - schedule_date (str): 调度日期（格式：YYYY-MM-DD）
        user: 已认证的用户对象
        
    Returns:
        HSAITaskResponse: 创建的模拟子任务信息
        
    Raises:
        HTTPException: 400 - 任务不是循环任务或日期格式无效或子任务已存在
        HTTPException: 500 - 创建模拟任务失败
        
    Note:
        - 用于预览和测试循环任务的调度效果
        - 模拟任务不会实际执行
        - 会记录状态变更日志
        - 模拟任务优先级会比原任务低5级
    """
    task = _get_task_for_user(task_id, user.id)
    if not _is_recurring_task(task):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not recurring")

    try:
        target_date = datetime.strptime(form.schedule_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid schedule_date")

    scheduled_key = target_date.isoformat()
    existing_subtasks = HSAITasks.get_tasks_by_user_id(user.id, project_id=task.project_id, limit=200)
    for sub in existing_subtasks:
        if sub.parent_task_id == task.id and (sub.config or {}).get("scheduled_for") == scheduled_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subtask already exists for date")

    subtask_form = HSAITaskForm(
        title=f"{scheduled_key} 循环发布任务",
        description="模拟调度生成的循环发布任务",
        task_type=task.task_type or HSAITaskType.PLATFORM_PUBLISHING.value,
        task_category="blueprint_daily_simulation",
        project_id=task.project_id,
        parent_task_id=task.id,
        config={
            "scheduled_for": scheduled_key,
            "generated_by": "simulate",
        },
        priority=max(0, (task.priority or 0) - 5),
    )
    subtask = HSAITasks.insert_new_task(user.id, subtask_form)
    if not subtask:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT())

    log_entry = _append_state_log(
        task_id=task_id,
        from_state=task.recurring_state,
        to_state=task.recurring_state or HSAIRecurringState.ACTIVE.value,
        user=user,
        source="admin_api",
        message=f"Simulated subtask scheduled for {scheduled_key}",
        snapshot=subtask.model_dump(),
    )
    context = {"log_id": log_entry.id} if log_entry else None
    _emit_task_event(
        task,
        "task_progress",
        f"Simulated subtask scheduled for {scheduled_key}",
        context,
    )
    return HSAITaskResponse(**subtask.model_dump())

@router.post("/{task_id}/cancel", response_model=HSAITaskResponse, summary="取消任务")
async def cancel_task(
    task_id: str,
    user=Depends(get_verified_user)
):
    """
    取消任务执行。
    
    停止正在执行或待执行的任务，释放相关资源。
    
    Args:
        task_id (str): 要取消的任务ID
        user: 已认证的用户对象
        
    Returns:
        HSAITaskResponse: 更新后的任务信息
        
    Raises:
        HTTPException: 404 - 任务不存在或无权限访问
        HTTPException: 400 - 任务已完成或已取消，无法取消
        HTTPException: 500 - 取消失败
        
    Note:
        - 已完成或已取消的任务无法再次取消
        - 取消后任务状态变为"cancelled"
        - 客户端需要主动轮询获取任务状态
    """
    try:
        # 验证任务所有权
        existing_task = HSAITasks.get_task_by_id(task_id)
        if not existing_task or existing_task.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if existing_task.status in [HSAITaskStatus.COMPLETED, HSAITaskStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel completed or already cancelled task"
            )
        
        # 更新任务状态
        update_form = HSAITaskUpdateForm(
            status=HSAITaskStatus.CANCELLED
        )
        
        task = HSAITasks.update_task_by_id(task_id, update_form)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel task"
            )

        log_entry = _append_state_log(
            task_id=task_id,
            from_state=existing_task.status,
            to_state=HSAITaskStatus.CANCELLED.value,
            user=user,
            source="admin_api",
            message="取消任务",
            snapshot=task.model_dump(),
        )
        context = {"log_id": log_entry.id} if log_entry else None
        _emit_task_event(task, "task_status_updated", "取消任务", context)
        
        return HSAITaskResponse(**task.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error cancelling task: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/{task_id}/progress", response_model=bool, summary="更新任务进度")
async def update_task_progress(
    task_id: str,
    progress: int,
    user=Depends(get_verified_user)
):
    """
    更新任务执行进度。
    
    通常由后台任务处理进程调用，实时更新任务的执行进度。
    
    Args:
        task_id (str): 任务ID
        progress (int): 进度百分比（0-100）
        user: 已认证的用户对象
        
    Returns:
        bool: 更新是否成功
        
    Raises:
        HTTPException: 404 - 任务不存在或无权限访问
        HTTPException: 500 - 更新失败
        
    Note:
        - 进度值应在0-100之间
        - 客户端需要主动轮询获取任务进度
        - 通常由异步任务处理器调用
    """
    try:
        # 验证任务所有权
        existing_task = HSAITasks.get_task_by_id(task_id)
        if not existing_task or existing_task.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        result = HSAITasks.update_task_progress(task_id, progress)

        if result:
            updated_task = HSAITasks.get_task_by_id(task_id)
            if updated_task:
                log_entry = _append_state_log(
                    task_id=task_id,
                    from_state=existing_task.status,
                    to_state=updated_task.status,
                    user=user,
                    source="admin_api",
                    message=f"更新进度到 {progress}",
                    snapshot=updated_task.model_dump(),
                )
                context = {"log_id": log_entry.id} if log_entry else None
                _emit_task_event(
                    updated_task,
                    "task_progress",
                    f"进度更新为 {progress}",
                    context,
                )

        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating task progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/{task_id}/assign", response_model=HSAITaskResponse, summary="指派任务")
async def assign_task(
    task_id: str,
    assignee_id: str,
    user=Depends(get_verified_user)
):
    """
    指派任务给指定用户。
    
    Args:
        task_id (str): 要指派的任务ID
        assignee_id (str): 指派给的用户ID
        user: 已认证的用户对象
        
    Returns:
        HSAITaskResponse: 更新后的任务信息
        
    Raises:
        HTTPException: 404 - 任务不存在或无权限访问
        HTTPException: 500 - 指派失败
        
    Note:
        - 任务创建者或管理员可以指派任务
        - 指派后会更新任务的assignee_id字段
    """
    try:
        # 验证任务所有权
        existing_task = HSAITasks.get_task_by_id(task_id)
        if not existing_task or existing_task.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # 更新任务指派人
        update_form = HSAITaskUpdateForm(
            assignee_id=assignee_id
        )
        
        task = HSAITasks.update_task_by_id(task_id, update_form)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign task"
            )
        
        return HSAITaskResponse(**task.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error assigning task: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 卡片管理
############################

@router.get("/cards/chat/{chat_id}", response_model=PaginatedHSAICardResponse, summary="获取聊天卡片")
async def get_chat_cards(
    chat_id: str,
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取聊天会话中的卡片列表（分页）。
    
    返回指定聊天会话中的所有卡片，支持分页查询。
    
    Args:
        chat_id (str): 聊天会话ID
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAICardResponse: 分页的卡片列表
        - data: 卡片列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
        
    Raises:
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 卡片按创建时间排序
        - 如果卡片关联了任务，会同时返回任务状态
        - 用于在聊天界面中显示交互式内容
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        cards = HSAICards.get_cards_by_chat_id(chat_id, limit=ps, offset=offset)
        
        # 获取总数
        total = HSAICards.get_cards_count(chat_id)
        
        responses = []
        for card in cards:
            # 如果卡片关联了任务，获取任务状态
            task_status = None
            if card.task_id:
                task = HSAITasks.get_task_by_id(card.task_id)
                if task:
                    task_status = task.status
            
            response = HSAICardResponse(
                **card.model_dump(),
                task_status=task_status
            )
            responses.append(response)
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAICardResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting chat cards: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/cards", response_model=HSAICardResponse, summary="创建卡片")
async def create_card(
    form_data: HSAICardForm,
    user=Depends(get_verified_user)
):
    """创建新卡片"""
    try:
        card = HSAICards.insert_new_card(user.id, form_data)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create card"
            )
        
        return HSAICardResponse(**card.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating card: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/cards/{card_id}", response_model=HSAICardResponse, summary="更新卡片")
async def update_card(
    card_id: str,
    updates: dict,
    user=Depends(get_verified_user)
):
    """更新卡片"""
    try:
        card = HSAICards.update_card_by_id(card_id, updates)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found or update failed"
            )
        
        return HSAICardResponse(**card.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating card: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )




