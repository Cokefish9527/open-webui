import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from open_webui.utils.auth import get_verified_user
from open_webui.utils.hsai_ai_service import hsai_ai_service
from open_webui.models.users import Users

log = logging.getLogger(__name__)

router = APIRouter()

####################
# Request Models
####################


class VideoScriptRequest(BaseModel):
    product_name: str = Field(..., description="产品或服务名称", example="高速激光切割机")
    target_audience: str = Field(..., description="目标受众描述", example="外贸B2B采购经理")
    key_points: List[str] = Field(..., description="关键卖点列表", example=["高精度", "节能", "稳定性强"])
    duration: int = Field(60, description="目标视频时长（秒）", example=60)
    style_requirements: str = Field("专业、有趣、易懂", description="脚本风格要求", example="专业、可信、简洁")


class ProductAnalysisRequest(BaseModel):
    product_info: str = Field(..., description="产品详细信息", example="型号X100，适用于不锈钢切割，功率3kW")
    market_context: str = Field("", description="市场背景信息", example="目标市场为东南亚地区，价格敏感")
    competition_info: str = Field("", description="主要竞争对手与对比信息", example="竞品A价格低但精度不足")


class MaterialOptimizationRequest(BaseModel):
    material_id: str = Field(..., description="要优化的素材ID", example="mat_123456")
    usage_context: str = Field("", description="素材使用场景描述", example="用于LinkedIn品牌宣传")


class ContentIdeasRequest(BaseModel):
    industry: str = Field(..., description="所属行业", example="机械制造")
    target_audience: str = Field(..., description="目标受众", example="海外采购商")
    content_type: str = Field("video", description="内容类型", example="video")
    count: int = Field(5, description="生成创意数量", example=5)


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息", example="帮我生成一个关于X100激光切割机的30秒视频脚本")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文参数（根据不同任务类型包含不同键）", example={"product_name":"X100","target_audience":"采购经理"})
    task_type: Optional[str] = Field("general", description="任务类型", example="video_script")


####################
# Response Models (for Swagger)
####################

class VideoScriptResponse(BaseModel):
    script: str = Field(..., description="完整脚本文本", example="开场：产品介绍\
主体：功能展示\
结尾：行动号召")
    scenes: Optional[List[Dict[str, Any]]] = Field(None, description="分镜头脚本列表", example=[{"order":1,"content":"展示产品外观","duration":5}])
    duration_estimate: Optional[int] = Field(None, description="预估时长（秒）", example=60)
    suggestions: Optional[List[str]] = Field(None, description="优化建议", example=["突出价格优势","增加行动号召"])
    class Config:
        extra = "allow"

class ProductAnalysisResponse(BaseModel):
    market_positioning: Optional[str] = Field(None, description="市场定位分析", example="高端工业设备，主打精度与稳定性")
    target_audience: Optional[Dict[str, Any]] = Field(None, description="目标受众画像", example={"roles":["采购经理","工厂负责人"]})
    competitive_advantages: Optional[List[str]] = Field(None, description="竞争优势", example=["精度高","能耗低"])
    marketing_strategies: Optional[List[str]] = Field(None, description="营销策略建议", example=["案例视频推广","渠道合作"])
    swot_analysis: Optional[Dict[str, Any]] = Field(None, description="SWOT分析")
    recommendations: Optional[List[str]] = Field(None, description="具体建议")
    class Config:
        extra = "allow"

class MaterialOptimizationResponse(BaseModel):
    optimized_description: Optional[str] = Field(None, description="优化后的描述")
    usage_suggestions: Optional[List[str]] = Field(None, description="使用建议")
    improvement_tips: Optional[List[str]] = Field(None, description="改进建议")
    suitable_scenarios: Optional[List[str]] = Field(None, description="适用场景")
    tags: Optional[List[str]] = Field(None, description="推荐标签")
    class Config:
        extra = "allow"

class ContentIdeasIdea(BaseModel):
    title: str = Field(..., description="创意标题", example="3个理由：为什么选择X100激光切割机")
    description: Optional[str] = Field(None, description="创意描述")
    key_points: Optional[List[str]] = Field(None, description="关键点")
    suggested_format: Optional[str] = Field(None, description="建议格式", example="短视频")

class ContentIdeasResponse(BaseModel):
    ideas: List[ContentIdeasIdea] = Field(..., description="创意列表")
    themes: Optional[List[str]] = Field(None, description="相关主题")
    trending_elements: Optional[List[str]] = Field(None, description="热门元素")
    class Config:
        extra = "allow"

