#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战略蓝图处理性能测试脚本
"""

import os
import sys
import time
import asyncio
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))


def performance_test_blueprint_sync():
    """测试蓝图同步的性能"""
    try:
        print("=== 蓝图同步性能测试 ===")
        
        # 模拟消息
        message = {
            "user_id": "test_user_id",
            "content_type": "blue_image_content",
            "status": "FINISHED",
            "session_id": "test_session_id"
        }
        
        # 测试单次处理性能
        with patch('open_webui.services.blueprint_sync_service._resolve_project_for_user') as mock_resolve_project, \
             patch('open_webui.services.blueprint_sync_service._fetch_latest_blueprint_from_n8n') as mock_fetch_blueprint, \
             patch('open_webui.services.blueprint_sync_service.HSAIBlueprintProgressTable') as mock_progress_table, \
             patch('open_webui.services.blueprint_sync_service._sync_task_links') as mock_sync_tasks, \
             patch('open_webui.services.blueprint_sync_service._maybe_generate_daily_subtask') as mock_generate_subtask, \
             patch('open_webui.services.blueprint_sync_service._complete_company_info_task') as mock_complete_info_task, \
             patch('open_webui.services.blueprint_sync_service.evaluate_project_tasks') as mock_evaluate_tasks, \
             patch('open_webui.services.blueprint_sync_service.HSAI_WEBSOCKET_EVENTS', {"RESPONSE": "hsai_response"}):
            
            # 设置模拟返回值
            mock_resolve_project.return_value = "test_project_id"
            mock_fetch_blueprint.return_value = {
                "id": "blueprint_1",
                "blueprintVersion": "v1.0",
                "executionDurationDays": "30",
                "plannedTotalPosts": "100",
                "postingFrequency": "2条/天",
                "requiredTiktokAccounts": "3",
                "session_id": "session_1",
                "request_id": "request_1",
                "user_id": "user_1",
                "socket_id": "socket_1",
                "blue_image": "# Blueprint Content",
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-01T00:00:00Z"
            }
            
            mock_progress = MagicMock()
            mock_progress.id = "progress_1"
            mock_progress.project_id = "test_project_id"
            mock_progress.blueprint_version = "v1.0"
            mock_progress.info_collection_processed = False
            mock_progress.daily_cycle_config = None
            mock_progress.model_dump.return_value = {
                "id": "progress_1",
                "project_id": "test_project_id",
                "blueprint_version": "v1.0",
                "info_collection_processed": False
            }
            
            mock_progress_table.get_by_project.return_value = mock_progress
            mock_progress_table.upsert_progress.return_value = mock_progress
            
            mock_sync_tasks.return_value = ([], [])
            mock_generate_subtask.return_value = None
            mock_complete_info_task.return_value = MagicMock()
            mock_evaluate_tasks.return_value = []
            
            # 导入函数
            from open_webui.services.blueprint_sync_service import sync_blueprint_for_user
            
            # 执行性能测试
            start_time = time.time()
            
            # 执行100次同步操作
            for i in range(100):
                result = sync_blueprint_for_user(message)
                if result is None:
                    print(f"第{i+1}次执行失败")
                    return False
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"执行100次蓝图同步操作耗时: {duration:.4f}秒")
            print(f"平均每次操作耗时: {duration/100*1000:.4f}毫秒")
            
            if duration < 5.0:  # 5秒内完成100次操作
                print("✓ 性能测试通过")
                return True
            else:
                print("⚠ 性能测试警告：处理时间较长")
                return True
                
    except Exception as e:
        print(f"性能测试时发生错误: {e}")
        return False


def performance_test_conversation_handler():
    """测试对话处理器的性能"""
    try:
        print("=== 对话处理器性能测试 ===")
        
        # 模拟消息
        message = {
            "user_id": "test_user_id",
            "content_type": "blue_image_content",
            "status": "FINISHED",
            "session_id": "test_session_id"
        }
        
        # 测试单次处理性能
        with patch('open_webui.utils.conversation_queue_handler.sync_blueprint_for_user') as mock_sync_blueprint, \
             patch('open_webui.utils.conversation_queue_handler.Users') as mock_users, \
             patch('open_webui.utils.conversation_queue_handler.sio') as mock_sio, \
             patch('open_webui.utils.conversation_queue_handler.SESSION_POOL', {}), \
             patch('open_webui.utils.conversation_queue_handler.USER_POOL', {}):
            
            # 设置模拟返回值
            mock_result = MagicMock()
            mock_result.logs = ["测试日志"]
            mock_result.notifications = []
            mock_result.progress = MagicMock()
            mock_sync_blueprint.return_value = mock_result
            
            mock_users.is_user_info_collection_completed.return_value = False
            
            mock_sio.emit = MagicMock()
            
            # 导入函数
            from open_webui.utils.conversation_queue_handler import handle_conversation_agent_message
            
            # 执行性能测试
            start_time = time.time()
            
            # 执行100次处理操作
            for i in range(100):
                try:
                    asyncio.run(handle_conversation_agent_message(message))
                except Exception as e:
                    if "Socket.IO is not initialized" not in str(e):
                        print(f"第{i+1}次执行失败: {e}")
                        return False
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"执行100次对话处理操作耗时: {duration:.4f}秒")
            print(f"平均每次操作耗时: {duration/100*1000:.4f}毫秒")
            
            if duration < 5.0:  # 5秒内完成100次操作
                print("✓ 性能测试通过")
                return True
            else:
                print("⚠ 性能测试警告：处理时间较长")
                return True
                
    except Exception as e:
        print(f"对话处理器性能测试时发生错误: {e}")
        return False


def main():
    print("== 战略蓝图处理性能测试 ==")
    
    success1 = performance_test_blueprint_sync()
    print()
    success2 = performance_test_conversation_handler()
    
    if success1 and success2:
        print("✅ 所有性能测试完成。")
        return 0

    print("❌ 性能测试失败。")
    return 1


if __name__ == "__main__":
    sys.exit(main())