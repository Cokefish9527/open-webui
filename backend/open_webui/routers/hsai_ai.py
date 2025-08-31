import logging
import time
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from open_webui.utils.auth import get_verified_user
from open_webui.models.users import Users
from open_webui.models.hsai_tasks import HSAITasks, HSAITaskForm
from open_webui.socket.main import get_event_emitter
from ..constants import ERROR_MESSAGES
from ..env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

####################
# Request Models
####################

class VideoScriptRequest(BaseModel):
    product_name: str = Field(..., description="产品或服务名称")
    target_audience: str = Field(..., description="目标受众描述")
    key_points: List[str] = Field(..., description="关键卖点列表")
    duration: int = Field(60, description="目标视频时长（秒）")
    style_requirements: str = Field("专业、有趣、易懂", description="脚本风格要求")

class ProductAnalysisRequest(BaseModel):
    product_info: str = Field(..., description="产品详细信息")
    market_context: str = Field("", description="市场背景信息")
    competition_info: str = Field("", description="主要竞争对手与对比信息")

class MaterialOptimizationRequest(BaseModel):
    material_id: str = Field(..., description="要优化的素材ID")
    usage_context: str = Field("", description="素材使用场景描述")

class ContentIdeasRequest(BaseModel):
    industry: str = Field(..., description="所属行业")
    target_audience: str = Field(..., description="目标受众")
    content_type: str = Field("video", description="内容类型")
    count: int = Field(5, description="生成创意数量")

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文参数")
    task_type: Optional[str] = Field("general", description="任务类型")

####################
# Response Models
####################

class AITaskResponse(BaseModel):
    """AI任务统一响应模型"""
    success: bool
    task_id: str
    status: str  # pending, running, completed, failed
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

####################
# 核心AI服务接口（集成任务系统）
####################

@router.post("/generate-video-script", response_model=AITaskResponse, summary="生成视频脚本（任务集成）")
async def generate_video_script_task(
    request: VideoScriptRequest,
    user=Depends(get_verified_user)
):
    """
    生成视频脚本（集成任务系统）
    
    基于产品信息和目标受众，生成适合的视频脚本内容。
    自动创建任务并跟踪执行状态。
    
    Args:
        request: 视频脚本生成请求
        user: 已认证的用户对象
        
    Returns:
        AITaskResponse: 包含任务ID、状态和结果的统一响应
    """
    try:
        # 创建任务记录
        task_form = HSAITaskForm(
            title=f"生成视频脚本: {request.product_name}",
            task_type="video_script_generation",
            description=f"为{request.product_name}生成{request.duration}秒视频脚本",
            priority=2,  # medium priority
            config={
                "product_name": request.product_name,
                "target_audience": request.target_audience,
                "key_points": request.key_points,
                "duration": request.duration,
                "style_requirements": request.style_requirements
            }
        )
        
        task = HSAITasks.insert_new_task(user.id, task_form)
        if not task:
            raise HTTPException(status_code=500, detail="任务创建失败")
        
        # 更新任务状态为运行中
        HSAITasks.update_task_by_id(task.id, {
            "status": "running",
            "started_at": int(time.time()),
            "updated_at": int(time.time())
        })
        
        # 通过WebSocket通知任务开始
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_task_started",
                {
                    "task_id": task.id,
                    "task_type": "video_script_generation",
                    "user_id": user.id
                },
                to=user.id
            )
        
        # 异步执行AI服务（简化版本：模拟AI生成）
        asyncio.create_task(_execute_video_script_generation(task.id, request, user.id))
        
        return AITaskResponse(
            success=True,
            task_id=task.id,
            status="running",
            message="视频脚本生成任务已启动",
            data={"estimated_duration": 30}  # 预估30秒完成
        )
        
    except Exception as e:
        log.exception(f"Error in video script generation task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"视频脚本生成任务失败: {str(e)}"
        )

