"""
智能工作流选择器
基于消息内容和场景规则匹配合适的工作流
"""

import re
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import jieba
import jieba.analyse
from .n8n_workflow_manager import WorkflowConfig, WorkflowType, workflow_manager

log = logging.getLogger(__name__)

class MessageIntent(str, Enum):
    """消息意图枚举"""
    VIDEO_CREATION = "video_creation"
    COMPANY_ANALYSIS = "company_analysis"
    CONTENT_LEARNING = "content_learning"
    DATA_ANALYSIS = "data_analysis"
    GENERAL_CHAT = "general_chat"

@dataclass
class SelectionContext:
    """工作流选择上下文"""
    message: str
    user_id: str
    session_id: str
    business_name: Optional[str] = None
    previous_messages: List[str] = None
    user_preferences: Dict[str, Any] = None
    
class WorkflowSelector:
    """智能工作流选择器"""
    
    def __init__(self):
        # 初始化jieba分词
        jieba.initialize()
        
        # 意图识别规则
        self.intent_patterns = {
            MessageIntent.VIDEO_CREATION: [
                r'(视频|短视频|抖音|tiktok|创作|拍摄|脚本|文案|发布)',
                r'(制作.*视频|生成.*视频|创建.*视频)',
                r'(爆款.*文案|热门.*内容|病毒.*视频)',
                r'(产品.*推广|营销.*视频|广告.*创意)'
            ],
            MessageIntent.COMPANY_ANALYSIS: [
                r'(公司|企业|竞品|对手|市场|行业)',
                r'(分析.*公司|调研.*企业|了解.*竞品)',
                r'(作战.*地图|竞争.*分析|市场.*调研)',
                r'(企业.*信息|公司.*背景|行业.*报告)'
            ],
            MessageIntent.CONTENT_LEARNING: [
                r'(爆款|热门|趋势|流行|病毒)',
                r'(学习.*内容|分析.*热门|研究.*爆款)',
                r'(内容.*策略|创意.*灵感|热点.*追踪)',
                r'(流量.*密码|传播.*规律|用户.*喜好)'
            ],
            MessageIntent.DATA_ANALYSIS: [
                r'(数据|统计|分析|报告|指标)',
                r'(爬取.*数据|收集.*信息|获取.*内容)',
                r'(关键词.*分析|标签.*提取|文本.*挖掘)',
                r'(用户.*行为|内容.*表现|传播.*效果)'
            ]
        }
        
        # 关键词权重配置
        self.keyword_weights = {
            # 视频创作相关
            '视频': 3, '短视频': 3, '抖音': 3, 'tiktok': 3,
            '创作': 2, '拍摄': 2, '脚本': 2, '文案': 2,
            '发布': 2, '制作': 2, '生成': 2,
            
            # 公司分析相关
            '公司': 3, '企业': 3, '竞品': 3, '对手': 3,
            '市场': 2, '行业': 2, '分析': 2, '调研': 2,
            '作战': 2, '地图': 2, '竞争': 2,
            
            # 内容学习相关
            '爆款': 3, '热门': 3, '趋势': 3, '流行': 2,
            '病毒': 2, '学习': 2, '策略': 2, '灵感': 2,
            
            # 数据分析相关
            '数据': 3, '统计': 2, '报告': 2, '指标': 2,
            '爬取': 3, '收集': 2, '获取': 2, '挖掘': 2
        }
        
    async def select_workflow(self, context: SelectionContext) -> Optional[WorkflowConfig]:
        """选择最适合的工作流"""
        try:
            log.info(f"Selecting workflow for message: {context.message[:50]}...")
            
            # 1. 意图识别
            intent = self._detect_intent(context.message)
            log.info(f"Detected intent: {intent}")
            
            # 2. 关键词提取和分析
            keywords = self._extract_keywords(context.message)
            log.info(f"Extracted keywords: {keywords}")
            
            # 3. 基于意图和关键词匹配工作流
            candidate_workflows = await self._match_workflows(intent, keywords, context)
            
            if not candidate_workflows:
                log.warning("No matching workflows found")
                return None
                
            # 4. 选择最佳工作流
            best_workflow = self._select_best_workflow(candidate_workflows, context)
            log.info(f"Selected workflow: {best_workflow.name} ({best_workflow.type})")
            
            return best_workflow
            
        except Exception as e:
            log.error(f"Error selecting workflow: {e}")
            return None
            
    def _detect_intent(self, message: str) -> MessageIntent:
        """检测消息意图"""
        message_lower = message.lower()
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, message_lower)
                score += len(matches) * 2  # 每个匹配得2分
                
            intent_scores[intent] = score
            
        # 返回得分最高的意图
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0:
                return best_intent
                
        return MessageIntent.GENERAL_CHAT
        
    def _extract_keywords(self, message: str) -> List[str]:
        """提取关键词"""
        try:
            # 使用jieba提取关键词
            keywords = jieba.analyse.extract_tags(message, topK=10, withWeight=False)
            
            # 过滤和增强关键词
            enhanced_keywords = []
            for keyword in keywords:
                if len(keyword) > 1:  # 过滤单字符
                    enhanced_keywords.append(keyword)
                    
            # 添加手动识别的重要词汇
            for word, weight in self.keyword_weights.items():
                if word in message and word not in enhanced_keywords:
                    enhanced_keywords.append(word)
                    
            return enhanced_keywords[:15]  # 限制关键词数量
            
        except Exception as e:
            log.error(f"Error extracting keywords: {e}")
            return []
            
    async def _match_workflows(self, intent: MessageIntent, keywords: List[str], 
                             context: SelectionContext) -> List[Tuple[WorkflowConfig, float]]:
        """匹配工作流并计算匹配度"""
        all_workflows = workflow_manager.get_all_workflows()
        matched_workflows = []
        
        for workflow in all_workflows:
            if not workflow.enabled:
                continue
                
            score = self._calculate_match_score(workflow, intent, keywords, context)
            if score > 0:
                matched_workflows.append((workflow, score))
                
        # 按匹配度排序
        matched_workflows.sort(key=lambda x: x[1], reverse=True)
        return matched_workflows
        
    def _calculate_match_score(self, workflow: WorkflowConfig, intent: MessageIntent,
                             keywords: List[str], context: SelectionContext) -> float:
        """计算工作流匹配度"""
        score = 0.0
        
        # 1. 基于意图的匹配
        intent_mapping = {
            MessageIntent.VIDEO_CREATION: [WorkflowType.MAIN],
            MessageIntent.COMPANY_ANALYSIS: [WorkflowType.COMPANY_INFO],
            MessageIntent.CONTENT_LEARNING: [WorkflowType.VIRAL_LEARNING],
            MessageIntent.DATA_ANALYSIS: [WorkflowType.VIDEO_CRAWL]
        }
        
        if workflow.type in intent_mapping.get(intent, []):
            score += 10.0  # 意图匹配得高分
            
        # 2. 关键词匹配
        keyword_matches = 0
        for keyword in keywords:
            for wf_keyword in workflow.keywords:
                if keyword.lower() in wf_keyword.lower() or wf_keyword.lower() in keyword.lower():
                    weight = self.keyword_weights.get(keyword, 1)
                    score += weight
                    keyword_matches += 1
                    
        # 3. 关键词匹配度加成
        if keyword_matches > 0:
            match_ratio = keyword_matches / len(workflow.keywords)
            score += match_ratio * 5.0
            
        # 4. 工作流优先级
        score += workflow.priority
        
        # 5. 上下文相关性（如果有历史消息）
        if context.previous_messages:
            context_score = self._calculate_context_relevance(workflow, context.previous_messages)
            score += context_score
            
        return score
        
    def _calculate_context_relevance(self, workflow: WorkflowConfig, 
                                   previous_messages: List[str]) -> float:
        """计算上下文相关性"""
        relevance_score = 0.0
        
        # 分析最近几条消息的主题连续性
        recent_keywords = []
        for msg in previous_messages[-3:]:  # 只看最近3条消息
            msg_keywords = self._extract_keywords(msg)
            recent_keywords.extend(msg_keywords)
            
        # 计算与当前工作流的关键词重叠度
        overlap_count = 0
        for keyword in recent_keywords:
            for wf_keyword in workflow.keywords:
                if keyword.lower() in wf_keyword.lower():
                    overlap_count += 1
                    
        if recent_keywords:
            overlap_ratio = overlap_count / len(recent_keywords)
            relevance_score = overlap_ratio * 3.0
            
        return relevance_score
        
    def _select_best_workflow(self, candidates: List[Tuple[WorkflowConfig, float]],
                            context: SelectionContext) -> WorkflowConfig:
        """从候选工作流中选择最佳的"""
        if not candidates:
            return None
            
        # 如果最高分明显高于其他候选者，直接选择
        best_candidate = candidates[0]
        if len(candidates) == 1 or best_candidate[1] > candidates[1][1] * 1.5:
            return best_candidate[0]
            
        # 如果分数接近，考虑其他因素
        top_candidates = [c for c in candidates if c[1] >= best_candidate[1] * 0.8]
        
        # 优先选择主工作流（如果在候选中）
        for workflow, score in top_candidates:
            if workflow.type == WorkflowType.MAIN:
                return workflow
                
        # 否则返回得分最高的
        return best_candidate[0]
        
    def get_selection_explanation(self, workflow: WorkflowConfig, 
                                context: SelectionContext) -> Dict[str, Any]:
        """获取选择解释"""
        intent = self._detect_intent(context.message)
        keywords = self._extract_keywords(context.message)
        
        return {
            "selected_workflow": {
                "id": workflow.id,
                "name": workflow.name,
                "type": workflow.type.value,
                "description": workflow.description
            },
            "selection_reason": {
                "detected_intent": intent.value,
                "extracted_keywords": keywords,
                "matching_keywords": [kw for kw in keywords if any(kw.lower() in wf_kw.lower() for wf_kw in workflow.keywords)],
                "confidence_score": self._calculate_match_score(workflow, intent, keywords, context)
            },
            "context": {
                "message_length": len(context.message),
                "has_previous_context": bool(context.previous_messages),
                "business_context": context.business_name
            }
        }

# 全局工作流选择器实例
workflow_selector = WorkflowSelector()