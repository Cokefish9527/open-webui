#!/usr/bin/env python3
"""
测试附件转发功能的脚本
"""

import asyncio
import logging
from open_webui.models.attachments import AttachmentDescriptor
from open_webui.utils.n8n_client import ExecutionRequest

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_attachment_payload():
    """测试附件负载生成"""
    # 创建附件描述符
    attachment = AttachmentDescriptor(
        file_id="file_1234567890",
        filename="test.pdf",
        mime_type="application/pdf",
        local_path="/uploads/test.pdf",
        size=102400
    )
    
    # 创建执行请求
    request = ExecutionRequest(
        workflow_id="test_workflow",
        session_id="session_789",
        user_id="user_456",
        message="请分析这个文件",
        attachment=attachment
    )
    
    # 生成webhook负载
    payload = request.to_webhook_payload()
    
    # 打印负载信息
    logger.info("Generated webhook payload:")
    logger.info(f"Payload: {payload}")
    
    # 验证附件信息是否正确包含在负载中
    assert "attachment" in payload, "附件信息未包含在负载中"
    assert payload["attachment"]["file_id"] == "file_1234567890", "文件ID不正确"
    assert payload["attachment"]["filename"] == "test.pdf", "文件名不正确"
    assert payload["attachment"]["mime_type"] == "application/pdf", "MIME类型不正确"
    assert payload["attachment"]["size"] == 102400, "文件大小不正确"
    
    logger.info("附件负载测试通过!")


if __name__ == "__main__":
    asyncio.run(test_attachment_payload())