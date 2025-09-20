import logging
import time
import uuid
import json
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel, Field

from open_webui.models.hsai_tasks import HSAITasks
from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.socket.main import get_event_emitter

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/workflows", tags=["HSAI 工作流"])

############################
# 数据模型定义
############################

class WorkflowTriggerRequest(BaseModel):
    """工作流触发请求模型"""
    workflow_id: str
    input_data: Dict[str, Any]
    task_id: Optional[str] = None
    priority: str = "medium"  # low, medium, high
    callback_url: Optional[str] = None


class WorkflowStatusResponse(BaseModel):
    """工作流状态响应模型"""
    workflow_id: str = Field(description="工作流ID")
    execution_id: str = Field(description="执行ID")
    status: str = Field(description="执行状态 (pending, running, completed, failed, cancelled)")
    progress: int = Field(description="执行进度 (0-100)")
    current_step: Optional[str] = Field(default=None, description="当前步骤")
    total_steps: int = Field(default=0, description="总步骤数")
    completed_steps: int = Field(default=0, description="已完成步骤数")
    start_time: Optional[int] = Field(default=None, description="开始时间戳")
    end_time: Optional[int] = Field(default=None, description="结束时间戳")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="输出数据")


class WorkflowWebhookData(BaseModel):
    """工作流Webhook数据模型"""
    execution_id: str = Field(description="执行ID")
    workflow_id: str = Field(description="工作流ID")
    status: str = Field(description="执行状态")
    event_type: str = Field(description="事件类型 (started, progress, completed, failed)")
    timestamp: int = Field(description="时间戳")
    data: Optional[Dict[str, Any]] = Field(default=None, description="事件数据")


class WorkflowTemplateResponse(BaseModel):
    """工作流模板响应模型"""
    id: str = Field(description="模板ID")
    name: str = Field(description="模板名称")
    description: str = Field(description="模板描述")
    category: str = Field(description="分类 (content_creation, data_processing, automation)")
    input_schema: Dict[str, Any] = Field(description="输入模式")
    output_schema: Dict[str, Any] = Field(description="输出模式")
    steps: List[Dict[str, Any]] = Field(description="步骤列表")
    is_active: bool = Field(default=True, description="是否激活")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class WorkflowExecutionLog(BaseModel):
    """工作流执行日志模型"""
    execution_id: str = Field(description="执行ID")
    step_name: str = Field(description="步骤名称")
    status: str = Field(description="步骤状态")
    timestamp: int = Field(description="时间戳")
    duration: Optional[int] = Field(default=None, description="执行时长(毫秒)")
    input_data: Optional[Dict[str, Any]] = Field(default=None, description="输入数据")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="输出数据")
    error_message: Optional[str] = Field(default=None, description="错误信息")

############################
# 工作流触发接口
############################

