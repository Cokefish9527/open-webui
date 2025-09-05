#!/usr/bin/env python3
"""
验证工作流URL配置
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def verify_workflow_urls():
    """验证工作流URL配置"""
    try:
        from open_webui.config.n8n_workflows import N8NWorkflowType, N8N_WORKFLOW_WEBHOOKS
        
        print("=== 工作流URL配置验证 ===")
        
        expected_urls = {
            N8NWorkflowType.MAIN: "https://webhook-n8n.hsai.cc/webhook/n8n_chat",
            N8NWorkflowType.COMPANY_INFO: "https://webhook-n8n.hsai.cc/webhook/business_information_get",
            N8NWorkflowType.VIRAL_LEARNING: "https://n8n.hsai.cc/webhook-test/viral-learning"
        }
        
        all_correct = True
        for workflow_type, expected_url in expected_urls.items():
            actual_url = N8N_WORKFLOW_WEBHOOKS.get(workflow_type)
            is_correct = actual_url == expected_url
            all_correct = all_correct and is_correct
            
            print(f"工作流类型: {workflow_type.value}")
            print(f"  期望URL: {expected_url}")
            print(f"  实际URL: {actual_url}")
            print(f"  状态: {'✓ 正确' if is_correct else '✗ 错误'}")
            print()
            
        if all_correct:
            print("🎉 所有工作流URL配置正确!")
        else:
            print("❌ 部分工作流URL配置错误!")
            
        return all_correct
        
    except Exception as e:
        print(f"验证过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    verify_workflow_urls()