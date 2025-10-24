import logging
import time
from typing import Dict, List, Optional

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS
from ._timestamp_utils import EpochTimestamp
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, String, Text, JSON

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Files DB Schema
####################


class File(Base):
    __tablename__ = "file"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    user_id = Column(String)
    hash = Column(Text, nullable=True)

    filename = Column(Text)
    path = Column(Text, nullable=True)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    access_control = Column(JSON, nullable=True)

    created_at = Column(EpochTimestamp())
    updated_at = Column(EpochTimestamp())


class FileModel(BaseModel):
    """文件模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="文件唯一标识符")
    user_id: str = Field(description="用户ID")
    hash: Optional[str] = Field(default=None, description="文件哈希值")
    filename: str = Field(description="文件名")
    path: Optional[str] = Field(default=None, description="文件路径")
    data: Optional[dict] = Field(default=None, description="文件数据")
    meta: Optional[dict] = Field(default=None, description="文件元数据")
    access_control: Optional[dict] = Field(default=None, description="访问控制设置")
    created_at: Optional[int] = Field(default=None, description="创建时间戳")
    updated_at: Optional[int] = Field(default=None, description="更新时间戳")


####################
# Forms
####################


class FileMeta(BaseModel):
    """文件元数据模型"""
    name: Optional[str] = Field(default=None, description="文件名")
    content_type: Optional[str] = Field(default=None, description="内容类型")
    size: Optional[int] = Field(default=None, description="文件大小(字节)")


class FileModelResponse(BaseModel):
    """文件模型响应"""
    id: str = Field(description="文件唯一标识符")
    user_id: str = Field(description="用户ID")
    hash: Optional[str] = Field(default=None, description="文件哈希值")
    filename: str = Field(description="文件名")
    data: Optional[dict] = Field(default=None, description="文件数据")
    meta: FileMeta = Field(description="文件元数据")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")

    model_config = ConfigDict(extra="allow")


class FileMetadataResponse(BaseModel):
    """文件元数据响应"""
    id: str = Field(description="文件唯一标识符")
    meta: dict = Field(description="文件元数据")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class FileForm(BaseModel):
    id: str
    hash: Optional[str] = None
    filename: str
    path: str
    data: dict = {}
    meta: dict = {}
    access_control: Optional[dict] = None


class FilesTable:
    def insert_new_file(self, user_id: str, form_data: FileForm) -> Optional[FileModel]:
        with get_db() as db:
            file = FileModel(
                **{
                    **form_data.model_dump(),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = File(**file.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return FileModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error inserting a new file: {e}")
                return None

    def get_file_by_id(self, id: str) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.get(File, id)
                return FileModel.model_validate(file)
            except Exception:
                return None

    def get_file_metadata_by_id(self, id: str) -> Optional[FileMetadataResponse]:
        with get_db() as db:
            try:
                file = db.get(File, id)
                return FileMetadataResponse(
                    id=file.id,
                    meta=file.meta,
                    created_at=file.created_at,
                    updated_at=file.updated_at,
                )
            except Exception:
                return None

    def get_files(self) -> List[FileModel]:
        with get_db() as db:
            return [FileModel.model_validate(file) for file in db.query(File).all()]

    def get_files_by_ids(self, ids: List[str]) -> List[FileModel]:
        with get_db() as db:
            return [
                FileModel.model_validate(file)
                for file in db.query(File)
                .filter(File.id.in_(ids))
                .order_by(File.updated_at.desc())
                .all()
            ]

    def get_file_metadatas_by_ids(self, ids: List[str]) -> List[FileMetadataResponse]:
        with get_db() as db:
            return [
                FileMetadataResponse(
                    id=file.id,
                    meta=file.meta,
                    created_at=file.created_at,
                    updated_at=file.updated_at,
                )
                for file in db.query(File)
                .filter(File.id.in_(ids))
                .order_by(File.updated_at.desc())
                .all()
            ]

    def get_files_by_user_id(self, user_id: str) -> List[FileModel]:
        with get_db() as db:
            return [
                FileModel.model_validate(file)
                for file in db.query(File).filter_by(user_id=user_id).all()
            ]

    def update_file_hash_by_id(self, id: str, hash: str) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                file.hash = hash
                db.commit()

                return FileModel.model_validate(file)
            except Exception:
                return None

    def update_file_data_by_id(self, id: str, data: dict) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                file.data = {**(file.data if file.data else {}), **data}
                db.commit()
                return FileModel.model_validate(file)
            except Exception as e:

                return None

    def update_file_metadata_by_id(self, id: str, meta: dict) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                file.meta = {**(file.meta if file.meta else {}), **meta}
                db.commit()
                return FileModel.model_validate(file)
            except Exception:
                return None

    def delete_file_by_id(self, id: str) -> bool:
        with get_db() as db:
            try:
                db.query(File).filter_by(id=id).delete()
                db.commit()

                return True
            except Exception:
                return False

    def delete_all_files(self) -> bool:
        with get_db() as db:
            try:
                db.query(File).delete()
                db.commit()

                return True
            except Exception:
                return False


Files = FilesTable()
