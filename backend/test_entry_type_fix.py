#!/usr/bin/env python3
"""
测试entry_type路由修复的脚本
"""

import sys
import os
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from open_webui.services.workflow_orchestration_center import workflow_orchestration_center
from open_webui.config.n8n_workflows import N8NWorkflowType
from open_webui.utils.n8n_workflow_manager import WorkflowType

async def test_entry_type_routing():
    """测试entry_type路由功能"""
    print("🔧 测试entry_type路由修复...")
    
    # 初始化工作流编排中心
    await workflow_orchestration_center.initialize()
    
    # 测试用例1: entry_type = company
    print("\n📝 测试用例1: entry_type = company")
    context1 = {"entry_type": "company"}
    workflow_type1 = workflow_orchestration_center.router_manager.route_request("你好", context1)
    print(f"   输入: entry_type=company")
    print(f"   期望: WorkflowType.COMPANY_INFO")
    print(f"   实际: {workflow_type1}")
    print(f"   结果: {'✅ 通过' if workflow_type1 == WorkflowType.COMPANY_INFO else '❌ 失败'}")
    
    # 测试用例2: entry_type = chat
    print("\n📝 测试用例2: entry_type = chat")
    context2 = {"entry_type": "chat"}
    workflow_type2 = workflow_orchestration_center.router_manager.route_request("你好", context2)
    print(f"   输入: entry_type=chat")
    print(f"   期望: WorkflowType.MAIN")
    print(f"   实际: {workflow_type2}")
    print(f"   结果: {'✅ 通过' if workflow_type2 == WorkflowType.MAIN else '❌ 失败'}")
    
    # 测试用例3: entry_type = video_crawl
    print("\n📝 测试用例3: entry_type = video_crawl")
    context3 = {"entry_type": "video_crawl"}
    workflow_type3 = workflow_orchestration_center.router_manager.route_request("你好", context3)
    print(f"   输入: entry_type=video_crawl")
    print(f"   期望: WorkflowType.VIDEO_CRAWL")
    print(f"   实际: {workflow_type3}")
    print(f"   结果: {'✅ 通过' if workflow_type3 == WorkflowType.VIDEO_CRAWL else '❌ 失败'}")
    
    # 测试用例4: entry_type = viral_learning
    print("\n📝 测试用例4: entry_type = viral_learning")
    context4 = {"entry_type": "viral_learning"}
    workflow_type4 = workflow_orchestration_center.router_manager.route_request("你好", context4)
    print(f"   输入: entry_type=viral_learning")
    print(f"   期望: WorkflowType.VIRAL_LEARNING")
    print(f"   实际: {workflow_type4}")
    print(f"   结果: {'✅ 通过' if workflow_type4 == WorkflowType.VIRAL_LEARNING else '❌ 失败'}")
    
    # 测试用例5: 无entry_type，使用内容路由
    print("\n📝 测试用例5: 无entry_type，使用内容路由")
    context5 = {}
    workflow_type5 = workflow_orchestration_center.router_manager.route_request("帮我收集阿里巴巴集团的企业信息", context5)
    print(f"   输入: 内容='帮我收集阿里巴巴集团的企业信息'")
    print(f"   期望: WorkflowType.COMPANY_INFO (基于内容匹配)")
    print(f"   实际: {workflow_type5}")
    print(f"   结果: {'✅ 通过' if workflow_type5 == WorkflowType.COMPANY_INFO else '❌ 失败'}")
    
    print("\n🏁 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_entry_type_routing())