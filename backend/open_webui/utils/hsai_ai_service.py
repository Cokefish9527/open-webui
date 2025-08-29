import logging
import json
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from open_webui.models.hsai_tasks import HSAITasks, HSAITaskForm, HSAITaskStatus, HSAITaskType
from open_webui.models.hsai_materials import HSAIMaterials
from open_webui.utils.chat import generate_chat_completion

log = logging.getLogger(__name__)


class HSAIAIService:
    """HSAI AI服务类，提供AI驱动的内容生成和分析功能"""
    
    def __init__(self):
        self.content_generation_prompts = {
            "video_script": """
你是一个专业的短视频脚本创作专家。请根据以下信息生成一个吸引人的短视频脚本：

产品/服务：{product_name}
目标受众：{target_audience}
关键卖点：{key_points}
视频时长：{duration}秒
风格要求：{style_requirements}

请生成一个结构化的短视频脚本，包含：
1. 开场引人注目的话题或问题（3-5秒）
2. 产品/服务展示和核心卖点（主体部分）
3. 强有力的行动号召（最后3-5秒）

要求：
- 语言简洁有力，符合短视频节奏
- 突出产品优势和用户价值
- 包含适当的情感元素
- 提供镜头建议和视觉提示

请以JSON格式返回，包含以下字段：
{
  "title": "视频标题",
  "script_segments": [
    {
      "time_range": "0-5秒",
      "content": "脚本内容",
      "visual_hint": "视觉提示",
      "emotion": "情感表达"
    }
  ],
  "call_to_action": "行动号召",
  "tags": ["相关标签"],
  "estimated_engagement": "预期互动效果分析"
}
""",
            
            "product_analysis": """
你是一个专业的产品分析师。请对以下产品进行深度分析，为短视频营销提供策略建议：

产品信息：{product_info}
市场背景：{market_context}
竞争环境：{competition_info}

请从以下维度进行分析：
1. 产品核心价值和差异化优势
2. 目标用户画像和痛点分析
3. 最佳传播渠道和平台选择
4. 内容创作方向和主题建议
5. 营销策略和时机建议

请以JSON格式返回分析结果：
{
  "product_strengths": ["核心优势列表"],
  "target_audience": {
    "primary": "主要受众",
    "demographics": "人群特征",
    "pain_points": ["痛点列表"]
  },
  "content_strategies": [
    {
      "theme": "内容主题",
      "approach": "创作方法",
      "platforms": ["适合平台"],
      "success_metrics": "成功指标"
    }
  ],
  "recommendations": ["策略建议"]
}
""",
            
            "material_optimization": """
你是一个专业的多媒体内容优化专家。请分析以下素材并提供优化建议：

素材类型：{material_type}
当前描述：{current_description}
文件信息：{file_info}
使用场景：{usage_context}

请提供以下优化建议：
1. 内容描述优化
2. 关键词标签建议
3. 使用场景扩展
4. 组合搭配建议
5. 技术优化建议

返回JSON格式：
{
  "optimized_description": "优化后的描述",
  "suggested_tags": ["建议标签"],
  "usage_scenarios": ["使用场景"],
  "combination_suggestions": ["组合建议"],
  "technical_improvements": ["技术优化建议"],
  "seo_keywords": ["SEO关键词"]
}
"""
        }
    
    async def generate_video_script(
        self, 
        user_id: str,
        product_name: str,
        target_audience: str,
        key_points: List[str],
        duration: int = 60,
        style_requirements: str = "专业、有趣、易懂"
    ) -> Dict[str, Any]:
        """生成视频脚本"""
        try:
            # 创建任务记录
            task = await self._create_ai_task(
                user_id=user_id,
                title=f"生成视频脚本：{product_name}",
                task_type=HSAITaskType.CONTENT_ANALYSIS,
                inputs={
                    "product_name": product_name,
                    "target_audience": target_audience,
                    "key_points": key_points,
                    "duration": duration,
                    "style_requirements": style_requirements
                }
            )
            
            if not task:
                raise Exception("Failed to create task")
            
            # 更新任务状态为进行中
            HSAITasks.update_task_by_id(task.id, {"status": HSAITaskStatus.IN_PROGRESS})
            
            # 生成prompt
            prompt = self.content_generation_prompts["video_script"].format(
                product_name=product_name,
                target_audience=target_audience,
                key_points=", ".join(key_points),
                duration=duration,
                style_requirements=style_requirements
            )
            
            # 调用AI生成内容
            response = await self._call_ai_completion(prompt)
            
            # 解析响应
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # 如果不是有效JSON，作为文本处理
                result = {
                    "title": f"{product_name}营销视频脚本",
                    "content": response,
                    "generated_at": datetime.now().isoformat()
                }
            
            # 更新任务结果
            HSAITasks.update_task_by_id(task.id, {
                "status": HSAITaskStatus.COMPLETED,
                "outputs": result,
                "progress": 100
            })
            
            return {
                "task_id": task.id,
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            log.error(f"Error generating video script: {e}")
            if 'task' in locals():
                HSAITasks.update_task_by_id(task.id, {
                    "status": HSAITaskStatus.FAILED,
                    "error_message": str(e)
                })
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def analyze_product(
        self,
        user_id: str,
        product_info: str,
        market_context: str = "",
        competition_info: str = ""
    ) -> Dict[str, Any]:
        """产品分析"""
        try:
            # 创建任务记录
            task = await self._create_ai_task(
                user_id=user_id,
                title="产品市场分析",
                task_type=HSAITaskType.CONTENT_ANALYSIS,
                inputs={
                    "product_info": product_info,
                    "market_context": market_context,
                    "competition_info": competition_info
                }
            )
            
            if not task:
                raise Exception("Failed to create task")
            
            HSAITasks.update_task_by_id(task.id, {"status": HSAITaskStatus.IN_PROGRESS})
            
            # 生成prompt
            prompt = self.content_generation_prompts["product_analysis"].format(
                product_info=product_info,
                market_context=market_context or "暂无市场背景信息",
                competition_info=competition_info or "暂无竞争信息"
            )
            
            # 调用AI生成分析
            response = await self._call_ai_completion(prompt)
            
            # 解析响应
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                result = {
                    "analysis": response,
                    "generated_at": datetime.now().isoformat()
                }
            
            # 更新任务结果
            HSAITasks.update_task_by_id(task.id, {
                "status": HSAITaskStatus.COMPLETED,
                "outputs": result,
                "progress": 100
            })
            
            return {
                "task_id": task.id,
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            log.error(f"Error analyzing product: {e}")
            if 'task' in locals():
                HSAITasks.update_task_by_id(task.id, {
                    "status": HSAITaskStatus.FAILED,
                    "error_message": str(e)
                })
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def optimize_material(
        self,
        user_id: str,
        material_id: str,
        usage_context: str = ""
    ) -> Dict[str, Any]:
        """优化素材描述和标签"""
        try:
            # 获取素材信息
            material = HSAIMaterials.get_material_by_id(material_id)
            if not material:
                raise Exception("Material not found")
            
            # 创建任务记录
            task = await self._create_ai_task(
                user_id=user_id,
                title=f"优化素材：{material.name}",
                task_type=HSAITaskType.MATERIAL_PROCESSING,
                inputs={
                    "material_id": material_id,
                    "current_description": material.description,
                    "material_type": material.material_type,
                    "usage_context": usage_context
                }
            )
            
            if not task:
                raise Exception("Failed to create task")
            
            HSAITasks.update_task_by_id(task.id, {"status": HSAITaskStatus.IN_PROGRESS})
            
            # 生成prompt
            prompt = self.content_generation_prompts["material_optimization"].format(
                material_type=material.material_type,
                current_description=material.description or "暂无描述",
                file_info=f"文件类型: {material.mime_type}, 大小: {material.file_size}字节",
                usage_context=usage_context or "通用场景"
            )
            
            # 调用AI优化
            response = await self._call_ai_completion(prompt)
            
            # 解析响应
            try:
                result = json.loads(response)
                
                # 应用优化建议到素材
                update_data = {}
                if result.get("optimized_description"):
                    update_data["description"] = result["optimized_description"]
                
                if result.get("suggested_tags"):
                    update_data["tags"] = result["suggested_tags"]
                
                if result.get("seo_keywords"):
                    if not material.metadata:
                        material.metadata = {}
                    material.metadata["seo_keywords"] = result["seo_keywords"]
                    update_data["metadata"] = material.metadata
                
                # 更新素材
                if update_data:
                    HSAIMaterials.update_material_by_id(material_id, update_data)
                
            except json.JSONDecodeError:
                result = {
                    "optimization_suggestions": response,
                    "generated_at": datetime.now().isoformat()
                }
            
            # 更新任务结果
            HSAITasks.update_task_by_id(task.id, {
                "status": HSAITaskStatus.COMPLETED,
                "outputs": result,
                "progress": 100
            })
            
            return {
                "task_id": task.id,
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            log.error(f"Error optimizing material: {e}")
            if 'task' in locals():
                HSAITasks.update_task_by_id(task.id, {
                    "status": HSAITaskStatus.FAILED,
                    "error_message": str(e)
                })
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def generate_content_ideas(
        self,
        user_id: str,
        industry: str,
        target_audience: str,
        content_type: str = "video",
        count: int = 5
    ) -> Dict[str, Any]:
        """生成内容创意"""
        try:
            # 创建任务记录
            task = await self._create_ai_task(
                user_id=user_id,
                title=f"生成{content_type}内容创意",
                task_type=HSAITaskType.CONTENT_ANALYSIS,
                inputs={
                    "industry": industry,
                    "target_audience": target_audience,
                    "content_type": content_type,
                    "count": count
                }
            )
            
            if not task:
                raise Exception("Failed to create task")
            
            HSAITasks.update_task_by_id(task.id, {"status": HSAITaskStatus.IN_PROGRESS})
            
            # 生成创意prompt
            prompt = f"""
你是一个专业的内容创意策划师。请为{industry}行业生成{count}个{content_type}内容创意。

目标受众：{target_audience}
内容类型：{content_type}

请为每个创意提供：
1. 标题/主题
2. 核心概念
3. 执行方法
4. 预期效果
5. 适合平台

返回JSON格式：
{{
  "ideas": [
    {{
      "title": "创意标题",
      "concept": "核心概念",
      "execution": "执行方法",
      "expected_outcome": "预期效果",
      "platforms": ["适合平台"],
      "difficulty": "制作难度",
      "trending_potential": "流行潜力评分"
    }}
  ],
  "industry_insights": "行业洞察",
  "trending_topics": ["当前热门话题"]
}}
"""
            
            # 调用AI生成创意
            response = await self._call_ai_completion(prompt)
            
            # 解析响应
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                result = {
                    "ideas": response,
                    "generated_at": datetime.now().isoformat()
                }
            
            # 更新任务结果
            HSAITasks.update_task_by_id(task.id, {
                "status": HSAITaskStatus.COMPLETED,
                "outputs": result,
                "progress": 100
            })
            
            return {
                "task_id": task.id,
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            log.error(f"Error generating content ideas: {e}")
            if 'task' in locals():
                HSAITasks.update_task_by_id(task.id, {
                    "status": HSAITaskStatus.FAILED,
                    "error_message": str(e)
                })
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _create_ai_task(
        self,
        user_id: str,
        title: str,
        task_type: str,
        inputs: Dict[str, Any]
    ) -> Optional[Any]:
        """创建AI任务记录"""
        try:
            task_form = HSAITaskForm(
                title=title,
                description=f"AI生成任务：{title}",
                task_type=task_type,
                inputs=inputs,
                priority=1  # AI任务优先级较高
            )
            
            return HSAITasks.insert_new_task(user_id, task_form)
        except Exception as e:
            log.error(f"Error creating AI task: {e}")
            return None
    
    async def _call_ai_completion(self, prompt: str) -> str:
        """调用AI生成API"""
        try:
            # 构造AI请求
            messages = [
                {
                    "role": "system",
                    "content": "你是HSAI系统的AI助手，专门协助用户进行短视频内容创作和营销策划。请提供专业、实用的建议和内容。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # 调用OpenWebUI的chat completion API
            response = await generate_chat_completion(
                messages=messages,
                model="",  # 使用默认模型
                stream=False
            )
            
            if response and "choices" in response:
                return response["choices"][0]["message"]["content"]
            else:
                return "AI生成响应格式错误"
                
        except Exception as e:
            log.error(f"Error calling AI completion: {e}")
            return f"AI生成过程中发生错误：{str(e)}"


# 全局AI服务实例
hsai_ai_service = HSAIAIService()