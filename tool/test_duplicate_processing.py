#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重复处理场景的脚本
"""

import os
import sys
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))


def test_duplicate_blueprint_processing():
    """测试重复处理蓝图场景"""
    try:
        # 模拟第一次处理
        print("=== 第一次处理蓝图 ===")
        
        with patch('open_webui.services.blueprint_sync_service.HSAIBlueprintProgressTable') as mock_progress_table, \
             patch('open_webui.services.blueprint_sync_service._complete_company_info_task') as mock_complete_task:
            
            # 模拟第一次处理时的蓝图进度（未处理信息收集）
            mock_progress_first = MagicMock()
            mock_progress_first.id = "progress_1"
            mock_progress_first.project_id = "test_project_id"
            mock_progress_first.blueprint_version = "v1.0"
            mock_progress_first.info_collection_processed = False
            mock_progress_first.model_dump.return_value = {
                "id": "progress_1",
                "project_id": "test_project_id",
                "blueprint_version": "v1.0",
                "info_collection_processed": False
            }
            
            mock_progress_table.get_by_project.return_value = mock_progress_first
            mock_progress_table.upsert_progress.return_value = mock_progress_first
            
            # 模拟完成任务的返回值
            mock_task_result = MagicMock()
            mock_task_result.id = "task_1"
            mock_complete_task.return_value = mock_task_result
            
            # 调用同步函数
            from open_webui.services.blueprint_sync_service import sync_blueprint_for_user
            
            message = {
                "user_id": "user_1",
                "content_type": "blue_image_content",
                "status": "FINISHED"
            }
            
            result1 = sync_blueprint_for_user(message)
            
            print(f"第一次处理结果: {result1 is not None}")
            print(f"日志条数: {len(result1.logs) if result1 else 0}")
            if result1 and result1.logs:
                for log in result1.logs:
                    print(f"  - {log}")
            
            # 验证第一次处理调用了完成任务函数
            mock_complete_task.assert_called_once()
            print("✓ 第一次处理正确调用了信息收集任务完成函数")
            
        print()
        print("=== 第二次处理相同蓝图 ===")
        
        # 模拟第二次处理
        with patch('open_webui.services.blueprint_sync_service.HSAIBlueprintProgressTable') as mock_progress_table, \
             patch('open_webui.services.blueprint_sync_service._complete_company_info_task') as mock_complete_task:
            
            # 模拟第二次处理时的蓝图进度（已处理信息收集）
            mock_progress_second = MagicMock()
            mock_progress_second.id = "progress_1"
            mock_progress_second.project_id = "test_project_id"
            mock_progress_second.blueprint_version = "v1.0"
            mock_progress_second.info_collection_processed = True  # 已处理
            mock_progress_second.model_dump.return_value = {
                "id": "progress_1",
                "project_id": "test_project_id",
                "blueprint_version": "v1.0",
                "info_collection_processed": True
            }
            
            mock_progress_table.get_by_project.return_value = mock_progress_second
            mock_progress_table.upsert_progress.return_value = mock_progress_second
            
            # 调用同步函数
            result2 = sync_blueprint_for_user(message)
            
            print(f"第二次处理结果: {result2 is not None}")
            print(f"日志条数: {len(result2.logs) if result2 else 0}")
            if result2 and result2.logs:
                for log in result2.logs:
                    print(f"  - {log}")
            
            # 验证第二次处理没有调用完成任务函数
            mock_complete_task.assert_not_called()
            print("✓ 第二次处理正确跳过了信息收集任务完成函数")
            
        print()
        print("=== 重复处理保护验证通过 ===")
        return True
        
    except Exception as e:
        print(f"测试重复处理时发生错误: {e}")
        return False


def test_duplicate_user_info_collection():
    """测试重复处理用户信息收集状态"""
    try:
        print("=== 用户信息收集状态重复处理测试 ===")
        
        # 模拟第一次处理
        with patch('open_webui.utils.conversation_queue_handler.Users') as mock_users:
            # 模拟用户信息收集状态为未完成
            mock_users.is_user_info_collection_completed.return_value = False
            
            from open_webui.utils.conversation_queue_handler import handle_conversation_agent_message
            import asyncio
            
            message = {
                "user_id": "test_user_id",
                "content_type": "blue_image",
                "status": "FINISHED",
                "session_id": "test_session_id"
            }
            
            # 第一次处理应该更新状态
            try:
                asyncio.run(handle_conversation_agent_message(message))
            except:
                pass  # 忽略Socket.IO错误
            
            # 验证调用了更新方法
            mock_users.update_user_info_collection_status.assert_called_once_with("test_user_id", True)
            print("✓ 第一次处理正确更新了用户信息收集状态")
            
        # 模拟第二次处理
        with patch('open_webui.utils.conversation_queue_handler.Users') as mock_users:
            # 模拟用户信息收集状态为已完成
            mock_users.is_user_info_collection_completed.return_value = True
            
            # 第二次处理应该跳过更新
            try:
                asyncio.run(handle_conversation_agent_message(message))
            except:
                pass  # 忽略Socket.IO错误
            
            # 验证没有调用更新方法
            mock_users.update_user_info_collection_status.assert_not_called()
            print("✓ 第二次处理正确跳过了用户信息收集状态更新")
            
        print()
        print("=== 用户信息收集状态重复处理验证通过 ===")
        return True
        
    except Exception as e:
        print(f"测试用户信息收集状态重复处理时发生错误: {e}")
        return False


def main():
    print("== 重复处理场景验证 ==")
    
    success1 = test_duplicate_blueprint_processing()
    print()
    success2 = test_duplicate_user_info_collection()
    
    if success1 and success2:
        print("✅ 所有重复处理场景验证通过。")
        return 0

    print("❌ 重复处理场景验证失败。")
    return 1


if __name__ == "__main__":
    sys.exit(main())