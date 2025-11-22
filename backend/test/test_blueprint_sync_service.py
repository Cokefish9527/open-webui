#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战略蓝图同步服务单元测试
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# 添加项目路径
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from open_webui.services.blueprint_sync_service import (
    _complete_company_info_task,
    sync_blueprint_for_user
)
from open_webui.models.hsai_tasks import HSAITaskModel, HSAITaskStatus


class TestBlueprintSyncService(unittest.TestCase):
    
    def setUp(self):
        """测试前准备"""
        pass
    
    def tearDown(self):
        """测试后清理"""
        pass
    
    @patch('open_webui.services.blueprint_sync_service.HSAITasks')
    def test_complete_company_info_task_with_multiple_templates(self, mock_tasks):
        """测试处理多种模板键的企业信息收集任务"""
        # 模拟任务数据
        mock_task1 = MagicMock()
        mock_task1.config = {"template_key": "company_info_collection"}
        mock_task1.status = HSAITaskStatus.PENDING.value
        
        mock_task2 = MagicMock()
        mock_task2.config = {"template_key": "company_info_collection_fallback"}
        mock_task2.status = HSAITaskStatus.PENDING.value
        
        mock_task3 = MagicMock()
        mock_task3.config = {"template_key": "other_template"}
        mock_task3.status = HSAITaskStatus.PENDING.value
        
        # 模拟已完成的任务
        mock_task4 = MagicMock()
        mock_task4.config = {"template_key": "company_info_collection"}
        mock_task4.status = HSAITaskStatus.COMPLETED.value
        
        # 设置模拟返回值
        mock_tasks.get_tasks_by_user_id.return_value = [
            mock_task1, mock_task2, mock_task3, mock_task4
        ]
        
        # 模拟更新任务的返回值
        mock_updated_task = MagicMock()
        mock_updated_task.id = "test_task_id"
        mock_updated_task.status = HSAITaskStatus.COMPLETED.value
        mock_tasks.update_task_by_id.return_value = mock_updated_task
        
        # 模拟日志记录
        with patch('open_webui.services.blueprint_sync_service.HSAITaskStateLogs'):
            # 调用函数
            result = _complete_company_info_task("test_project_id", "test_user_id")
            
            # 验证结果
            self.assertIsNotNone(result)
            # 验证调用了获取任务的方法
            mock_tasks.get_tasks_by_user_id.assert_called_once_with(
                user_id="test_user_id",
                project_id="test_project_id",
                limit=50
            )
            # 验证调用了更新任务的方法
            mock_tasks.update_task_by_id.assert_called_once_with(
                mock_task1.id,
                unittest.mock.ANY
            )
    
    @patch('open_webui.services.blueprint_sync_service.HSAITasks')
    def test_complete_company_info_task_skip_completed(self, mock_tasks):
        """测试跳过已完成的任务"""
        # 模拟已完成的任务
        mock_task = MagicMock()
        mock_task.config = {"template_key": "company_info_collection"}
        mock_task.status = HSAITaskStatus.COMPLETED.value
        
        # 设置模拟返回值
        mock_tasks.get_tasks_by_user_id.return_value = [mock_task]
        
        # 调用函数
        result = _complete_company_info_task("test_project_id", "test_user_id")
        
        # 验证结果
        self.assertIsNone(result)
        # 验证没有调用更新任务的方法
        mock_tasks.update_task_by_id.assert_not_called()
    
    @patch('open_webui.services.blueprint_sync_service._resolve_project_for_user')
    @patch('open_webui.services.blueprint_sync_service._fetch_latest_blueprint_from_n8n')
    @patch('open_webui.services.blueprint_sync_service.HSAIBlueprintProgressTable')
    def test_sync_blueprint_for_user_first_processing(self, mock_progress_table, mock_fetch_blueprint, mock_resolve_project):
        """测试首次处理蓝图时的信息收集状态更新"""
        # 模拟数据
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
        
        # 模拟蓝图进度记录（未处理信息收集）
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
        
        # 模拟消息
        message = {
            "user_id": "user_1",
            "content_type": "blue_image_content",
            "status": "FINISHED"
        }
        
        # 模拟其他依赖函数
        with patch('open_webui.services.blueprint_sync_service._sync_task_links') as mock_sync_tasks, \
             patch('open_webui.services.blueprint_sync_service._maybe_generate_daily_subtask') as mock_generate_subtask, \
             patch('open_webui.services.blueprint_sync_service._complete_company_info_task') as mock_complete_info_task, \
             patch('open_webui.services.blueprint_sync_service.evaluate_project_tasks') as mock_evaluate_tasks, \
             patch('open_webui.services.blueprint_sync_service.HSAI_WEBSOCKET_EVENTS', {"RESPONSE": "hsai_response"}):
            
            # 设置模拟返回值
            mock_sync_tasks.return_value = ([], [])
            mock_generate_subtask.return_value = None
            mock_complete_info_task.return_value = MagicMock()
            mock_evaluate_tasks.return_value = []
            
            # 调用函数
            result = sync_blueprint_for_user(message)
            
            # 验证结果
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.progress)
            # 验证调用了完成信息收集任务的函数
            mock_complete_info_task.assert_called_once_with(
                project_id="test_project_id",
                user_id="user_1"
            )
            # 验证更新了蓝图进度（标记信息收集已处理）
            self.assertEqual(mock_progress_table.upsert_progress.call_count, 2)
    
    @patch('open_webui.services.blueprint_sync_service._resolve_project_for_user')
    @patch('open_webui.services.blueprint_sync_service._fetch_latest_blueprint_from_n8n')
    @patch('open_webui.services.blueprint_sync_service.HSAIBlueprintProgressTable')
    def test_sync_blueprint_for_user_skip_duplicate_processing(self, mock_progress_table, mock_fetch_blueprint, mock_resolve_project):
        """测试跳过重复处理信息收集状态"""
        # 模拟数据
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
        
        # 模拟蓝图进度记录（已处理信息收集）
        mock_progress = MagicMock()
        mock_progress.id = "progress_1"
        mock_progress.project_id = "test_project_id"
        mock_progress.blueprint_version = "v1.0"
        mock_progress.info_collection_processed = True  # 已处理
        mock_progress.daily_cycle_config = None
        mock_progress.model_dump.return_value = {
            "id": "progress_1",
            "project_id": "test_project_id",
            "blueprint_version": "v1.0",
            "info_collection_processed": True
        }
        
        mock_progress_table.get_by_project.return_value = mock_progress
        mock_progress_table.upsert_progress.return_value = mock_progress
        
        # 模拟消息
        message = {
            "user_id": "user_1",
            "content_type": "blue_image_content",
            "status": "FINISHED"
        }
        
        # 模拟其他依赖函数
        with patch('open_webui.services.blueprint_sync_service._sync_task_links') as mock_sync_tasks, \
             patch('open_webui.services.blueprint_sync_service._maybe_generate_daily_subtask') as mock_generate_subtask, \
             patch('open_webui.services.blueprint_sync_service._complete_company_info_task') as mock_complete_info_task, \
             patch('open_webui.services.blueprint_sync_service.evaluate_project_tasks') as mock_evaluate_tasks, \
             patch('open_webui.services.blueprint_sync_service.HSAI_WEBSOCKET_EVENTS', {"RESPONSE": "hsai_response"}):
            
            # 设置模拟返回值
            mock_sync_tasks.return_value = ([], [])
            mock_generate_subtask.return_value = None
            mock_complete_info_task.return_value = None
            mock_evaluate_tasks.return_value = []
            
            # 调用函数
            result = sync_blueprint_for_user(message)
            
            # 验证结果
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.progress)
            # 验证没有调用完成信息收集任务的函数
            mock_complete_info_task.assert_not_called()
            # 验证只更新了一次蓝图进度（没有标记信息收集已处理）
            self.assertEqual(mock_progress_table.upsert_progress.call_count, 1)


if __name__ == '__main__':
    unittest.main()