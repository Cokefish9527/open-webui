"""
测试business_name实现
"""

import unittest
from unittest.mock import patch, MagicMock
from open_webui.utils.n8n_client import ExecutionRequest


class TestBusinessNameImplementation(unittest.TestCase):
    
    def setUp(self):
        """测试前准备"""
        pass
        
    @patch('open_webui.utils.n8n_client.Users')
    @patch('open_webui.utils.n8n_client.CONFIG_BUSINESS_NAME')
    def test_business_name_from_request(self, mock_config, mock_users):
        """测试从请求中获取business_name"""
        # 模拟配置
        mock_config.value = "HSAI"
        
        # 创建ExecutionRequest实例
        request = ExecutionRequest(
            workflow_id="test_workflow",
            session_id="test_session",
            user_id="test_user",
            message="test_message",
            business_name="Test Company"  # 直接提供business_name
        )
        
        # 调用to_webhook_payload方法
        payload = request.to_webhook_payload()
        
        # 验证结果
        self.assertEqual(payload["business_name"], "Test Company")
        
    @patch('open_webui.utils.n8n_client.Users')
    @patch('open_webui.utils.n8n_client.CONFIG_BUSINESS_NAME')
    def test_business_name_from_company(self, mock_config, mock_users):
        """测试从用户公司获取business_name"""
        # 模拟配置
        mock_config.value = "HSAI"
        
        # 模拟用户公司
        mock_company = MagicMock()
        mock_company.business_name = "Company from DB"
        mock_users.get_user_company.return_value = mock_company
        
        # 创建ExecutionRequest实例，不提供business_name
        request = ExecutionRequest(
            workflow_id="test_workflow",
            session_id="test_session",
            user_id="test_user",
            message="test_message"
            # 不提供business_name
        )
        
        # 调用to_webhook_payload方法
        payload = request.to_webhook_payload()
        
        # 验证结果
        self.assertEqual(payload["business_name"], "Company from DB")
        
    @patch('open_webui.utils.n8n_client.Users')
    @patch('open_webui.utils.n8n_client.CONFIG_BUSINESS_NAME')
    def test_business_name_from_config(self, mock_config, mock_users):
        """测试从配置获取business_name"""
        # 模拟配置
        mock_config.value = "HSAI"
        
        # 模拟用户没有关联公司
        mock_users.get_user_company.return_value = None
        
        # 创建ExecutionRequest实例，不提供business_name
        request = ExecutionRequest(
            workflow_id="test_workflow",
            session_id="test_session",
            user_id="test_user",
            message="test_message"
            # 不提供business_name
        )
        
        # 调用to_webhook_payload方法
        payload = request.to_webhook_payload()
        
        # 验证结果
        self.assertEqual(payload["business_name"], "HSAI")
        
    @patch('open_webui.utils.n8n_client.Users')
    @patch('open_webui.utils.n8n_client.CONFIG_BUSINESS_NAME')
    def test_business_name_missing(self, mock_config, mock_users):
        """测试缺少business_name时抛出异常"""
        # 模拟配置为空
        mock_config.value = ""
        
        # 模拟用户没有关联公司
        mock_users.get_user_company.return_value = None
        
        # 创建ExecutionRequest实例，不提供business_name
        request = ExecutionRequest(
            workflow_id="test_workflow",
            session_id="test_session",
            user_id="test_user",
            message="test_message"
            # 不提供business_name
        )
        
        # 验证抛出异常
        with self.assertRaises(ValueError) as context:
            request.to_webhook_payload()
            
        self.assertTrue("business_name字段是必需的，但未提供" in str(context.exception))


if __name__ == '__main__':
    unittest.main()