@router.post("/analyze-product", response_model=AITaskResponse, summary="产品市场分析（任务集成）")
async def analyze_product_task(
    request: ProductAnalysisRequest,
    user=Depends(get_verified_user)
):
    """
    产品市场分析（集成任务系统）
    
    分析产品定位、竞争优势与营销策略建议。
    自动创建任务并跟踪执行状态。
    """
    try:
        # 创建任务记录
        task_form = HSAITaskForm(
            title=f"产品市场分析",
            task_type="product_analysis",
            description="分析产品定位、竞争优势与营销策略",
            priority=2,  # medium priority
            config={
                "product_info": request.product_info,
                "market_context": request.market_context,
                "competition_info": request.competition_info
            }
        )
        
        task = HSAITasks.insert_new_task(user.id, task_form)
        if not task:
            raise HTTPException(status_code=500, detail="任务创建失败")
        
        # 更新任务状态为运行中
        HSAITasks.update_task_by_id(task.id, {
            "status": "running",
            "started_at": int(time.time()),
            "updated_at": int(time.time())
        })
        
        # 通知任务开始
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_task_started",
                {
                    "task_id": task.id,
                    "task_type": "product_analysis",
                    "user_id": user.id
                },
                to=user.id
            )
        
        # 异步执行分析
        asyncio.create_task(_execute_product_analysis(task.id, request, user.id))
        
        return AITaskResponse(
            success=True,
            task_id=task.id,
            status="running",
            message="产品分析任务已启动",
            data={"estimated_duration": 45}
        )
        
    except Exception as e:
        log.exception(f"Error in product analysis task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"产品分析任务失败: {str(e)}"
        )

@router.post("/generate-content-ideas", response_model=AITaskResponse, summary="生成内容创意（任务集成）")
async def generate_content_ideas_task(
    request: ContentIdeasRequest,
    user=Depends(get_verified_user)
):
    """
    生成内容创意（集成任务系统）
    
    基于行业和目标受众生成内容创意。
    自动创建任务并跟踪执行状态。
    """
    try:
        # 创建任务记录
        task_form = HSAITaskForm(
            title=f"生成内容创意: {request.industry}",
            task_type="content_ideas_generation",
            description=f"为{request.industry}行业生成{request.count}个{request.content_type}创意",
            priority="medium",
            config={
                "industry": request.industry,
                "target_audience": request.target_audience,
                "content_type": request.content_type,
                "count": request.count
            }
        )
        
        task = HSAITasks.insert_new_task(user.id, task_form)
        if not task:
            raise HTTPException(status_code=500, detail="任务创建失败")
        
        # 更新任务状态为运行中
        HSAITasks.update_task_by_id(task.id, {
            "status": "running",
            "started_at": int(time.time()),
            "updated_at": int(time.time())
        })
        
        # 通知任务开始
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_task_started",
                {
                    "task_id": task.id,
                    "task_type": "content_ideas_generation",
                    "user_id": user.id
                },
                to=user.id
            )
        
        # 异步执行创意生成
        asyncio.create_task(_execute_content_ideas_generation(task.id, request, user.id))
        
        return AITaskResponse(
            success=True,
            task_id=task.id,
            status="running",
            message="内容创意生成任务已启动",
            data={"estimated_duration": 20}
        )
        
    except Exception as e:
        log.exception(f"Error in content ideas generation task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"内容创意生成任务失败: {str(e)}"
        )