@router.post("/trigger", response_model=WorkflowStatusResponse, summary="触发工作流")
async def trigger_workflow(
    request_data: WorkflowTriggerRequest,
    user=Depends(get_verified_user)
):
    """
    触发指定的工作流执行。
    
    启动n8n工作流或内置自动化流程，支持异步执行和状态跟踪。
    
    Args:
        request_data (WorkflowTriggerRequest): 工作流触发请求
        - workflow_id: 工作流ID
        - input_data: 输入数据
        - task_id: 关联的任务ID（可选）
        - priority: 执行优先级
        - callback_url: 回调URL（可选）
        user: 已认证的用户对象
        
    Returns:
        WorkflowStatusResponse: 工作流执行状态
        
    Raises:
        HTTPException: 404 - 工作流不存在
        HTTPException: 400 - 输入数据无效
        HTTPException: 500 - 触发失败
        
    Note:
        - 支持同步和异步执行模式
        - 自动创建执行记录和日志
        - 通过WebSocket实时通知执行状态
        - 支持与任务系统的深度集成
    """
    try:
        # 生成执行ID
        execution_id = str(uuid.uuid4())
        current_time = int(time.time())
        
        # 验证工作流是否存在（简化版本：预定义工作流）
        predefined_workflows = {
            "content_generation": {
                "name": "内容生成工作流",
                "steps": ["analyze_requirements", "generate_content", "review_content", "format_output"],
                "estimated_duration": 300  # 5分钟
            },
            "data_processing": {
                "name": "数据处理工作流",
                "steps": ["validate_input", "process_data", "generate_report", "save_results"],
                "estimated_duration": 600  # 10分钟
            },
            "task_automation": {
                "name": "任务自动化工作流",
                "steps": ["parse_task", "execute_actions", "validate_results", "notify_completion"],
                "estimated_duration": 180  # 3分钟
            }
        }
        
        if request_data.workflow_id not in predefined_workflows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow not found: {request_data.workflow_id}"
            )
        
        workflow_info = predefined_workflows[request_data.workflow_id]
        
        # 验证输入数据（简化版本）
        if not request_data.input_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input data is required"
            )
        
        # 创建工作流执行记录
        execution_record = {
            "execution_id": execution_id,
            "workflow_id": request_data.workflow_id,
            "user_id": user.id,
            "task_id": request_data.task_id,
            "status": "pending",
            "progress": 0,
            "current_step": workflow_info["steps"][0],
            "total_steps": len(workflow_info["steps"]),
            "completed_steps": 0,
            "start_time": current_time,
            "input_data": request_data.input_data,
            "priority": request_data.priority,
            "callback_url": request_data.callback_url,
            "created_at": current_time
        }
        
        # 这里应该保存到数据库，简化版本存储在内存中
        # 实际实现中应该有专门的WorkflowExecutions模型
        
        # 如果关联了任务，更新任务状态
        if request_data.task_id:
            try:
                HSAITasks.update_task_by_id(request_data.task_id, {
                    "workflow_execution_id": execution_id,
                    "status": "running",
                    "updated_at": current_time
                })
            except Exception as e:
                log.warning(f"Failed to update task status: {e}")
        
        # 异步启动工作流执行
        # 这里应该调用实际的工作流引擎（如n8n API）
        # 简化版本：模拟异步执行
        asyncio.create_task(_execute_workflow_async(
            execution_id, request_data.workflow_id, workflow_info, 
            request_data.input_data, user.id
        ))
        
        # 通过WebSocket通知前端
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_response",  # 合并到核心事件中
                {
                    "type": "hsai_response",
                    "subtype": "workflow_started",  # 添加子类型用于区分原始事件
                    "execution_id": execution_id,
                    "workflow_id": request_data.workflow_id,
                    "user_id": user.id
                },
                to=user.id
            )
        
        return WorkflowStatusResponse(
            workflow_id=request_data.workflow_id,
            execution_id=execution_id,
            status="pending",
            progress=0,
            current_step=workflow_info["steps"][0],
            total_steps=len(workflow_info["steps"]),
            completed_steps=0,
            start_time=current_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error triggering workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 工作流状态查询接口
############################

@router.get("/{workflow_id}/status", response_model=WorkflowStatusResponse, summary="获取工作流状态")
async def get_workflow_status(
    workflow_id: str,
    execution_id: Optional[str] = Query(None, description="执行ID，不提供则返回最新执行状态"),
    user=Depends(get_verified_user)
):
    """
    获取工作流执行状态。
    
    查询指定工作流的执行状态和进度信息。
    
    Args:
        workflow_id (str): 工作流ID
        execution_id (Optional[str]): 执行ID，不提供则返回最新执行
        user: 已认证的用户对象
        
    Returns:
        WorkflowStatusResponse: 工作流执行状态
        
    Raises:
        HTTPException: 404 - 工作流执行不存在
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 简化版本：模拟状态查询
        # 实际实现中应该从数据库查询执行记录
        
        if not execution_id:
            # 如果没有提供execution_id，返回最新的执行状态
            execution_id = "latest_execution_id"  # 这里应该从数据库查询
        
        # 模拟状态数据
        mock_status = WorkflowStatusResponse(
            workflow_id=workflow_id,
            execution_id=execution_id,
            status="running",
            progress=65,
            current_step="generate_content",
            total_steps=4,
            completed_steps=2,
            start_time=int(time.time()) - 300,  # 5分钟前开始
            output_data={"partial_results": "生成中..."}
        )
        
        return mock_status
        
    except Exception as e:
        log.exception(f"Error getting workflow status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/executions", summary="获取工作流执行历史")
async def get_workflow_executions(
    workflow_id: Optional[str] = Query(None, description="工作流ID过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(20, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    user=Depends(get_verified_user)
):
    """
    获取用户的工作流执行历史。
    
    Args:
        workflow_id (Optional[str]): 工作流ID过滤
        status (Optional[str]): 状态过滤
        limit (int): 返回数量限制
        offset (int): 偏移量
        user: 已认证的用户对象
        
    Returns:
        dict: 执行历史列表
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 简化版本：返回模拟数据
        # 实际实现中应该从数据库查询用户的执行记录
        
        mock_executions = []
        for i in range(min(limit, 10)):  # 最多返回10条模拟数据
            execution = {
                "execution_id": f"exec_{i+1}",
                "workflow_id": workflow_id or "content_generation",
                "status": ["completed", "running", "failed"][i % 3],
                "progress": 100 if i % 3 == 0 else (50 if i % 3 == 1 else 0),
                "start_time": int(time.time()) - (i * 3600),  # 每小时一个
                "end_time": int(time.time()) - (i * 3600) + 300 if i % 3 == 0 else None,
                "duration": 300 if i % 3 == 0 else None
            }
            
            # 应用状态过滤
            if status and execution["status"] != status:
                continue
                
            mock_executions.append(execution)
        
        return {
            "total": len(mock_executions),
            "executions": mock_executions[offset:offset + limit]
        }
        
    except Exception as e:
        log.exception(f"Error getting workflow executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 工作流控制接口
############################

@router.post("/{execution_id}/cancel", summary="取消工作流执行")
async def cancel_workflow_execution(
    execution_id: str,
    user=Depends(get_verified_user)
):
    """
    取消正在执行的工作流。
    
    Args:
        execution_id (str): 执行ID
        user: 已认证的用户对象
        
    Returns:
        dict: 取消结果
        
    Raises:
        HTTPException: 404 - 执行不存在或无权限
        HTTPException: 400 - 执行已完成，无法取消
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 验证执行记录的所有权
        # 实际实现中应该从数据库查询并验证
        
        # 简化版本：模拟取消操作
        # 这里应该调用工作流引擎的取消API
        
        # 更新执行状态
        # 实际实现中应该更新数据库记录
        
        # 通过WebSocket通知前端
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_response",  # 合并到核心事件中
                {
                    "type": "hsai_response",
                    "subtype": "workflow_cancelled",  # 添加子类型用于区分原始事件
                    "execution_id": execution_id,
                    "user_id": user.id
                },
                to=user.id
            )
        
        return {
            "success": True,
            "message": "Workflow execution cancelled successfully",
            "execution_id": execution_id
        }
        
    except Exception as e:
        log.exception(f"Error cancelling workflow execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/{execution_id}/retry", summary="重试工作流执行")
async def retry_workflow_execution(
    execution_id: str,
    user=Depends(get_verified_user)
):
    """
    重试失败的工作流执行。
    
    Args:
        execution_id (str): 原执行ID
        user: 已认证的用户对象
        
    Returns:
        WorkflowStatusResponse: 新的执行状态
        
    Raises:
        HTTPException: 404 - 执行不存在或无权限
        HTTPException: 400 - 执行状态不允许重试
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 验证原执行记录
        # 实际实现中应该从数据库查询原执行记录
        
        # 生成新的执行ID
        new_execution_id = str(uuid.uuid4())
        current_time = int(time.time())
        
        # 创建新的执行记录（复制原执行的配置）
        # 实际实现中应该从原记录复制配置并创建新记录
        
        # 启动重试执行
        # 这里应该调用工作流引擎重新执行
        
        return WorkflowStatusResponse(
            workflow_id="content_generation",  # 从原记录获取
            execution_id=new_execution_id,
            status="pending",
            progress=0,
            current_step="analyze_requirements",
            total_steps=4,
            completed_steps=0,
            start_time=current_time
        )
        
    except Exception as e:
        log.exception(f"Error retrying workflow execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# Webhook接口
############################

@router.post("/webhook", summary="工作流Webhook回调")
async def workflow_webhook(
    webhook_data: WorkflowWebhookData,
    request: Request
):
    """
    处理工作流引擎的Webhook回调。
    
    接收来自n8n或其他工作流引擎的状态更新通知。
    
    Args:
        webhook_data (WorkflowWebhookData): Webhook数据
        request: HTTP请求对象
        
    Returns:
        dict: 处理结果
        
    Note:
        - 验证Webhook签名（生产环境必需）
        - 更新执行状态和进度
        - 通过WebSocket通知前端
        - 触发相关的后续操作
    """
    try:
        # 验证Webhook签名（简化版本跳过）
        # 实际实现中应该验证请求签名确保安全性
        
        # 更新执行状态
        # 实际实现中应该更新数据库中的执行记录
        
        # 根据事件类型处理不同逻辑
        if webhook_data.event_type == "started":
            # 工作流开始执行
            log.info(f"Workflow {webhook_data.workflow_id} started: {webhook_data.execution_id}")
            
        elif webhook_data.event_type == "progress":
            # 工作流进度更新
            log.info(f"Workflow {webhook_data.workflow_id} progress: {webhook_data.data}")
            
        elif webhook_data.event_type == "completed":
            # 工作流完成
            log.info(f"Workflow {webhook_data.workflow_id} completed: {webhook_data.execution_id}")
            
            # 如果关联了任务，更新任务状态
            if webhook_data.data and "task_id" in webhook_data.data:
                task_id = webhook_data.data["task_id"]
                try:
                    HSAITasks.update_task_by_id(task_id, {
                        "status": "completed",
                        "completed_at": webhook_data.timestamp,
                        "result": webhook_data.data.get("output_data"),
                        "updated_at": webhook_data.timestamp
                    })
                except Exception as e:
                    log.warning(f"Failed to update task status: {e}")
            
        elif webhook_data.event_type == "failed":
            # 工作流失败
            log.error(f"Workflow {webhook_data.workflow_id} failed: {webhook_data.data}")
            
            # 更新关联任务状态
            if webhook_data.data and "task_id" in webhook_data.data:
                task_id = webhook_data.data["task_id"]
                try:
                    HSAITasks.update_task_by_id(task_id, {
                        "status": "failed",
                        "error_message": webhook_data.data.get("error_message"),
                        "updated_at": webhook_data.timestamp
                    })
                except Exception as e:
                    log.warning(f"Failed to update task status: {e}")
        
        # 通过WebSocket广播状态更新
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_response" if webhook_data.event_type != "failed" else "hsai_error",  # 合并到核心事件中
                {
                    "type": "hsai_response" if webhook_data.event_type != "failed" else "hsai_error",
                    "subtype": f"workflow_{webhook_data.event_type}",  # 添加子类型用于区分原始事件
                    "execution_id": webhook_data.execution_id,
                    "workflow_id": webhook_data.workflow_id,
                    "status": webhook_data.status,
                    "data": webhook_data.data
                }
            )
        
        return {
            "success": True,
            "message": "Webhook processed successfully",
            "execution_id": webhook_data.execution_id
        }
        
    except Exception as e:
        log.exception(f"Error processing workflow webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 工作流模板接口
############################

@router.get("/templates", response_model=List[WorkflowTemplateResponse], summary="获取工作流模板")
async def get_workflow_templates(
    category: Optional[str] = Query(None, description="分类过滤"),
    user=Depends(get_verified_user)
):
    """
    获取可用的工作流模板列表。
    
    Args:
        category (Optional[str]): 分类过滤
        user: 已认证的用户对象
        
    Returns:
        List[WorkflowTemplateResponse]: 工作流模板列表
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 预定义的工作流模板
        templates = [
            WorkflowTemplateResponse(
                id="content_generation",
                name="内容生成工作流",
                description="基于AI的智能内容生成流程，支持多种内容类型",
                category="content_creation",
                input_schema={
                    "type": "object",
                    "properties": {
                        "content_type": {"type": "string", "enum": ["article", "video_script", "social_post"]},
                        "topic": {"type": "string"},
                        "target_audience": {"type": "string"},
                        "tone": {"type": "string", "enum": ["professional", "casual", "humorous"]}
                    },
                    "required": ["content_type", "topic"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "generated_content": {"type": "string"},
                        "metadata": {"type": "object"},
                        "quality_score": {"type": "number"}
                    }
                },
                steps=[
                    {"name": "analyze_requirements", "description": "分析内容需求"},
                    {"name": "generate_content", "description": "生成内容"},
                    {"name": "review_content", "description": "内容审核"},
                    {"name": "format_output", "description": "格式化输出"}
                ],
                created_at=int(time.time()) - 86400,
                updated_at=int(time.time()) - 3600
            ),
            WorkflowTemplateResponse(
                id="data_processing",
                name="数据处理工作流",
                description="自动化数据处理和分析流程",
                category="data_processing",
                input_schema={
                    "type": "object",
                    "properties": {
                        "data_source": {"type": "string"},
                        "processing_type": {"type": "string", "enum": ["clean", "analyze", "transform"]},
                        "output_format": {"type": "string", "enum": ["json", "csv", "excel"]}
                    },
                    "required": ["data_source", "processing_type"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "processed_data": {"type": "object"},
                        "statistics": {"type": "object"},
                        "report_url": {"type": "string"}
                    }
                },
                steps=[
                    {"name": "validate_input", "description": "验证输入数据"},
                    {"name": "process_data", "description": "处理数据"},
                    {"name": "generate_report", "description": "生成报告"},
                    {"name": "save_results", "description": "保存结果"}
                ],
                created_at=int(time.time()) - 172800,
                updated_at=int(time.time()) - 7200
            ),
            WorkflowTemplateResponse(
                id="task_automation",
                name="任务自动化工作流",
                description="智能任务执行和自动化流程",
                category="automation",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task_type": {"type": "string"},
                        "parameters": {"type": "object"},
                        "schedule": {"type": "string"}
                    },
                    "required": ["task_type"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "execution_result": {"type": "object"},
                        "logs": {"type": "array"},
                        "next_execution": {"type": "string"}
                    }
                },
                steps=[
                    {"name": "parse_task", "description": "解析任务"},
                    {"name": "execute_actions", "description": "执行操作"},
                    {"name": "validate_results", "description": "验证结果"},
                    {"name": "notify_completion", "description": "通知完成"}
                ],
                created_at=int(time.time()) - 259200,
                updated_at=int(time.time()) - 10800
            )
        ]
        
        # 应用分类过滤
        if category:
            templates = [t for t in templates if t.category == category]
        
        return templates
        
    except Exception as e:
        log.exception(f"Error getting workflow templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/{execution_id}/logs", response_model=List[WorkflowExecutionLog], summary="获取执行日志")
async def get_execution_logs(
    execution_id: str,
    user=Depends(get_verified_user)
):
    """
    获取工作流执行的详细日志。
    
    Args:
        execution_id (str): 执行ID
        user: 已认证的用户对象
        
    Returns:
        List[WorkflowExecutionLog]: 执行日志列表
        
    Raises:
        HTTPException: 404 - 执行不存在或无权限
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 简化版本：返回模拟日志数据
        # 实际实现中应该从数据库查询执行日志
        
        mock_logs = [
            WorkflowExecutionLog(
                execution_id=execution_id,
                step_name="analyze_requirements",
                status="completed",
                timestamp=int(time.time()) - 300,
                duration=45,
                input_data={"topic": "AI技术发展"},
                output_data={"analysis": "需求分析完成"}
            ),
            WorkflowExecutionLog(
                execution_id=execution_id,
                step_name="generate_content",
                status="running",
                timestamp=int(time.time()) - 255,
                input_data={"requirements": "基于分析结果生成内容"}
            )
        ]
        
        return mock_logs
        
    except Exception as e:
        log.exception(f"Error getting execution logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 辅助函数
############################

async def _execute_workflow_async(
    execution_id: str, 
    workflow_id: str, 
    workflow_info: Dict[str, Any], 
    input_data: Dict[str, Any], 
    user_id: str
):
    """
    异步执行工作流的辅助函数。
    
    这是一个简化的实现，实际应该调用真实的工作流引擎。
    """
    try:
        import asyncio
        
        steps = workflow_info["steps"]
        total_steps = len(steps)
        
        # 模拟步骤执行
        for i, step in enumerate(steps):
            # 模拟步骤执行时间
            await asyncio.sleep(30)  # 每步30秒
            
            progress = int((i + 1) / total_steps * 100)
            
            # 通过WebSocket通知进度
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    "hsai_response",  # 合并到核心事件中
                    {
                        "type": "hsai_response",
                        "subtype": "workflow_progress",  # 添加子类型用于区分原始事件
                        "execution_id": execution_id,
                        "workflow_id": workflow_id,
                        "progress": progress,
                        "current_step": step,
                        "completed_steps": i + 1,
                        "user_id": user_id
                    },
                    to=user_id
                )
        
        # 工作流完成
        completion_time = int(time.time())
        
        # 通知完成
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_response",  # 合并到核心事件中
                {
                    "type": "hsai_response",
                    "subtype": "workflow_completed",  # 添加子类型用于区分原始事件
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "status": "completed",
                    "end_time": completion_time,
                    "output_data": {"result": "工作流执行完成"},
                    "user_id": user_id
                },
                to=user_id
            )
        
    except Exception as e:
        log.exception(f"Error in async workflow execution: {e}")
        
        # 通知失败
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_error",  # 合并到核心事件中
                {
                    "type": "hsai_error",
                    "subtype": "workflow_failed",  # 添加子类型用于区分原始事件
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "status": "failed",
                    "error_message": str(e),
                    "user_id": user_id
                },
                to=user_id
            )