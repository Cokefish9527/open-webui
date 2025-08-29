import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.utils.hsai_ai_service import hsai_ai_service
from open_webui.models.users import Users

log = logging.getLogger(__name__)

router = APIRouter()

####################
# Request Models
####################


class VideoScriptRequest(BaseModel):
    product_name: str
    target_audience: str
    key_points: List[str]
    duration: Optional[int] = 60
    style_requirements: Optional[str] = "专业、有趣、易懂"


class ProductAnalysisRequest(BaseModel):
    product_info: str
    market_context: Optional[str] = ""
    competition_info: Optional[str] = ""


class MaterialOptimizationRequest(BaseModel):
    material_id: str
    usage_context: Optional[str] = ""


class ContentIdeasRequest(BaseModel):
    industry: str
    target_audience: str
    content_type: Optional[str] = "video"
    count: Optional[int] = 5


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None
    task_type: Optional[str] = "general"


####################
# API Routes
####################


@router.post("/generate-video-script")
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


@router.post("/analyze-product")
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


@router.post("/optimize-material")
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


@router.post("/generate-content-ideas")
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


@router.post("/chat")
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


@router.get("/task-templates")
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