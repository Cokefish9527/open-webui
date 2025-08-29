import logging
import time
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

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
    HSAICardType
)

from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.socket.main import get_event_emitter

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/tasks", tags=["hsai_tasks"])

############################
# 任务管理
############################

@router.get("/", response_model=List[HSAITaskResponse])
async def get_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    chat_id: Optional[str] = None,
    user=Depends(get_verified_user)
):
    """
    获取用户的任务列表。
    
    支持按状态、类型和聊天会话进行过滤，返回任务的详细信息和预估执行时间。
    
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
        chat_id (Optional[str]): 聊天会话ID过滤
        user: 已认证的用户对象
        
    Returns:
        List[HSAITaskResponse]: 任务列表
        - id: 任务唯一标识
        - title: 任务标题
        - description: 任务描述
        - task_type: 任务类型
        - status: 当前状态
        - progress: 执行进度（0-100）
        - estimated_duration: 预估执行时间（秒）
        - created_at: 创建时间
        - started_at: 开始时间
        - completed_at: 完成时间
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        tasks = HSAITasks.get_tasks_by_user_id(
            user.id,
            status=status,
            task_type=task_type,
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
        
        return responses
        
    except Exception as e:
        log.exception(f"Error getting tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/", response_model=HSAITaskResponse)
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
            
            # 通过WebSocket通知前端
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    "hsai_task_created",
                    {
                        "task_id": task.id,
                        "chat_id": form_data.chat_id,
                        "user_id": user.id
                    },
                    to=user.id
                )
        
        return HSAITaskResponse(**task.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{task_id}", response_model=HSAITaskResponse)
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/{task_id}", response_model=HSAITaskResponse)
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
            
            # 通过WebSocket通知前端
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    "hsai_task_updated",
                    {
                        "task_id": task_id,
                        "chat_id": existing_task.chat_id,
                        "status": task.status,
                        "progress": task.progress,
                        "user_id": user.id
                    },
                    to=user.id
                )
        
        return HSAITaskResponse(**task.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/{task_id}/start", response_model=HSAITaskResponse)
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
        - 会通过WebSocket实时通知前端
        - 实际的AI处理逻辑需要通过队列系统异步执行
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
        
        # 在这里可以添加异步任务执行逻辑
        # 例如：通过Celery或其他队列系统执行实际的AI处理
        
        # 通过WebSocket通知前端
        emitter = get_event_emitter()
        if emitter and existing_task.chat_id:
            await emitter.emit(
                "hsai_task_started",
                {
                    "task_id": task_id,
                    "chat_id": existing_task.chat_id,
                    "user_id": user.id
                },
                to=user.id
            )
        
        return HSAITaskResponse(**task.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error starting task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/{task_id}/cancel", response_model=HSAITaskResponse)
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
        - 会通过WebSocket通知前端更新状态
        - 需要确保后台处理进程也能正确停止
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
        
        # 通过WebSocket通知前端
        emitter = get_event_emitter()
        if emitter and existing_task.chat_id:
            await emitter.emit(
                "hsai_task_cancelled",
                {
                    "task_id": task_id,
                    "chat_id": existing_task.chat_id,
                    "user_id": user.id
                },
                to=user.id
            )
        
        return HSAITaskResponse(**task.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error cancelling task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/{task_id}/progress", response_model=bool)
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
        - 会通过WebSocket实时推送进度更新
        - 前端可以据此显示进度条
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
        
        if result and existing_task.chat_id:
            # 通过WebSocket实时更新进度
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    "hsai_task_progress",
                    {
                        "task_id": task_id,
                        "chat_id": existing_task.chat_id,
                        "progress": progress,
                        "user_id": user.id
                    },
                    to=user.id
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating task progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# 卡片管理
############################

@router.get("/cards/chat/{chat_id}", response_model=List[HSAICardResponse])
async def get_chat_cards(
    chat_id: str,
    user=Depends(get_verified_user)
):
    """
    获取聊天会话中的所有卡片。
    
    返回指定聊天会话中的所有交互卡片，包括任务卡片、结果卡片等。
    
    Args:
        chat_id (str): 聊天会话ID
        user: 已认证的用户对象
        
    Returns:
        List[HSAICardResponse]: 卡片列表
        - id: 卡片唯一标识
        - title: 卡片标题
        - description: 卡片描述
        - card_type: 卡片类型
        - content: 卡片内容（JSON格式）
        - actions: 可用操作按钮
        - task_id: 关联的任务ID（如果有）
        - task_status: 关联任务的状态（如果有）
        - created_at: 创建时间
        
    Raises:
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 卡片按创建时间排序
        - 如果卡片关联了任务，会同时返回任务状态
        - 用于在聊天界面中显示交互式内容
    """
    try:
        cards = HSAICards.get_cards_by_chat_id(chat_id)
        
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
        
        return responses
        
    except Exception as e:
        log.exception(f"Error getting chat cards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/cards", response_model=HSAICardResponse)
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/cards/{card_id}", response_model=HSAICardResponse)
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


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


@router.get("/stats", response_model=TaskStatsResponse)
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
        tasks = HSAITasks.get_tasks_by_user_id(user.id)
        
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
        
        return TaskStatsResponse(**stats)
        
    except Exception as e:
        log.exception(f"Error getting task stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )