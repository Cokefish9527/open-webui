#!/usr/bin/env python3
"""
计费系统测试脚本
用于测试计费模块的各项功能
"""

import asyncio
import logging
import time
import uuid
from decimal import Decimal
from typing import Dict, Any

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.billing_config import BillingConfigs, BillingConfigForm
from open_webui.models.api_usage_log import APIUsageLogs, APIUsageLogForm
from open_webui.models.hsai_companies import Companies, CompanyForm
from open_webui.models.hsai_tasks import HSAITasks, HSAITaskForm
from open_webui.models.users import Users
from open_webui.models.credits import Credits
from open_webui.services.billing_service import billing_service

# 配置日志
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class BillingSystemTester:
    """计费系统测试类"""
    
    def __init__(self):
        self.user_id = ""
        self.company_id = ""
        self.task_id = ""
    
    def generate_random_string(self, length=8):
        """生成随机字符串"""
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=length))
    
    def test_billing_config_crud(self):
        """测试计费配置的增删改查"""
        print("\n=== 测试计费配置CRUD操作 ===")
        
        try:
            # 创建计费配置
            config_form = BillingConfigForm(
                config_type="resource",
                config_key="test_api_call",
                config_value={"rate": "0.5", "unit": "per_call"},
                description="测试API调用计费配置",
                is_active=True
            )
            
            config = BillingConfigs.insert_new_config(config_form)
            if not config:
                print("✗ 创建计费配置失败")
                return False
            
            config_id = config.id
            print(f"✓ 创建计费配置成功: {config_id}")
            
            # 查询计费配置
            retrieved_config = BillingConfigs.get_config_by_id(config_id)
            if not retrieved_config:
                print("✗ 查询计费配置失败")
                return False
            
            print(f"✓ 查询计费配置成功: {retrieved_config.config_key}")
            
            # 更新计费配置
            from open_webui.models.billing_config import BillingConfigUpdateForm
            update_form = BillingConfigUpdateForm(
                description="更新后的测试API调用计费配置",
                is_active=False
            )
            
            updated_config = BillingConfigs.update_config_by_id(config_id, update_form)
            if not updated_config:
                print("✗ 更新计费配置失败")
                return False
            
            print(f"✓ 更新计费配置成功: {updated_config.description}, is_active={updated_config.is_active}")
            
            # 删除计费配置
            result = BillingConfigs.delete_config_by_id(config_id)
            if not result:
                print("✗ 删除计费配置失败")
                return False
            
            print("✓ 删除计费配置成功")
            return True
            
        except Exception as e:
            print(f"✗ 计费配置CRUD测试异常: {e}")
            return False
    
    def test_api_usage_log_crud(self):
        """测试API使用记录的增删改查"""
        print("\n=== 测试API使用记录CRUD操作 ===")
        
        try:
            # 创建API使用记录
            usage_form = APIUsageLogForm(
                user_id="test_user_123",
                session_id="test_session_456",
                service_provider="openai",
                model_name="gpt-4",
                credits_consumed=Decimal("0.3")
            )
            
            usage_log = APIUsageLogs.insert_new_log(usage_form)
            if not usage_log:
                print("✗ 创建API使用记录失败")
                return False
            
            log_id = usage_log.id
            print(f"✓ 创建API使用记录成功: {log_id}")
            
            # 根据会话ID查询API使用记录
            logs = APIUsageLogs.get_logs_by_session_id("test_session_456")
            if not logs:
                print("✗ 根据会话ID查询API使用记录失败")
                return False
            
            print(f"✓ 根据会话ID查询API使用记录成功: 找到 {len(logs)} 条记录")
            
            # 查询总消耗积分
            total_credits = APIUsageLogs.get_total_credits_consumed_by_session("test_session_456")
            print(f"✓ 查询总消耗积分成功: {total_credits}")
            
            return True
            
        except Exception as e:
            print(f"✗ API使用记录CRUD测试异常: {e}")
            return False
    
    def test_billing_rate_calculation(self):
        """测试计费比率计算"""
        print("\n=== 测试计费比率计算 ===")
        
        try:
            # 创建计费配置
            config_form = BillingConfigForm(
                config_type="resource",
                config_key="calculation_test",
                config_value={"rate": "1.5", "unit": "per_unit"},
                description="计费比率计算测试配置",
                is_active=True
            )
            
            config = BillingConfigs.insert_new_config(config_form)
            if not config:
                print("✗ 创建计费配置失败")
                return False
            
            # 测试计费比率获取
            rate = BillingConfigs.get_billing_rate("resource", "calculation_test")
            expected_rate = Decimal("1.5")
            if rate != expected_rate:
                print(f"✗ 计费比率获取失败: 期望 {expected_rate}, 实际 {rate}")
                return False
            
            print(f"✓ 计费比率获取成功: {rate}")
            
            # 测试费用计算
            cost = billing_service.calculate_resource_cost("calculation_test", {"count": 10})
            expected_cost = Decimal("15.0")
            if cost != expected_cost:
                print(f"✗ 费用计算失败: 期望 {expected_cost}, 实际 {cost}")
                return False
            
            print(f"✓ 费用计算成功: {cost}")
            
            # 清理测试数据
            BillingConfigs.delete_config_by_id(config.id)
            return True
            
        except Exception as e:
            print(f"✗ 计费比率计算测试异常: {e}")
            return False
    
    def test_complete_billing_flow(self):
        """测试完整的计费流程"""
        print("\n=== 测试完整计费流程 ===")
        
        try:
            # 创建公司
            company_form = CompanyForm(
                name="测试公司",
                description="用于计费系统测试的公司"
            )
            
            company = Companies.insert_new_company("test_owner_123", company_form)
            if not company:
                print("✗ 创建公司失败")
                return False
            
            self.company_id = company.id
            print(f"✓ 创建公司成功: {company.name}")
            
            # 创建用户并关联公司
            # 注意：在实际测试中，需要确保用户表中有相应的用户
            
            # 创建任务
            task_form = HSAITaskForm(
                title="计费测试任务",
                description="用于测试计费系统的任务",
                task_type="api_call",
                task_category="test"
            )
            
            task = HSAITasks.insert_new_task("test_user_123", task_form)
            if not task:
                print("✗ 创建任务失败")
                return False
            
            self.task_id = task.id
            print(f"✓ 创建任务成功: {task.title}")
            
            # 模拟任务完成消息
            message = {
                "session_id": "test_session_123456",
                "service_provider": "openai",
                "model_name": "gpt-4",
                "credits_consumed": "0.5",
                "content": {
                    "api_calls": 5
                }
            }
            
            # 处理计费
            billing_service.handle_task_completion_with_billing(message)
            print("✓ 计费处理完成")
            
            # 验证API使用记录
            logs = APIUsageLogs.get_logs_by_session_id("test_session_123456")
            if not logs:
                print("✗ API使用记录未创建")
                return False
            
            print(f"✓ API使用记录创建成功: {len(logs)} 条记录")
            
            # 清理测试数据
            # 注意：在实际实现中，需要清理创建的测试数据
            
            return True
            
        except Exception as e:
            print(f"✗ 完整计费流程测试异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("开始计费系统测试...")
        
        tests = [
            self.test_billing_config_crud,
            self.test_api_usage_log_crud,
            self.test_billing_rate_calculation,
            # self.test_complete_billing_flow,  # 这个测试需要更多设置
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"测试 {test.__name__} 发生异常: {e}")
                failed += 1
        
        print(f"\n测试完成: {passed} 个通过, {failed} 个失败")
        return failed == 0


def main():
    """主函数"""
    tester = BillingSystemTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 所有计费系统测试通过!")
        return 0
    else:
        print("\n❌ 部分计费系统测试失败!")
        return 1


if __name__ == "__main__":
    import random
    exit(main())