class ChatResponse(BaseModel):
    status: str = Field(..., description="状态", example="success")
    message: Optional[str] = Field(None, description="AI回复或提示信息")
    suggestions: Optional[List[Dict[str, Any]]] = Field(None, description="行动建议列表")
    required_fields: Optional[List[Dict[str, Any]]] = Field(None, description="缺失的必填字段提示")
    class Config:
        extra = "allow"

class TaskFieldModel(BaseModel):
    field: str = Field(..., description="字段名")
    label: str = Field(..., description="显示标签")
    type: str = Field(..., description="字段类型")
    required: Optional[bool] = Field(None, description="是否必填")
    default: Optional[Any] = Field(None, description="默认值")
    options: Optional[List[str]] = Field(None, description="可选项")

class TaskTemplateModel(BaseModel):
    id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    icon: Optional[str] = Field(None, description="图标")
    fields: List[TaskFieldModel] = Field(..., description="模板表单字段")

class TaskTemplatesResponse(BaseModel):
    templates: List[TaskTemplateModel] = Field(..., description="任务模板列表")

####################
# API Routes
####################


@router.post(
    "/generate-video-script",
    summary="生成视频脚本",
    description="基于产品信息和目标受众，使用AI生成专业的短视频脚本内容",
    response_model=VideoScriptResponse,
    responses={
        500: {"description": "AI服务调用失败", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
    },
)
async def generate_video_script(
    request: VideoScriptRequest,
    user=Depends(get_verified_user)
):
    """
    生成视频脚本。
    
    基于产品信息和目标受众，使用AI生成专业的短视频脚本内容。
    
    Args:
        request (VideoScriptRequest): 脚本生成请求
        - product_name: 产品或服务名称（必填）
        - target_audience: 目标受众描述（必填）
        - key_points: 关键卖点列表（必填）
        - duration: 视频时长（秒，默认60秒）
        - style_requirements: 风格要求（默认"专业、有趣、易懂"）
        user: 已认证的用户对象
        
    Returns:
        dict: 生成的脚本内容
        - script: 完整脚本文本
        - scenes: 分镜头脚本
        - duration_estimate: 预估时长
        - suggestions: 优化建议
        
    Raises:
        HTTPException: 500 - AI服务调用失败
        
    Note:
        - 脚本会根据指定时长进行优化
        - 包含开场、主体和结尾三个部分
        - 适合短视频平台的节奏和风格
    """
    try:
        result = await hsai_ai_service.generate_video_script(
            user_id=user.id,
            product_name=request.product_name,
            target_audience=request.target_audience,
            key_points=request.key_points,
            duration=request.duration,
            style_requirements=request.style_requirements
        )
        
        return result
        
    except Exception as e:
        log.error(f"Error in generate_video_script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/analyze-product",
    summary="产品市场分析",
    description="分析产品定位、竞争优势与营销策略建议",
    response_model=ProductAnalysisResponse,
    responses={
        500: {"description": "AI服务调用失败", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
    },
)
async def analyze_product(
    request: ProductAnalysisRequest,
    user=Depends(get_verified_user)
):
    """
    产品市场分析。
    
    使用AI深度分析产品的市场定位、竞争优势和营销策略建议。
    
    Args:
        request (ProductAnalysisRequest): 产品分析请求
        - product_info: 产品详细信息（必填）
        - market_context: 市场背景信息（可选）
        - competition_info: 竞争对手信息（可选）
        user: 已认证的用户对象
        
    Returns:
        dict: 分析结果
        - market_positioning: 市场定位分析
        - target_audience: 目标受众画像
        - competitive_advantages: 竞争优势
        - marketing_strategies: 营销策略建议
        - swot_analysis: SWOT分析
        - recommendations: 具体建议
        
    Raises:
        HTTPException: 500 - AI服务调用失败
        
    Note:
        - 分析结果基于提供的信息质量
        - 建议提供详细的产品和市场信息
        - 可用于制定营销策略和内容规划
    """
    try:
        result = await hsai_ai_service.analyze_product(
            user_id=user.id,
            product_info=request.product_info,
            market_context=request.market_context,
            competition_info=request.competition_info
        )
        
        return result
        
    except Exception as e:
        log.error(f"Error in analyze_product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/optimize-material",
    summary="优化素材内容",
    description="分析并优化素材，提供使用建议与改进方案",
    response_model=MaterialOptimizationResponse,
    responses={
        404: {"description": "素材不存在", "content": {"application/json": {"example": {"detail": "Not Found"}}}},
        500: {"description": "AI服务调用失败", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
    },
)
async def optimize_material(
    request: MaterialOptimizationRequest,
    user=Depends(get_verified_user)
):
    """
    优化素材内容。
    
    使用AI分析和优化现有素材，提供使用建议和改进方案。
    
    Args:
        request (MaterialOptimizationRequest): 素材优化请求
        - material_id: 要优化的素材ID（必填）
        - usage_context: 使用场景描述（可选）
        user: 已认证的用户对象
        
    Returns:
        dict: 优化结果
        - optimized_description: 优化后的描述
        - usage_suggestions: 使用建议
        - improvement_tips: 改进建议
        - suitable_scenarios: 适用场景
        - tags: 推荐标签
        
    Raises:
        HTTPException: 500 - AI服务调用失败或素材不存在
        
    Note:
        - 需要素材已上传到系统中
        - 优化建议基于素材类型和内容
        - 可用于提升素材的营销效果
    """
    try:
        result = await hsai_ai_service.optimize_material(
            user_id=user.id,
            material_id=request.material_id,
            usage_context=request.usage_context
        )
        
        return result
        
    except Exception as e:
        log.error(f"Error in optimize_material: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/generate-content-ideas",
    summary="生成内容创意",
    description="基于主题和要求生成多样化的内容创意",
    response_model=ContentIdeasResponse,
    responses={
        500: {"description": "AI服务调用失败", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
    },
)
async def generate_content_ideas(
    request: ContentIdeasRequest,
    user=Depends(get_verified_user)
):
    """
    生成内容创意。
    
    基于主题和要求，使用AI生成多样化的内容创意和灵感。
    
    Args:
        request (ContentIdeasRequest): 内容创意请求
        - topic: 主题或关键词（必填）
        - content_type: 内容类型（可选，如"短视频"、"图文"等）
        - count: 生成数量（可选，默认5个）
        user: 已认证的用户对象
        
    Returns:
        dict: 创意结果
        - ideas: 创意列表
          - title: 标题
          - description: 描述
          - key_points: 关键点
          - suggested_format: 建议格式
        - themes: 相关主题
        - trending_elements: 热门元素
        
    Raises:
        HTTPException: 500 - AI服务调用失败
        
    Note:
        - 创意基于当前热点和趋势
        - 适合各种内容平台和格式
        - 可用于内容规划和创作灵感
    """
    try:
        result = await hsai_ai_service.generate_content_ideas(
            user_id=user.id,
            industry=request.industry,
            target_audience=request.target_audience,
            content_type=request.content_type,
            count=request.count
        )
        
        return result
        
    except Exception as e:
        log.error(f"Error in generate_content_ideas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/chat",
    summary="HSAI 智能对话",
    description="支持视频脚本、产品分析、内容创意等任务的智能对话接口",
    response_model=ChatResponse,
    responses={
        500: {"description": "内部错误", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
    },
)
async def hsai_chat(
    request: ChatRequest,
    user=Depends(get_verified_user)
):
    """HSAI智能对话"""
    try:
        # 根据任务类型选择不同的处理方式
        if request.task_type == "video_script":
            # 如果是视频脚本相关，引导用户提供必要信息
            if not request.context or not all(k in request.context for k in ["product_name", "target_audience"]):
                return {
                    "status": "need_more_info",
                    "message": "为了生成更好的视频脚本，请提供以下信息：",
                    "required_fields": [
                        {"field": "product_name", "label": "产品/服务名称", "type": "text"},
                        {"field": "target_audience", "label": "目标受众", "type": "text"},
                        {"field": "key_points", "label": "关键卖点", "type": "array"},
                        {"field": "duration", "label": "视频时长(秒)", "type": "number", "default": 60},
                        {"field": "style_requirements", "label": "风格要求", "type": "text", "default": "专业、有趣、易懂"}
                    ]
                }
            else:
                # 信息完整，直接生成脚本
                result = await hsai_ai_service.generate_video_script(
                    user_id=user.id,
                    product_name=request.context["product_name"],
                    target_audience=request.context["target_audience"],
                    key_points=request.context.get("key_points", []),
                    duration=request.context.get("duration", 60),
                    style_requirements=request.context.get("style_requirements", "专业、有趣、易懂")
                )
                return result
        
        elif request.task_type == "product_analysis":
            if not request.context or "product_info" not in request.context:
                return {
                    "status": "need_more_info",
                    "message": "请提供产品信息进行分析：",
                    "required_fields": [
                        {"field": "product_info", "label": "产品信息", "type": "textarea"},
                        {"field": "market_context", "label": "市场背景", "type": "textarea", "optional": True},
                        {"field": "competition_info", "label": "竞争信息", "type": "textarea", "optional": True}
                    ]
                }
            else:
                result = await hsai_ai_service.analyze_product(
                    user_id=user.id,
                    product_info=request.context["product_info"],
                    market_context=request.context.get("market_context", ""),
                    competition_info=request.context.get("competition_info", "")
                )
                return result
        
        elif request.task_type == "content_ideas":
            if not request.context or not all(k in request.context for k in ["industry", "target_audience"]):
                return {
                    "status": "need_more_info",
                    "message": "请提供以下信息来生成内容创意：",
                    "required_fields": [
                        {"field": "industry", "label": "行业", "type": "text"},
                        {"field": "target_audience", "label": "目标受众", "type": "text"},
                        {"field": "content_type", "label": "内容类型", "type": "select", "options": ["video", "image", "text"], "default": "video"},
                        {"field": "count", "label": "创意数量", "type": "number", "default": 5}
                    ]
                }
            else:
                result = await hsai_ai_service.generate_content_ideas(
                    user_id=user.id,
                    industry=request.context["industry"],
                    target_audience=request.context["target_audience"],
                    content_type=request.context.get("content_type", "video"),
                    count=request.context.get("count", 5)
                )
                return result
        
        else:
            # 通用对话
            from open_webui.utils.hsai_ai_service import hsai_ai_service
            response = await hsai_ai_service._call_ai_completion(
                f"""
用户消息：{request.message}

请作为HSAI系统的AI助手回复用户。HSAI是一个AI短视频自动化获客系统，专注于帮助外贸企业创建营销视频。

你可以帮助用户：
1. 生成视频脚本
2. 分析产品市场定位
3. 优化素材内容
4. 提供内容创意
5. 解答营销策略问题

请简洁、专业地回复用户。
"""
            )
            
            return {
                "status": "success",
                "message": response,
                "suggestions": [
                    {"action": "generate_script", "label": "生成视频脚本"},
                    {"action": "analyze_product", "label": "产品分析"},
                    {"action": "content_ideas", "label": "内容创意"},
                    {"action": "optimize_material", "label": "优化素材"}
                ]
            }
        
    except Exception as e:
        log.error(f"Error in hsai_chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/task-templates",
    summary="获取AI任务模板",
    description="返回可用的AI任务模板及其表单字段定义",
    response_model=TaskTemplatesResponse,
)
async def get_task_templates(user=Depends(get_verified_user)):
    """获取AI任务模板"""
    return {
        "templates": [
            {
                "id": "video_script",
                "name": "视频脚本生成",
                "description": "为产品或服务生成专业的短视频脚本",
                "icon": "🎬",
                "fields": [
                    {"field": "product_name", "label": "产品/服务名称", "type": "text", "required": True},
                    {"field": "target_audience", "label": "目标受众", "type": "text", "required": True},
                    {"field": "key_points", "label": "关键卖点", "type": "array", "required": True},
                    {"field": "duration", "label": "视频时长(秒)", "type": "number", "default": 60},
                    {"field": "style_requirements", "label": "风格要求", "type": "text", "default": "专业、有趣、易懂"}
                ]
            },
            {
                "id": "product_analysis",
                "name": "产品市场分析",
                "description": "深度分析产品定位和市场策略",
                "icon": "📊",
                "fields": [
                    {"field": "product_info", "label": "产品信息", "type": "textarea", "required": True},
                    {"field": "market_context", "label": "市场背景", "type": "textarea"},
                    {"field": "competition_info", "label": "竞争信息", "type": "textarea"}
                ]
            },
            {
                "id": "content_ideas",
                "name": "内容创意生成",
                "description": "生成多样化的内容创意和主题",
                "icon": "💡",
                "fields": [
                    {"field": "industry", "label": "行业", "type": "text", "required": True},
                    {"field": "target_audience", "label": "目标受众", "type": "text", "required": True},
                    {"field": "content_type", "label": "内容类型", "type": "select", "options": ["video", "image", "text"], "default": "video"},
                    {"field": "count", "label": "创意数量", "type": "number", "default": 5}
                ]
            },
            {
                "id": "material_optimization",
                "name": "素材优化",
                "description": "优化素材描述和使用建议",
                "icon": "⚡",
                "fields": [
                    {"field": "material_id", "label": "素材ID", "type": "hidden", "required": True},
                    {"field": "usage_context", "label": "使用场景", "type": "text"}
                ]
            }
        ]
    }