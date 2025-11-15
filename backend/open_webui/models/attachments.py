import logging
from typing import Optional
from pydantic import BaseModel, Field
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class AttachmentDescriptor(BaseModel):
    """附件描述对象"""
    file_id: str = Field(description="文件唯一标识符")
    filename: str = Field(description="文件名")
    mime_type: Optional[str] = Field(default=None, description="MIME类型")
    local_path: str = Field(description="本地文件路径")
    size: int = Field(description="文件大小(字节)")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "file_id": "file_1234567890",
                    "filename": "example.pdf",
                    "mime_type": "application/pdf",
                    "local_path": "/uploads/example.pdf",
                    "size": 102400
                }
            ]
        }
    }