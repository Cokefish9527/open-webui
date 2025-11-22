#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战略蓝图集成测试
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# 添加项目路径
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from open_webui.services.blueprint_sync_service import sync_blueprint_for_user
from open_webui.utils.conversation_queue_handler import handle_conversation_agent_message
from open_webui.models.hsai_blueprint_progress import HSAIBlueprintProgressModel


class TestBlueprintIntegration(unittest.TestCase):
    
    def setUp(self):
        """测试前准备"""
        pass
    
    def tearDown(self):
        """测试后清理"""
        pass
    
    @patch('open_webui.utils.conversation_queue_handler.sync_blueprint_for_user')
    @patch('open_webui.utils.conversation_queue_handler.Users')
    def test_handle_conversation_agent_message_blueprint_content(self, mock_users, mock_sync_blueprint):
        """测试处理蓝图内容消息的集成流程"""
        # 模拟用户信息收集状态
        mock_users.is_user_info_collection_completed.return_value = False
        
        # 模拟蓝图同步结果
        mock_result = MagicMock()
        mock_result.logs = ["测试日志"]
        mock_result.notifications = []
        mock_result.progress = MagicMock()
        mock_sync_blueprint.return_value = mock_result
        
        # 模拟消息
        message = {
            "user_id": "test_user_id",
            "content_type": "blue_image_content",
            "status": "FINISHED",
            "session_id": "test_session_id"
        }
        
        # 模拟Socket.IO
        with patch('open_webui.utils.conversation_queue_handler.sio') as mock_sio, \
             patch('open_webui.utils.conversation_queue_handler.SESSION_POOL', {}), \
             patch('open_webui.utils.conversation_queue_handler.USER_POOL', {}):
            
            mock_sio.emit = MagicMock()
            
            # 调用函数
            import asyncio
            # 使用asyncio.run来运行异步函数
            try:
                asyncio.run(handle_conversation_agent_message(message))
            except Exception as e:
                # 忽略Socket.IO未初始化的错误
                if "Socket.IO is not initialized" not in str(e):
                    raise
            
            # 验证调用了蓝图同步函数
            mock_sync_blueprint.assert_called_once()
    
    @patch('open_webui.utils.conversation_queue_handler.Users')
    def test_handle_conversation_agent_message_blue_image_first_time(self, mock_users):
        """测试首次处理blue_image消息"""
        # 模拟用户信息收集状态为未完成
        mock_users.is_user_info_collection_completed.return_value = False
        mock_users.update_user_info_collection_status.return_value = None
        
        # 模拟消息
        message = {
            "user_id": "test_user_id",
            "content_type": "blue_image",
            "status": "FINISHED",
            "session_id": "test_session_id"
        }
        
        # 模拟Socket.IO
        with patch('open_webui.utils.conversation_queue_handler.sio') as mock_sio, \
             patch('open_webui.utils.conversation_queue_handler.SESSION_POOL', {}), \
             patch('open_webui.utils.conversation_queue_handler.USER_POOL', {}), \
             patch('open_webui.utils.conversation_queue_handler.ensure_company_project_and_main_tasks') as mock_ensure_project:
            
            mock_sio.emit = MagicMock()
            mock_ensure_project.return_value = {"status": "success"}
            
            # 调用函数
            import asyncio
            # 使用asyncio.run来运行异步函数
            try:
                asyncio.run(handle_conversation_agent_message(message))
            except Exception as e:
                # 忽略Socket.IO未初始化的错误
                if "Socket.IO is not initialized" not in str(e):
                    raise
            
            # 验证调用了更新用户信息收集状态的方法
            mock_users.update_user_info_collection_status.assert_called_once_with("test_user_id", True)
            # 验证调用了确保项目和任务的方法
            mock_ensure_project.assert_called_once_with("test_user_id")
    
    @patch('open_webui.utils.conversation_queue_handler.Users')
    def test_handle_conversation_agent_message_blue_image_duplicate(self, mock_users):
        """测试重复处理blue_image消息"""
        # 模拟用户信息收集状态为已完成
        mock_users.is_user_info_collection_completed.return_value = True
        
        # 模拟消息
        message = {
            "user_id": "test_user_id",
            "content_type": "blue_image",
            "status": "FINISHED",
            "session_id": "test_session_id"
        }
        
        # 模拟Socket.IO
        with patch('open_webui.utils.conversation_queue_handler.sio') as mock_sio, \
             patch('open_webui.utils.conversation_queue_handler.SESSION_POOL', {}), \
             patch('open_webui.utils.conversation_queue_handler.USER_POOL', {}), \
             patch('open_webui.utils.conversation_queue_handler.ensure_company_project_and_main_tasks') as mock_ensure_project:
            
            mock_sio.emit = MagicMock()
            
            # 调用函数
            import asyncio
            # 使用asyncio.run来运行异步函数
            try:
                asyncio.run(handle_conversation_agent_message(message))
            except Exception as e:
                # 忽略Socket.IO未初始化的错误
                if "Socket.IO is not initialized" not in str(e):
                    raise
            
            # 验证没有调用更新用户信息收集状态的方法
            mock_users.update_user_info_collection_status.assert_not_called()
            # 验证没有调用确保项目和任务的方法
            mock_ensure_project.assert_not_called()


if __name__ == '__main__':
    unittest.main()