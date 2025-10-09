import logging
from typing import Optional, List

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
    HSAITaskResponse
)

from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/projects", tags=["HSAI 项目管理"])

# 项目模板定义
PROJECT_MAIN_TASK_TEMPLATES = {
    "company_info": {
        "title": "完善企业信息",
        "description": "请提供您企业的基本信息，包括企业名称、行业、规模等",
        "task_type": "workflow_execution",
        "task_category": "main",
        "workflow_type": "company_info",
        "priority": 10,
        "prompt_config": {
            "system_prompt": "您是一个企业信息收集助手，请引导用户完善企业基本信息",
            "initial_message": "您好！为了更好地为您服务，我们需要收集一些您企业的基本信息。",
            "guidance_questions": [
                "请告诉我您的企业名称是什么？",
                "您的企业属于哪个行业？",
                "企业大概有多少员工？",
                "企业成立多长时间了？"
            ],
            "completion_criteria": "用户提供了完整的企业基本信息",
            "success_message": "感谢您提供的企业信息，我们已经记录完毕。"
        }
    },
    "project_info": {
        "title": "完善项目信息",
        "description": "请提供项目的基本信息，包括项目目标、预期成果、时间规划等",
        "task_type": "workflow_execution",
        "task_category": "main",
        "workflow_type": "project_info",
        "priority": 9,
        "prompt_config": {
            "system_prompt": "您是一个项目信息收集助手，请引导用户完善项目基本信息",
            "initial_message": "接下来我们需要了解您的项目基本信息，以便为您提供更好的服务。",
            "guidance_questions": [
                "请描述一下您的项目目标是什么？",
                "您期望通过这个项目达成什么成果？",
                "项目的时间规划是怎样的？",
                "项目的主要挑战有哪些？"
            ],
            "completion_criteria": "用户提供了完整的项目基本信息",
            "success_message": "感谢您提供的项目信息，我们已经记录完毕。"
        }
    },
    "material_init": {
        "title": "素材库初始化",
        "description": "初始化项目素材库，上传相关素材文件",
        "task_type": "material_processing",
        "task_category": "main",
        "workflow_type": "material_init",
        "priority": 8,
        "prompt_config": {
            "system_prompt": "您是一个素材管理助手，请引导用户完成素材库初始化",
            "initial_message": "现在让我们初始化您的项目素材库，请上传相关素材文件。",
            "guidance_questions": [
                "请上传项目相关的图片素材",
                "请上传项目相关的视频素材",
                "请上传项目相关的文档素材"
            ],
            "completion_criteria": "用户完成了素材库的初始化上传",
            "success_message": "素材库初始化完成，您可以随时添加更多素材。"
        }
    }
}

@router.get("/", response_model=PaginatedHSAIProjectResponse, summary="获取项目列表")
async def get_projects(
    status: Optional[str] = Query(None, description="项目状态过滤"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
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
    """更新项目"""
    try:
        # 验证项目所有权
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
    """删除项目"""
    try:
        # 验证项目所有权
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
    """获取项目关联的任务列表"""
    try:
        # 验证项目所有权
        project = HSAIProjects.get_project_by_id(project_id)
        if not project or project.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # 获取项目关联的任务
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