@router.post("/optimize-material", response_model=AITaskResponse, summary="优化素材内容（任务集成）")
async def optimize_material_task(
    request: MaterialOptimizationRequest,
    user=Depends(get_verified_user)
):
    """
    优化素材内容（集成任务系统）
    
    基于使用场景优化素材描述和标签。
    自动创建任务并跟踪执行状态。
    """
    try:
        # 创建任务记录
        task_form = HSAITaskForm(
            title=f"优化素材: {request.material_id}",
            task_type="material_optimization",
            description="优化素材描述、标签和使用建议",
            priority=1,  # low priority
            config={
                "material_id": request.material_id,
                "usage_context": request.usage_context
            }
        )
        
        task = HSAITasks.insert_new_task(user.id, task_form)
        if not task:
            raise HTTPException(status_code=500, detail="任务创建失败")
        
        # 更新任务状态为运行中
        HSAITasks.update_task_by_id(task.id, {
            "status": "running",
            "started_at": int(time.time()),
            "updated_at": int(time.time())
        })
        
        # 异步执行优化
        asyncio.create_task(_execute_material_optimization(task.id, request, user.id))
        
        return AITaskResponse(
            success=True,
            task_id=task.id,
            status="running",
            message="素材优化任务已启动",
            data={"estimated_duration": 15}
        )
        
    except Exception as e:
        log.exception(f"Error in material optimization task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"素材优化任务失败: {str(e)}"
        )

@router.post("/chat", response_model=AITaskResponse, summary="HSAI智能对话（任务集成）")
async def hsai_chat_task(
    request: ChatRequest,
    user=Depends(get_verified_user)
):
    """
    HSAI智能对话（集成任务系统）
    
    智能理解用户意图，提供专业建议或执行相关任务。
    """
    try:
        # 创建任务记录
        task_form = HSAITaskForm(
            title=f"AI对话: {request.message[:50]}...",
            task_type="ai_chat",
            description="智能对话和意图理解",
            priority=3,  # high priority
            config={
                "message": request.message,
                "context": request.context or {},
                "task_type": request.task_type
            }
        )
        
        task = HSAITasks.insert_new_task(user.id, task_form)
        if not task:
            raise HTTPException(status_code=500, detail="任务创建失败")
        
        # 更新任务状态为运行中
        HSAITasks.update_task_by_id(task.id, {
            "status": "running",
            "started_at": int(time.time()),
            "updated_at": int(time.time())
        })
        
        # 异步执行对话处理
        asyncio.create_task(_execute_ai_chat(task.id, request, user.id))
        
        return AITaskResponse(
            success=True,
            task_id=task.id,
            status="running",
            message="AI对话处理中",
            data={"estimated_duration": 10}
        )
        
    except Exception as e:
        log.exception(f"Error in AI chat task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI对话任务失败: {str(e)}"
        )

####################
# 任务模板接口
####################

@router.get("/task-templates", summary="获取AI任务模板")
async def get_ai_task_templates(
    user=Depends(get_verified_user)
):
    """
    获取AI任务模板列表。
    
    返回所有可用的AI任务类型和对应的参数模板。
    """
    try:
        templates = [
            {
                "id": "video_script_generation",
                "name": "视频脚本生成",
                "description": "基于产品信息生成专业视频脚本",
                "icon": "video",
                "estimated_duration": 30,
                "fields": [
                    {"field": "product_name", "label": "产品名称", "type": "text", "required": True},
                    {"field": "target_audience", "label": "目标受众", "type": "text", "required": True},
                    {"field": "key_points", "label": "关键卖点", "type": "tags", "required": True},
                    {"field": "duration", "label": "视频时长(秒)", "type": "number", "default": 60},
                    {"field": "style_requirements", "label": "风格要求", "type": "text", "default": "专业、有趣、易懂"}
                ]
            },
            {
                "id": "product_analysis",
                "name": "产品市场分析",
                "description": "分析产品定位和竞争优势",
                "icon": "analytics",
                "estimated_duration": 45,
                "fields": [
                    {"field": "product_info", "label": "产品信息", "type": "textarea", "required": True},
                    {"field": "market_context", "label": "市场背景", "type": "textarea"},
                    {"field": "competition_info", "label": "竞争信息", "type": "textarea"}
                ]
            },
            {
                "id": "content_ideas_generation",
                "name": "内容创意生成",
                "description": "生成行业相关的内容创意",
                "icon": "lightbulb",
                "estimated_duration": 20,
                "fields": [
                    {"field": "industry", "label": "所属行业", "type": "text", "required": True},
                    {"field": "target_audience", "label": "目标受众", "type": "text", "required": True},
                    {"field": "content_type", "label": "内容类型", "type": "select", "options": ["video", "article", "social_post"], "default": "video"},
                    {"field": "count", "label": "生成数量", "type": "number", "default": 5}
                ]
            },
            {
                "id": "material_optimization",
                "name": "素材优化",
                "description": "优化素材描述和标签",
                "icon": "tune",
                "estimated_duration": 15,
                "fields": [
                    {"field": "material_id", "label": "素材ID", "type": "text", "required": True},
                    {"field": "usage_context", "label": "使用场景", "type": "textarea"}
                ]
            }
        ]
        
        return {"templates": templates}
        
    except Exception as e:
        log.exception(f"Error getting AI task templates: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT()
        )

