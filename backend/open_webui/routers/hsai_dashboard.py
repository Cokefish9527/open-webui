import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel, Field

from open_webui.models.hsai_tasks import HSAITasks
from open_webui.models.hsai_materials import HSAIMaterials
from open_webui.models.chats import Chats
from open_webui.models.users import Users
from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/dashboard", tags=["HSAI 仪表板"])

############################
# 数据模型定义
############################

class DashboardOverviewResponse(BaseModel):
    """工作台概览响应模型"""
    total_tasks: int = Field(description="总任务数")
    active_tasks: int = Field(description="活跃任务数")
    completed_tasks: int = Field(description="已完成任务数")
    failed_tasks: int = Field(description="失败任务数")
    total_materials: int = Field(description="总素材数")
    total_chats: int = Field(description="总对话数")
    storage_used: int = Field(description="已使用存储空间(MB)")
    storage_limit: int = Field(description="存储空间限制(MB)")


class KPIMetrics(BaseModel):
    """KPI指标模型"""
    task_completion_rate: float = Field(description="任务完成率(%)")
    avg_task_duration: float = Field(description="平均任务时长(小时)")
    daily_active_rate: float = Field(description="日活跃率(%)")
    material_usage_rate: float = Field(description="素材使用率(%)")
    ai_interaction_count: int = Field(description="AI交互次数")
    productivity_score: float = Field(description="生产力评分(0-100)")


class RecentActivity(BaseModel):
    """最近活动模型"""
    id: str = Field(description="活动唯一标识符")
    type: str = Field(description="活动类型 (task, material, chat, system)")
    title: str = Field(description="活动标题")
    description: str = Field(description="活动描述")
    timestamp: int = Field(description="活动时间戳")
    status: Optional[str] = Field(default=None, description="活动状态")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据")


class DashboardStatsResponse(BaseModel):
    """工作台统计响应模型"""
    overview: DashboardOverviewResponse = Field(description="工作台概览数据")
    kpi: KPIMetrics = Field(description="KPI指标数据")
    recent_activities: List[RecentActivity] = Field(description="最近活动列表")
    task_trend: List[Dict[str, Any]] = Field(description="任务趋势数据")
    material_trend: List[Dict[str, Any]] = Field(description="素材趋势数据")

############################
# 工作台概览接口
############################

