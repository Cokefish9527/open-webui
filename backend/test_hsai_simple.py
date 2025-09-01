#!/usr/bin/env python3
"""
HSAI集成功能简单测试脚本
"""

import asyncio
import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

async def test_hsai_modules():
    """测试HSAI模块导入和基本功能"""
    print("🔍 开始测试HSAI模块...")
    
    try:
        # 测试工作流管理器
        print("\n1. 测试工作流管理器...")
        from open_webui.utils.n8n_workflow_manager import N8NWorkflowManager
        
        workflow_manager = N8NWorkflowManager()
        workflows = await workflow_manager.load_workflows()
        print(f"   ✅ 成功加载 {len(workflows)} 个工作流配置")
        
        # 测试工作流选择器
        print("\n2. 测试工作流选择器...")
        from open_webui.utils.workflow_selector import WorkflowSelector
        
        selector = WorkflowSelector(workflow_manager)
        test_message = "我想了解公司的基本信息"
        selected_workflow = await selector.select_workflow(test_message)
        print(f"   ✅ 消息: '{test_message}'")
        print(f"   ✅ 选择的工作流: {selected_workflow}")
        
        # 测试N8N客户端
        print("\n3. 测试N8N客户端...")
        from open_webui.utils.n8n_client import N8NClient
        
        client = N8NClient()
        await client.initialize()
        print("   ✅ N8N客户端初始化成功")
        await client.close()
        
        # 测试消息处理器
        print("\n4. 测试消息处理器...")
        from open_webui.utils.message_processor import MessageProcessor
        
        processor = MessageProcessor()
        test_response = {
            "status": "success",
            "data": {"result": "测试结果", "type": "info"}
        }
        processed = await processor.process_response(test_response, "test_workflow")
        print(f"   ✅ 处理结果: {processed}")
        
        # 测试监控模块
        print("\n5. 测试监控模块...")
        from open_webui.utils.hsai_monitor import HSAIMonitor
        from open_webui.utils.hsai_logger import HSAILogger
        
        monitor = HSAIMonitor()
        logger = HSAILogger()
        
        # 记录一个测试事件
        await monitor.record_performance("test_function", 0.1, {"test": True})
        logger.info("测试日志记录", extra={"component": "test"})
        
        health = await monitor.get_health_status()
        print(f"   ✅ 系统健康状态: {health['status']}")
        
        print("\n🎉 所有HSAI模块测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_websocket_integration():
    """测试WebSocket集成"""
    print("\n🔍 测试WebSocket集成...")
    
    try:
        # 这里我们只测试导入，不实际连接WebSocket
        from open_webui.routers.hsai_websocket import router
        print("   ✅ WebSocket路由导入成功")
        
        return True
        
    except Exception as e:
        print(f"   ❌ WebSocket集成测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("=" * 60)
    print("🚀 HSAI智能对话消息转发系统 - 功能测试")
    print("=" * 60)
    
    # 测试基本模块
    modules_ok = await test_hsai_modules()
    
    # 测试WebSocket集成
    websocket_ok = await test_websocket_integration()
    
    print("\n" + "=" * 60)
    if modules_ok and websocket_ok:
        print("✅ 所有测试通过！系统准备就绪。")
        print("\n📋 下一步操作建议：")
        print("   1. 启动服务器: uvicorn open_webui.main:app --host 0.0.0.0 --port 8080")
        print("   2. 访问WebSocket端点: ws://localhost:8080/ws/hsai")
        print("   3. 发送测试消息验证完整流程")
    else:
        print("❌ 部分测试失败，请检查错误信息")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())