####################
# 异步任务执行函数
####################

async def _execute_video_script_generation(task_id: str, request: VideoScriptRequest, user_id: str):
    """异步执行视频脚本生成"""
    try:
        # 模拟AI处理时间
        await asyncio.sleep(30)
        
        # 模拟生成结果
        result = {
            "script": f"""
开场（0-10秒）：
大家好！今天为您介绍{request.product_name}，专为{request.target_audience}设计的高端解决方案。

主体（10-{request.duration-10}秒）：
{request.product_name}具有以下突出优势：
""" + "\n".join([f"• {point}" for point in request.key_points]) + f"""

结尾（{request.duration-10}-{request.duration}秒）：
选择{request.product_name}，选择专业与品质。立即联系我们获取详细方案！
            """.strip(),
            "scenes": [
                {"order": 1, "content": "产品外观展示", "duration": 10},
                {"order": 2, "content": "功能特点演示", "duration": request.duration - 20},
                {"order": 3, "content": "联系方式展示", "duration": 10}
            ],
            "duration_estimate": request.duration,
            "suggestions": [
                "建议添加客户案例",
                "可以增加产品细节特写",
                "结尾可以添加优惠信息"
            ]
        }
        
        # 更新任务为完成状态
        HSAITasks.update_task_by_id(task_id, {
            "status": "completed",
            "completed_at": int(time.time()),
            "result": result,
            "progress": 100,
            "updated_at": int(time.time())
        })
        
        # 通知任务完成
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_task_completed",
                {
                    "task_id": task_id,
                    "result": result,
                    "user_id": user_id
                },
                to=user_id
            )
        
    except Exception as e:
        # 更新任务为失败状态
        HSAITasks.update_task_by_id(task_id, {
            "status": "failed",
            "error_message": str(e),
            "updated_at": int(time.time())
        })
        
        # 通知任务失败
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_task_failed",
                {
                    "task_id": task_id,
                    "error": str(e),
                    "user_id": user_id
                },
                to=user_id
            )

async def _execute_product_analysis(task_id: str, request: ProductAnalysisRequest, user_id: str):
    """异步执行产品分析"""
    try:
        await asyncio.sleep(45)
        
        result = {
            "market_positioning": "高端工业设备，主打精度与稳定性",
            "target_audience": {
                "primary": ["制造业采购经理", "工厂技术负责人"],
                "secondary": ["设备代理商", "系统集成商"]
            },
            "competitive_advantages": [
                "技术领先，精度更高",
                "能耗低，运营成本优势",
                "稳定性强，故障率低",
                "服务网络完善"
            ],
            "marketing_strategies": [
                "技术展会参展",
                "客户案例视频制作",
                "行业媒体合作",
                "渠道伙伴培训"
            ],
            "swot_analysis": {
                "strengths": ["技术优势", "品牌知名度"],
                "weaknesses": ["价格较高", "市场覆盖有限"],
                "opportunities": ["市场需求增长", "政策支持"],
                "threats": ["竞争加剧", "原材料涨价"]
            },
            "recommendations": [
                "加强成本控制，提高价格竞争力",
                "扩大销售网络，增加市场覆盖",
                "加大研发投入，保持技术领先",
                "完善售后服务体系"
            ]
        }
        
        HSAITasks.update_task_by_id(task_id, {
            "status": "completed",
            "completed_at": int(time.time()),
            "result": result,
            "progress": 100,
            "updated_at": int(time.time())
        })
        
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_task_completed",
                {"task_id": task_id, "result": result, "user_id": user_id},
                to=user_id
            )
        
    except Exception as e:
        HSAITasks.update_task_by_id(task_id, {
            "status": "failed",
            "error_message": str(e),
            "updated_at": int(time.time())
        })

