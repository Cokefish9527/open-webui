import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch, mock_open
from open_webui.socket.hsai_events import register_hsai_events
from open_webui.models.files import Files, FileModel
from open_webui.models.attachments import AttachmentDescriptor
from open_webui.services.workflow_orchestration_center import workflow_orchestration_center
from open_webui.utils.n8n_client import N8NClient, ExecutionRequest


@pytest.mark.asyncio
async def test_websocket_attachment_forwarding():
    """测试WebSocket附件转发功能"""
    
    # 创建模拟的Socket.IO实例
    sio = Mock()
    sio.on = Mock()
    sio.emit = AsyncMock()
    
    # 注册HSAI事件
    register_hsai_events(sio, None)
    
    # 验证事件处理器已注册
    assert sio.on.call_count >= 1
    
    # 获取message事件处理器
    message_handler = None
    for call in sio.on.call_args_list:
        if call[0][0] == "message":
            message_handler = call[0][1]
            break
    
    assert message_handler is not None, "message事件处理器未注册"
    
    # 创建测试文件模型
    test_file = FileModel(
        id="file_test123",
        user_id="user_456",
        filename="test.pdf",
        path="/uploads/test.pdf",
        meta={
            "content_type": "application/pdf",
            "size": 102400
        },
        created_at=1234567890,
        updated_at=1234567890
    )
    
    # 模拟Files.get_file_by_id方法
    with patch.object(Files, 'get_file_by_id', return_value=test_file):
        # 模拟SESSION_POOL
        with patch('open_webui.socket.hsai_events.SESSION_POOL', {"sid_123": {"id": "user_456"}}):
            # 模拟Users.get_user_by_id方法
            with patch('open_webui.socket.hsai_events.Users.get_user_by_id') as mock_get_user:
                mock_user = Mock()
                mock_user.business_name = "TestBusiness"
                mock_user.info = {}
                mock_get_user.return_value = mock_user
                
                # 模拟Users.is_user_info_collection_completed方法
                with patch('open_webui.socket.hsai_events.Users.is_user_info_collection_completed', return_value=True):
                    # 模拟workflow_orchestration_center.process_request方法
                    with patch.object(workflow_orchestration_center, 'process_request', new=AsyncMock()) as mock_process_request:
                        # 创建测试消息数据，包含附件
                        test_data = {
                            "type": "chat",
                            "content": "请分析这个文件",
                            "session_id": "session_789",
                            "files": [
                                {
                                    "id": "file_test123"
                                }
                            ]
                        }
                        
                        # 调用message事件处理器
                        await message_handler("sid_123", test_data)
                        
                        # 验证process_request被调用
                        mock_process_request.assert_called_once()
                        
                        # 获取调用参数
                        call_args = mock_process_request.call_args
                        context = call_args[1]['context']
                        
                        # 验证附件已添加到context中
                        assert 'attachment' in context, "附件未添加到context中"
                        attachment = context['attachment']
                        assert isinstance(attachment, AttachmentDescriptor), "附件类型不正确"
                        assert attachment.file_id == "file_test123", "附件file_id不正确"
                        assert attachment.filename == "test.pdf", "附件filename不正确"
                        assert attachment.mime_type == "application/pdf", "附件mime_type不正确"
                        assert attachment.local_path == "/uploads/test.pdf", "附件local_path不正确"
                        assert attachment.size == 102400, "附件size不正确"


@pytest.mark.asyncio
async def test_n8n_client_with_attachment():
    """测试N8NClient处理附件功能"""
    
    # 创建N8NClient实例
    client = N8NClient()
    
    # 模拟aiohttp.ClientSession
    with patch.object(client, 'session') as mock_session:
        # 创建模拟响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json = AsyncMock(return_value={"status": "success"})
        
        # 创建模拟上下文管理器
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock()
        
        mock_session.post.return_value = mock_context_manager
        
        # 创建测试附件
        attachment = AttachmentDescriptor(
            file_id="file_test123",
            filename="test.pdf",
            mime_type="application/pdf",
            local_path="/uploads/test.pdf",
            size=102400
        )
        
        # 创建ExecutionRequest
        request = ExecutionRequest(
            workflow_id="test_workflow",
            session_id="session_789",
            user_id="user_456",
            message="请分析这个文件",
            attachment=attachment
        )
        
        # 模拟打开文件
        with patch('builtins.open', mock_open(read_data=b'test file content')):
            # 调用_execute_with_retry方法
            result = await client._execute_with_retry(
                url="http://test.n8n.local/webhook",
                payload={"message": "请分析这个文件"},
                timeout=30,
                max_retries=3,
                attachment=attachment
            )
            
            # 验证结果
            assert result == {"status": "success"}
            
            # 验证使用了multipart/form-data
            call_args = mock_session.post.call_args
            assert call_args[1]['data'] is not None, "未使用multipart/form-data发送请求"
            
            # 验证包含payload_json字段
            # 注意：由于FormData的特殊性，我们无法直接验证内容
            # 但在实际运行中，会包含payload_json和data字段


if __name__ == "__main__":
    pytest.main([__file__, "-v"])