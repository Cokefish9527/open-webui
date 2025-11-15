#!/usr/bin/env python3
"""
测试附件转发功能的调试脚本
"""

import asyncio
import logging
import json
from open_webui.models.attachments import AttachmentDescriptor
from open_webui.utils.n8n_client import ExecutionRequest

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_attachment_processing():
    """测试附件处理流程"""
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
    logger.info(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    # 验证附件信息是否正确处理
    logger.info(f"Request attachment: {request.attachment}")
    if request.attachment:
        logger.info(f"Attachment details: file_id={request.attachment.file_id}, filename={request.attachment.filename}, size={request.attachment.size}")
    
    logger.info("附件处理测试完成!")


if __name__ == "__main__":
    asyncio.run(test_attachment_processing())