async def _execute_content_ideas_generation(task_id: str, request: ContentIdeasRequest, user_id: str):
    """异步执行内容创意生成"""
    try:
        await asyncio.sleep(20)
        
        ideas = []
        for i in range(request.count):
            ideas.append({
                "title": f"{request.industry}行业解决方案第{i+1}期",
                "description": f"针对{request.target_audience}的专业内容",
                "key_points": ["技术优势", "成本效益", "应用案例"],
                "suggested_format": request.content_type
            })
        
        result = {
            "ideas": ideas,
            "themes": [f"{request.industry}技术趋势", "行业最佳实践", "成功案例分享"],
            "trending_elements": ["数据可视化", "客户证言", "专家访谈"]
        }
        
        HSAITasks.update_task_by_id(task_id, {
            "status": "completed",
            "completed_at": int(time.time()),
            "result": result,
            "progress": 100,
            "updated_at": int(time.time())
        })
        
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_task_completed",
                {"task_id": task_id, "result": result, "user_id": user_id},
                to=user_id
            )
        
    except Exception as e:
        HSAITasks.update_task_by_id(task_id, {
            "status": "failed",
            "error_message": str(e),
            "updated_at": int(time.time())
        })

async def _execute_material_optimization(task_id: str, request: MaterialOptimizationRequest, user_id: str):
    """异步执行素材优化"""
    try:
        await asyncio.sleep(15)
        
        result = {
            "optimized_description": "经过AI优化的素材描述，更加精准和吸引人",
            "usage_suggestions": [
                "适合在LinkedIn发布",
                "可用于产品宣传册",
                "适合展会展示"
            ],
            "improvement_tips": [
                "增加数据支撑",
                "添加客户证言",
                "优化视觉效果"
            ],
            "suitable_scenarios": [
                "B2B营销",
                "品牌宣传",
                "产品介绍"
            ],
            "tags": ["专业", "可信", "高质量", "B2B"]
        }
        
        HSAITasks.update_task_by_id(task_id, {
            "status": "completed",
            "completed_at": int(time.time()),
            "result": result,
            "progress": 100,
            "updated_at": int(time.time())
        })
        
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_task_completed",
                {"task_id": task_id, "result": result, "user_id": user_id},
                to=user_id
            )
        
    except Exception as e:
        HSAITasks.update_task_by_id(task_id, {
            "status": "failed",
            "error_message": str(e),
            "updated_at": int(time.time())
        })

async def _execute_ai_chat(task_id: str, request: ChatRequest, user_id: str):
    """异步执行AI对话"""
    try:
        await asyncio.sleep(10)
        
        result = {
            "status": "success",
            "message": f"我理解您的需求：{request.message}。基于您的描述，我建议以下方案...",
            "suggestions": [
                {
                    "action": "create_video_script",
                    "title": "创建视频脚本",
                    "description": "基于您的需求生成专业视频脚本"
                },
                {
                    "action": "analyze_market",
                    "title": "市场分析",
                    "description": "深入分析产品市场定位"
                }
            ],
            "required_fields": []
        }
        
        HSAITasks.update_task_by_id(task_id, {
            "status": "completed",
            "completed_at": int(time.time()),
            "result": result,
            "progress": 100,
            "updated_at": int(time.time())
        })
        
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_task_completed",
                {"task_id": task_id, "result": result, "user_id": user_id},
                to=user_id
            )
        
    except Exception as e:
        HSAITasks.update_task_by_id(task_id, {
            "status": "failed",
            "error_message": str(e),
            "updated_at": int(time.time())
        })