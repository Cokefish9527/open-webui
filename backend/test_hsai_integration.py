"""
HSAI智能工作流集成系统测试脚本
"""

import asyncio
import json
import logging
from pathlib import Path
import sys

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from open_webui.utils.n8n_workflow_manager import workflow_manager
from open_webui.utils.workflow_selector import workflow_selector, SelectionContext
from open_webui.utils.n8n_client import n8n_client, ExecutionRequest
from open_webui.utils.message_processor import message_processor
from open_webui.utils.hsai_monitor import hsai_monitor
from open_webui.utils.hsai_logger import hsai_logger

# 配置日志
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

async def test_workflow_manager():
    """测试工作流管理器"""
    print("\n=== 测试工作流管理器 ===")
    
    try:
        await workflow_manager.initialize()
        
        # 获取所有工作流
        workflows = workflow_manager.get_all_workflows()
        print(f"加载的工作流数量: {len(workflows)}")
        
        for workflow in workflows:
            print(f"- {workflow.name} ({workflow.type.value})")
            print(f"  URL: {workflow.webhook_url}")
            print(f"  关键词: {workflow.keywords}")
            
        # 获取统计信息
        stats = workflow_manager.get_workflow_stats()
        print(f"工作流统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
        return True
        
    except Exception as e:
        print(f"工作流管理器测试失败: {e}")
        return False

async def test_workflow_selector():
    """测试工作流选择器"""
    print("\n=== 测试工作流选择器 ===")
    
    test_messages = [
        "我想制作一个关于机械设备的短视频",
        "帮我分析一下竞品公司的信息",
        "最近有什么热门的内容趋势？",
        "分析这个视频的关键词数据"
    ]
    
    try:
        for message in test_messages:
            print(f"\n测试消息: {message}")
            
            context = SelectionContext(
                message=message,
                user_id="test_user",
                session_id="test_session",
                business_name="测试企业"
            )
            
            selected_workflow = await workflow_selector.select_workflow(context)
            
            if selected_workflow:
                print(f"选择的工作流: {selected_workflow.name}")
                print(f"工作流类型: {selected_workflow.type.value}")
                
                # 获取选择解释
                explanation = workflow_selector.get_selection_explanation(selected_workflow, context)
                print(f"选择原因: {explanation['selection_reason']['detected_intent']}")
                print(f"匹配关键词: {explanation['selection_reason']['matching_keywords']}")
            else:
                print("未找到匹配的工作流")
                
        return True
        
    except Exception as e:
        print(f"工作流选择器测试失败: {e}")
        return False

async def test_n8n_client():
    """测试N8N客户端"""
    print("\n=== 测试N8N客户端 ===")
    
    try:
        await n8n_client.initialize()
        
        # 健康检查
        health = await n8n_client.health_check()
        print(f"N8N健康状态: {json.dumps(health, indent=2, ensure_ascii=False)}")
        
        # 获取统计信息
        stats = n8n_client.get_execution_stats()
        print(f"执行统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
        return True
        
    except Exception as e:
        print(f"N8N客户端测试失败: {e}")
        return False

async def test_message_processor():
    """测试消息处理器"""
    print("\n=== 测试消息处理器 ===")
    
    # 模拟n8n响应数据
    test_responses = [
        {
            "success": True,
            "messageType": "video_creation",
            "session_id": "test_session",
            "business_name": "测试企业",
            "displayText": "视频创作完成！\\n\\n这是一个关于机械设备的专业视频。",
            "data": {
                "url_list": "https://example.com/video.mp4"
            },
            "file_preview": 1,
            "create_ts": "1693123456789"
        },
        {
            "success": True,
            "company_data": {
                "name": "测试公司",
                "industry": "制造业",
                "size": "中型企业"
            },
            "analysis_result": {
                "market_position": "行业领先",
                "competitive_advantage": "技术创新"
            },
            "recommendations": [
                "加强品牌建设",
                "扩大市场份额"
            ]
        }
    ]
    
    try:
        for i, response in enumerate(test_responses):
            print(f"\n测试响应 {i+1}:")
            
            workflow_type = "main" if i == 0 else "company_info"
            processed = await message_processor.process_n8n_response(response, workflow_type)
            
            print(f"消息类型: {processed.message_type.value}")
            print(f"处理状态: {processed.processing_status.value}")
            print(f"内容预览: {processed.content[:100]}...")
            
            if processed.media_urls:
                print(f"媒体URL: {processed.media_urls}")
                
            # 格式化为WebSocket消息
            ws_message = await message_processor.format_for_websocket(
                processed, "test_session", "test_user"
            )
            print(f"WebSocket消息类型: {ws_message['type']}")
            
        return True
        
    except Exception as e:
        print(f"消息处理器测试失败: {e}")
        return False

async def test_monitoring():
    """测试监控系统"""
    print("\n=== 测试监控系统 ===")
    
    try:
        # 启动监控
        hsai_monitor.start_monitoring()
        
        # 模拟一些操作和错误
        from open_webui.utils.hsai_monitor import ComponentType, ErrorLevel
        
        hsai_monitor.log_error(
            ComponentType.WEBSOCKET,
            ErrorLevel.WARNING,
            "测试警告消息",
            details={"test": True}
        )
        
        hsai_monitor.log_performance(
            ComponentType.N8N_CLIENT,
            "test_operation",
            1.5,
            True,
            details={"test": True}
        )
        
        # 获取系统健康状态
        health = hsai_monitor.get_system_health()
        print(f"系统健康状态: {json.dumps(health, indent=2, ensure_ascii=False)}")
        
        # 获取错误摘要
        error_summary = hsai_monitor.get_error_summary(1)
        print(f"错误摘要: {json.dumps(error_summary, indent=2, ensure_ascii=False)}")
        
        # 获取性能摘要
        perf_summary = hsai_monitor.get_performance_summary(1)
        print(f"性能摘要: {json.dumps(perf_summary, indent=2, ensure_ascii=False)}")
        
        # 获取日志统计
        log_stats = hsai_logger.get_log_stats()
        print(f"日志统计: {json.dumps(log_stats, indent=2, ensure_ascii=False)}")
        
        return True
        
    except Exception as e:
        print(f"监控系统测试失败: {e}")
        return False
    finally:
        hsai_monitor.stop_monitoring()

async def run_integration_test():
    """运行完整的集成测试"""
    print("开始HSAI智能工作流集成系统测试...")
    
    test_results = []
    
    # 运行各个测试
    tests = [
        ("工作流管理器", test_workflow_manager),
        ("工作流选择器", test_workflow_selector),
        ("N8N客户端", test_n8n_client),
        ("消息处理器", test_message_processor),
        ("监控系统", test_monitoring)
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results.append((test_name, result))
            print(f"✅ {test_name} 测试{'通过' if result else '失败'}")
        except Exception as e:
            test_results.append((test_name, False))
            print(f"❌ {test_name} 测试异常: {e}")
            
    # 输出测试总结
    print(f"\n=== 测试总结 ===")
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    print(f"总测试数: {total}")
    print(f"通过测试: {passed}")
    print(f"失败测试: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有测试通过！系统集成成功！")
    else:
        print("⚠️  部分测试失败，请检查相关模块")
        
    return passed == total

if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(run_integration_test())
    sys.exit(0 if success else 1)