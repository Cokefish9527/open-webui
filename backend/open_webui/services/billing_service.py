import logging
import time
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.billing_config import BillingConfigs
from open_webui.models.api_usage_log import APIUsageLogs, APIUsageLogForm
from open_webui.models.hsai_tasks import HSAITasks
from open_webui.models.hsai_companies import Companies
from open_webui.models.credits import Credits, AddCreditForm, SetCreditFormDetail
from open_webui.services.ops_dashboard_ingestor import enqueue_user_activity_event

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class BillingService:
    """计费服务类"""
    
    def __init__(self):
        self.billing_configs = BillingConfigs
        self.api_usage_logs = APIUsageLogs
        self.hsai_tasks = HSAITasks
        self.companies = Companies
        self.credits = Credits

    def calculate_resource_cost(self, resource_type: str, usage: dict) -> Decimal:
        """计算资源使用费用"""
        # 从数据库配置中获取计费比率
        rate = self.billing_configs.get_billing_rate("resource", resource_type)
        # 根据具体资源类型和使用量计算费用
        return self._calculate_cost_by_rate(rate, usage)

    def _calculate_cost_by_rate(self, rate: Decimal, data: dict) -> Decimal:
        """根据费率和数据计算费用"""
        # 默认按调用次数计算
        count = data.get("count", 0)
        return rate * Decimal(str(count))

    def update_company_credit(self, company_id: str, amount: Decimal, detail: dict) -> bool:
        """更新公司积分余额"""
        try:
            company = self.companies.get_company_by_id(company_id)
            if not company:
                log.error(f"公司不存在: company_id={company_id}")
                return False

            # 获取公司所有用户中第一个用户作为积分操作的用户
            # 在实际实现中，可能需要更复杂的逻辑来确定使用哪个用户
            # 这里简化处理，使用公司负责人的用户ID
            user_id = company.owner_user_id
            if not user_id:
                log.error(f"公司缺少负责人，无法更新积分: company_id={company_id}")
                return False

            # 更新公司积分余额
            result = self.credits.add_credit_by_user_id(
                form_data=AddCreditForm(
                    user_id=user_id,
                    company_id=company.id,
                    amount=amount,
                    detail=SetCreditFormDetail(**detail)
                )
            )
            
            return result is not None
        except Exception as e:
            log.error(f"更新公司积分余额失败: {e}")
            return False

    def record_api_call(self, user_id: str, session_id: str, service_provider: str, 
                       model_name: Optional[str], credits_consumed: Decimal, 
                       consumed_at: time.struct_time) -> bool:
        """记录API调用到hsai_business_api_usage_log表"""
        try:
            # 创建API调用记录
            api_log_form = APIUsageLogForm(
                user_id=user_id,
                session_id=session_id,
                service_provider=service_provider,
                model_name=model_name,
                credits_consumed=credits_consumed
            )
            
            result = self.api_usage_logs.insert_new_log(api_log_form)
            if result:
                enqueue_user_activity_event(
                    event_type="api_call",
                    user_id=user_id,
                    metadata={
                        "session_id": session_id,
                        "service_provider": service_provider,
                        "model_name": model_name,
                        "credits_consumed": float(credits_consumed),
                    },
                )
            return result is not None
        except Exception as e:
            log.error(f"记录API调用失败: {e}")
            return False

    def handle_task_completion_with_billing(self, message: Dict[str, Any]) -> None:
        """处理任务完成信号并触发计费"""
        try:
            # 获取任务信息
            session_id = message.get("session_id")
            if not session_id:
                log.warning("消息中缺少session_id")
                return

            # 根据session_id查找任务
            # 注意：在实际实现中，可能需要通过其他方式关联session_id和任务
            # 这里假设任务ID等于session_id或可以通过session_id找到任务
            task = None
            # 尝试直接通过session_id查找任务
            # 这需要在HSAITasks中实现相应的方法
            
            # 如果找不到任务，记录警告并返回
            if not task:
                log.warning(f"未找到与session_id关联的任务: session_id={session_id}")
                return

            # 记录API调用到hsai_business_api_usage_log表
            # 注意：这里需要从message中提取相关信息
            service_provider = message.get("service_provider", "unknown")
            model_name = message.get("model_name")
            credits_consumed = Decimal(str(message.get("credits_consumed", 0)))
            
            self.record_api_call(
                user_id=task.user_id,
                session_id=task.session_id or session_id,  # 使用任务的会话ID或消息中的session_id
                service_provider=service_provider,
                model_name=model_name,
                credits_consumed=credits_consumed,
                consumed_at=time.localtime()
            )

            # 计算费用（仅基于资源消耗）
            # 这里需要根据实际的资源使用情况计算费用
            # 示例：计算API调用费用
            api_calls = message.get("content", {}).get("api_calls", 0)
            cost = self.calculate_resource_cost("api_call", {"count": api_calls})

            # 更新公司credit余量
            if hasattr(task, 'company_id') and task.company_id:
                self.update_company_credit(
                    company_id=task.company_id,
                    amount=-cost,  # 负值表示消耗积分
                    detail={
                        "session_id": session_id,
                        "resource_type": "api_call",
                        "amount": float(cost)
                    }
                )
            else:
                log.warning(f"任务没有关联公司: task_id={getattr(task, 'id', 'unknown')}")

        except Exception as e:
            log.error(f"计费处理失败: {e}")


# 全局实例
billing_service = BillingService()
