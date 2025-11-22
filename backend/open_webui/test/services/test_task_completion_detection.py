"""
任务完成条件检测机制单元测试
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 使用相对导入
from services.blueprint_sync_service import (
    _complete_company_info_task,
    sync_blueprint_for_user,
    BlueprintSyncResult
)
from utils.video_learning_notifier import (
    handle_video_learning_notification,
    _find_and_complete_video_task
)
from models.hsai_tasks import (
    HSAITaskModel,
    HSAITaskStatus
)
from models.users import UserModel


class TestTaskCompletionDetection(unittest.TestCase):
    
    def setUp(self):
        """测试前准备"""
        self.user_id = "test_user_123"
        self.project_id = "test_project_456"
        self.task_id = "test_task_789"
        self.video_id = "test_video_abc"
        
        # 创建模拟任务
        self.mock_task = HSAITaskModel(
            id=self.task_id,
            title="企业信息收集任务",
            description="收集企业相关信息",
            task_type="company_info",
            task_category="main",
            status=HSAITaskStatus.IN_PROGRESS.value,
            user_id=self.user_id,
            project_id=self.project_id,
            config={"template_key": "company_info_collection"},
            priority=10,
            created_at=int(datetime.now(timezone.utc).timestamp()),
            updated_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        # 创建已完成的任务
        self.completed_task = HSAITaskModel(
            id=self.task_id,
            title="已完成的企业信息收集任务",
            description="收集企业相关信息",
            task_type="company_info",
            task_category="main",
            status=HSAITaskStatus.COMPLETED.value,
            user_id=self.user_id,
            project_id=self.project_id,
            config={"template_key": "company_info_collection"},
            priority=10,
            created_at=int(datetime.now(timezone.utc).timestamp()),
            updated_at=int(datetime.now(timezone.utc).timestamp())
        )
    
    @patch('services.blueprint_sync_service.HSAITasks')
    def test_complete_company_info_task_success(self, mock_tasks):
        """测试成功完成企业信息收集任务"""
        # 设置模拟返回值
        mock_tasks.get_tasks_by_user_id.return_value = [self.mock_task]
        mock_tasks.update_task_by_id.return_value = self.completed_task
        
        # 调用被测试函数
        result = _complete_company_info_task(self.project_id, self.user_id)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result.status, HSAITaskStatus.COMPLETED.value)
        mock_tasks.update_task_by_id.assert_called_once_with(
            self.task_id,
            unittest.mock.ANY  # HSAITaskUpdateForm实例
        )
    
    @patch('services.blueprint_sync_service.HSAITasks')
    def test_complete_company_info_task_already_completed(self, mock_tasks):
        """测试已完成的企业信息收集任务"""
        # 设置模拟返回值
        mock_tasks.get_tasks_by_user_id.return_value = [self.completed_task]
        
        # 调用被测试函数
        result = _complete_company_info_task(self.project_id, self.user_id)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result.status, HSAITaskStatus.COMPLETED.value)
        # 验证没有调用更新方法
        mock_tasks.update_task_by_id.assert_not_called()
    
    @patch('services.blueprint_sync_service.HSAITasks')
    def test_complete_company_info_task_no_matching_task(self, mock_tasks):
        """测试没有匹配的企业信息收集任务"""
        # 创建不匹配的任务
        non_matching_task = HSAITaskModel(
            id="other_task",
            title="其他任务",
            description="其他任务描述",
            task_type="other",
            task_category="main",
            status=HSAITaskStatus.IN_PROGRESS.value,
            user_id=self.user_id,
            project_id=self.project_id,
            config={"template_key": "other_template"},
            priority=10,
            created_at=int(datetime.now(timezone.utc).timestamp()),
            updated_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        # 设置模拟返回值
        mock_tasks.get_tasks_by_user_id.return_value = [non_matching_task]
        
        # 调用被测试函数
        result = _complete_company_info_task(self.project_id, self.user_id)
        
        # 验证结果
        self.assertIsNone(result)
    
    @patch('services.blueprint_sync_service.HSAITasks')
    @patch('services.blueprint_sync_service.HSAITaskStateLogs')
    def test_sync_blueprint_for_user_info_collection_processed(self, mock_logs, mock_tasks):
        """测试处理企业信息收集任务的蓝图同步"""
        # 创建模拟消息
        message = {
            "user_id": self.user_id,
            "session_id": "test_session_123"
        }
        
        # 创建模拟蓝图进度（已处理过信息收集）
        mock_progress = MagicMock()
        mock_progress.info_collection_processed = True
        
        # 创建模拟函数
        with patch('services.blueprint_sync_service.HSAIBlueprintProgressTable') as mock_bp_table, \
             patch('services.blueprint_sync_service._resolve_project_for_user') as mock_resolve_project, \
             patch('services.blueprint_sync_service._fetch_latest_blueprint_from_n8n') as mock_fetch_blueprint, \
             patch('services.blueprint_sync_service._sync_task_links') as mock_sync_links, \
             patch('services.blueprint_sync_service._maybe_generate_daily_subtask') as mock_generate_subtask, \
             patch('services.blueprint_sync_service.evaluate_project_tasks') as mock_evaluate:
            
            # 设置模拟返回值
            mock_resolve_project.return_value = self.project_id
            mock_fetch_blueprint.return_value = {
                "id": "blueprint_123",
                "blueprintVersion": "v1",
                "blue_image": "战略蓝图内容"
            }
            mock_bp_table.get_by_project.return_value = mock_progress
            mock_bp_table.upsert_progress.return_value = mock_progress
            mock_sync_links.return_value = ([], [])
            mock_generate_subtask.return_value = None
            mock_evaluate.return_value = []
            
            # 调用被测试函数
            result = sync_blueprint_for_user(message)
            
            # 验证结果
            self.assertIsInstance(result, BlueprintSyncResult)
            self.assertEqual(result.logs[0], "信息收集状态已处理过，跳过重复处理")
    
    @patch('utils.video_learning_notifier.HSAITasks')
    def test_find_and_complete_video_task_success(self, mock_tasks):
        """测试成功查找并完成视频发布任务"""
        # 创建视频发布任务
        video_task = HSAITaskModel(
            id=self.task_id,
            title="视频发布任务",
            description="发布视频内容",
            task_type="platform_publishing",
            task_category="daily",
            status=HSAITaskStatus.IN_PROGRESS.value,
            user_id=self.user_id,
            project_id=self.project_id,
            config={"video_id": self.video_id},
            priority=10,
            created_at=int(datetime.now(timezone.utc).timestamp()),
            updated_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        completed_video_task = HSAITaskModel(
            id=self.task_id,
            title="已完成的视频发布任务",
            description="发布视频内容",
            task_type="platform_publishing",
            task_category="daily",
            status=HSAITaskStatus.COMPLETED.value,
            user_id=self.user_id,
            project_id=self.project_id,
            config={"video_id": self.video_id},
            priority=10,
            created_at=int(datetime.now(timezone.utc).timestamp()),
            updated_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        # 设置模拟返回值
        mock_tasks.get_tasks_by_user_id.return_value = [video_task]
        mock_tasks.update_task_by_id.return_value = completed_video_task
        
        # 调用被测试函数
        result = _find_and_complete_video_task(self.video_id, self.user_id)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result.status, HSAITaskStatus.COMPLETED.value)
        mock_tasks.update_task_by_id.assert_called_once()
    
    @patch('utils.video_learning_notifier.HSAITasks')
    def test_find_and_complete_video_task_not_found(self, mock_tasks):
        """测试未找到对应的视频发布任务"""
        # 创建不匹配的任务
        other_task = HSAITaskModel(
            id="other_task",
            title="其他任务",
            description="其他任务描述",
            task_type="other",
            task_category="main",
            status=HSAITaskStatus.IN_PROGRESS.value,
            user_id=self.user_id,
            project_id=self.project_id,
            config={"video_id": "other_video"},
            priority=10,
            created_at=int(datetime.now(timezone.utc).timestamp()),
            updated_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        # 设置模拟返回值
        mock_tasks.get_tasks_by_user_id.return_value = [other_task]
        
        # 调用被测试函数
        result = _find_and_complete_video_task(self.video_id, self.user_id)
        
        # 验证结果
        self.assertIsNone(result)
    
    @patch('utils.video_learning_notifier.HSAIVideoLearningStatuses')
    @patch('utils.video_learning_notifier.HSAIVideoLearningLogs')
    @patch('utils.video_learning_notifier._find_and_complete_video_task')
    def test_handle_video_learning_notification_success(self, mock_find_task, mock_logs, mock_statuses):
        """测试成功处理视频学习通知"""
        # 创建模拟消息
        message = {
            "video_id": self.video_id,
            "status": "success",
            "business_name": "HSAI",
            "user_id": self.user_id,
            "session_id": "test_session_123"
        }
        
        # 设置模拟返回值
        mock_statuses.get_status_by_business_and_video.return_value = None
        mock_statuses.upsert_status.return_value = MagicMock(status="learned")
        mock_logs.record_status_change.return_value = MagicMock()
        mock_find_task.return_value = self.mock_task
        
        # 注意：这是一个异步函数，需要特殊处理
        import asyncio
        # 创建异步事件循环来运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(handle_video_learning_notification(message))
        finally:
            loop.close()
        
        # 验证结果
        mock_statuses.upsert_status.assert_called_once()
        mock_find_task.assert_called_once_with(self.video_id, self.user_id)
    
    @patch('utils.video_learning_notifier.HSAIVideoLearningStatuses')
    @patch('utils.video_learning_notifier.HSAIVideoLearningLogs')
    def test_handle_video_learning_notification_failed(self, mock_logs, mock_statuses):
        """测试处理失败的视频学习通知"""
        # 创建模拟消息
        message = {
            "video_id": self.video_id,
            "status": "failed",
            "business_name": "HSAI",
            "user_id": self.user_id,
            "session_id": "test_session_123"
        }
        
        # 设置模拟返回值
        mock_statuses.get_status_by_business_and_video.return_value = None
        mock_statuses.mark_pending.return_value = MagicMock(status="pending")
        mock_logs.record_status_change.return_value = MagicMock()
        
        # 注意：这是一个异步函数，需要特殊处理
        import asyncio
        # 创建异步事件循环来运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(handle_video_learning_notification(message))
        finally:
            loop.close()
        
        # 验证结果
        mock_statuses.mark_pending.assert_called_once()
    
    def test_handle_video_learning_notification_invalid_status(self):
        """测试处理无效状态的视频学习通知"""
        # 创建模拟消息
        message = {
            "video_id": self.video_id,
            "status": "invalid_status",
            "business_name": "HSAI"
        }
        
        # 验证会记录错误日志但不会抛出异常
        with self.assertLogs('utils.video_learning_notifier', level='ERROR'):
            import asyncio
            # 创建异步事件循环来运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(handle_video_learning_notification(message))
            finally:
                loop.close()


if __name__ == '__main__':
    unittest.main()