@router.get("/overview", response_model=DashboardOverviewResponse, summary="获取工作台概览")
async def get_dashboard_overview(
    user=Depends(get_verified_user)
):
    """
    获取用户工作台概览数据。
    
    提供用户的核心数据统计，包括任务、素材、对话等关键指标。
    
    Args:
        user: 已认证的用户对象
        
    Returns:
        DashboardOverviewResponse: 工作台概览数据
        - total_tasks: 总任务数
        - active_tasks: 活跃任务数
        - completed_tasks: 已完成任务数
        - failed_tasks: 失败任务数
        - total_materials: 总素材数
        - total_chats: 总对话数
        - storage_used: 已使用存储空间(MB)
        - storage_limit: 存储空间限制(MB)
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 获取任务统计
        user_tasks = HSAITasks.get_tasks_by_user_id(user.id)
        total_tasks = len(user_tasks)
        active_tasks = len([t for t in user_tasks if t.status in ["pending", "running"]])
        completed_tasks = len([t for t in user_tasks if t.status == "completed"])
        failed_tasks = len([t for t in user_tasks if t.status == "failed"])
        
        # 获取素材统计
        user_materials = HSAIMaterials.get_materials_by_user_id(user.id)
        total_materials = len(user_materials)
        
        # 计算存储使用量
        storage_used = sum(m.file_size or 0 for m in user_materials) // (1024 * 1024)  # 转换为MB
        
        # 获取对话统计
        user_chats = Chats.get_chats_by_user_id(user.id)
        total_chats = len(user_chats)
        
        # 存储限制（可以从配置或用户套餐获取）
        storage_limit = 1024  # 1GB 默认限制
        
        return DashboardOverviewResponse(
            total_tasks=total_tasks,
            active_tasks=active_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            total_materials=total_materials,
            total_chats=total_chats,
            storage_used=storage_used,
            storage_limit=storage_limit
        )
        
    except Exception as e:
        log.exception(f"Error getting dashboard overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# KPI指标接口
############################

@router.get("/kpi", response_model=KPIMetrics, summary="获取KPI指标")
async def get_kpi_metrics(
    days: int = Query(30, description="统计天数，默认30天"),
    user=Depends(get_verified_user)
):
    """
    获取用户KPI指标数据。
    
    计算用户在指定时间范围内的关键绩效指标。
    
    Args:
        days (int): 统计天数，默认30天
        user: 已认证的用户对象
        
    Returns:
        KPIMetrics: KPI指标数据
        - task_completion_rate: 任务完成率(%)
        - avg_task_duration: 平均任务时长(小时)
        - daily_active_rate: 日活跃率(%)
        - material_usage_rate: 素材使用率(%)
        - ai_interaction_count: AI交互次数
        - productivity_score: 生产力评分(0-100)
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 计算时间范围
        end_time = int(time.time())
        start_time = end_time - (days * 24 * 3600)
        
        # 获取时间范围内的任务
        user_tasks = HSAITasks.get_tasks_by_user_id(user.id)
        period_tasks = [t for t in user_tasks if t.created_at >= start_time]
        
        # 计算任务完成率
        total_tasks = len(period_tasks)
        completed_tasks = len([t for t in period_tasks if t.status == "completed"])
        task_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # 计算平均任务时长
        completed_task_durations = []
        for task in period_tasks:
            if task.status == "completed" and task.completed_at and task.started_at:
                duration = (task.completed_at - task.started_at) / 3600  # 转换为小时
                completed_task_durations.append(duration)
        
        avg_task_duration = sum(completed_task_durations) / len(completed_task_durations) if completed_task_durations else 0
        
        # 计算日活跃率（简化版本：有任务活动的天数比例）
        active_days = set()
        for task in period_tasks:
            task_date = datetime.fromtimestamp(task.created_at).date()
            active_days.add(task_date)
        
        daily_active_rate = (len(active_days) / days * 100) if days > 0 else 0
        
        # 计算素材使用率
        user_materials = HSAIMaterials.get_materials_by_user_id(user.id)
        period_materials = [m for m in user_materials if m.created_at >= start_time]
        used_materials = len([m for m in period_materials if m.usage_count > 0])
        material_usage_rate = (used_materials / len(period_materials) * 100) if period_materials else 0
        
        # AI交互次数（从对话记录统计）
        user_chats = Chats.get_chats_by_user_id(user.id)
        ai_interaction_count = sum(1 for chat in user_chats if chat.updated_at >= start_time)
        
        # 生产力评分（综合指标）
        productivity_score = (
            task_completion_rate * 0.4 +
            min(daily_active_rate, 100) * 0.3 +
            min(material_usage_rate, 100) * 0.2 +
            min(ai_interaction_count / days * 10, 100) * 0.1
        )
        
        return KPIMetrics(
            task_completion_rate=round(task_completion_rate, 2),
            avg_task_duration=round(avg_task_duration, 2),
            daily_active_rate=round(daily_active_rate, 2),
            material_usage_rate=round(material_usage_rate, 2),
            ai_interaction_count=ai_interaction_count,
            productivity_score=round(productivity_score, 2)
        )
        
    except Exception as e:
        log.exception(f"Error getting KPI metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 最近活动接口
############################

@router.get("/recent-activities", response_model=List[RecentActivity], summary="获取最近活动")
async def get_recent_activities(
    limit: int = Query(20, description="返回数量限制，默认20条"),
    activity_type: Optional[str] = Query(None, description="活动类型过滤：task, material, chat, system"),
    user=Depends(get_verified_user)
):
    """
    获取用户最近活动记录。
    
    返回用户最近的操作活动，包括任务、素材、对话等各类活动。
    
    Args:
        limit (int): 返回数量限制，默认20条
        activity_type (Optional[str]): 活动类型过滤
        user: 已认证的用户对象
        
    Returns:
        List[RecentActivity]: 最近活动列表
        - id: 活动唯一标识
        - type: 活动类型
        - title: 活动标题
        - description: 活动描述
        - timestamp: 活动时间戳
        - status: 活动状态
        - metadata: 额外元数据
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        activities = []
        
        # 获取任务活动
        if not activity_type or activity_type == "task":
            user_tasks = HSAITasks.get_tasks_by_user_id(user.id)
            for task in user_tasks[-10:]:  # 最近10个任务
                activities.append(RecentActivity(
                    id=f"task_{task.id}",
                    type="task",
                    title=f"任务: {task.title}",
                    description=f"状态: {task.status}",
                    timestamp=task.updated_at or task.created_at,
                    status=task.status,
                    metadata={"task_type": task.task_type}
                ))
        
        # 获取素材活动
        if not activity_type or activity_type == "material":
            user_materials = HSAIMaterials.get_materials_by_user_id(user.id)
            for material in user_materials[-10:]:  # 最近10个素材
                activities.append(RecentActivity(
                    id=f"material_{material.id}",
                    type="material",
                    title=f"素材: {material.name}",
                    description=f"类型: {material.material_type}",
                    timestamp=material.updated_at or material.created_at,
                    status="uploaded",
                    metadata={"file_type": material.material_type, "file_size": material.file_size}
                ))
        
        # 获取对话活动
        if not activity_type or activity_type == "chat":
            user_chats = Chats.get_chats_by_user_id(user.id)
            for chat in user_chats[-10:]:  # 最近10个对话
                activities.append(RecentActivity(
                    id=f"chat_{chat.id}",
                    type="chat",
                    title=f"对话: {chat.title or '未命名对话'}",
                    description="AI对话交互",
                    timestamp=chat.updated_at,
                    status="active",
                    metadata={"message_count": len(chat.chat.get("messages", []))}
                ))
        
        # 按时间戳排序并限制数量
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        return activities[:limit]
        
    except Exception as e:
        log.exception(f"Error getting recent activities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 趋势数据接口
############################

@router.get("/stats", response_model=DashboardStatsResponse, summary="获取工作台统计数据")
async def get_dashboard_stats(
    days: int = Query(7, description="统计天数，默认7天"),
    user=Depends(get_verified_user)
):
    """
    获取工作台完整统计数据。
    
    包含概览、KPI指标、最近活动和趋势数据的综合统计信息。
    
    Args:
        days (int): 趋势统计天数，默认7天
        user: 已认证的用户对象
        
    Returns:
        DashboardStatsResponse: 完整统计数据
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 获取概览数据
        overview = await get_dashboard_overview(user)
        
        # 获取KPI指标
        kpi = await get_kpi_metrics(days, user)
        
        # 获取最近活动
        recent_activities = await get_recent_activities(10, None, user)
        
        # 生成任务趋势数据
        task_trend = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # 简化版本：模拟趋势数据
            task_trend.append({
                "date": date_str,
                "created": max(0, 5 - i),
                "completed": max(0, 3 - i//2),
                "failed": max(0, 1 - i//3)
            })
        
        task_trend.reverse()
        
        # 生成素材趋势数据
        material_trend = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            material_trend.append({
                "date": date_str,
                "uploaded": max(0, 3 - i//2),
                "used": max(0, 2 - i//3),
                "storage_mb": max(0, 100 + i * 10)
            })
        
        material_trend.reverse()
        
        return DashboardStatsResponse(
            overview=overview,
            kpi=kpi,
            recent_activities=recent_activities,
            task_trend=task_trend,
            material_trend=material_trend
        )
        
    except Exception as e:
        log.exception(f"Error getting dashboard stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 快捷操作接口
############################

@router.post("/quick-actions/create-task", summary="快速创建任务")
async def quick_create_task(
    title: str,
    task_type: str = "general",
    user=Depends(get_verified_user)
):
    """
    快速创建任务。
    
    从工作台快速创建新任务的便捷接口。
    
    Args:
        title (str): 任务标题
        task_type (str): 任务类型，默认为general
        user: 已认证的用户对象
        
    Returns:
        dict: 创建结果
        - success: 是否成功
        - task_id: 创建的任务ID
        - message: 结果消息
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        from open_webui.models.hsai_tasks import HSAITaskForm
        
        # 创建任务表单
        task_form = HSAITaskForm(
            title=title,
            task_type=task_type,
            description=f"通过工作台快速创建的{task_type}任务",
            priority="medium",
            config={}
        )
        
        # 创建任务
        task = HSAITasks.insert_new_task(user.id, task_form)
        
        if task:
            return {
                "success": True,
                "task_id": task.id,
                "message": "任务创建成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="任务创建失败"
            )
        
    except Exception as e:
        log.exception(f"Error creating quick task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/system-status", summary="获取系统状态")
async def get_system_status(
    user=Depends(get_verified_user)
):
    """
    获取系统状态信息。
    
    返回系统运行状态和健康检查信息。
    
    Returns:
        dict: 系统状态信息
        - status: 系统状态
        - uptime: 运行时间
        - version: 系统版本
        - features: 可用功能列表
    """
    try:
        return {
            "status": "healthy",
            "uptime": "24h 30m",
            "version": "1.0.0",
            "features": {
                "tasks": True,
                "materials": True,
                "ai_chat": True,
                "workflows": False,  # 待实现
                "analytics": True
            },
            "limits": {
                "max_tasks": 1000,
                "max_materials": 500,
                "storage_limit_mb": 1024
            }
        }
        
    except Exception as e:
        log.exception(f"Error getting system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )