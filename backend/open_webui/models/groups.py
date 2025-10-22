import json
import logging
import time
from typing import List, Optional
import uuid

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from open_webui.models.files import FileMetadataResponse


from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import BigInteger, Column, String, Text, JSON, func, ForeignKey
from ._timestamp_utils import normalize_required_timestamp


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# UserGroup DB Schema
####################


class Group(Base):
    __tablename__ = "group"
    __table_args__ = {'extend_existing': True}

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    permissions = Column(JSON, nullable=True)
    user_ids = Column(JSON, nullable=True)
    
    # 组织关联字段
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class GroupModel(BaseModel):
    """用户组模型"""
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(description="组唯一标识符")
    user_id: str = Field(description="用户ID")
    name: str = Field(description="组名称")
    description: str = Field(description="组描述")
    data: Optional[dict] = Field(default=None, description="数据")
    meta: Optional[dict] = Field(default=None, description="元数据")
    permissions: Optional[dict] = Field(default=None, description="权限设置")
    user_ids: List[str] = Field(default=[], description="用户ID列表")
    # 组织关联字段
    organization_id: Optional[str] = Field(default=None, description="所属组织ID")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_required_timestamps(cls, value):
        if value is None:
            raise ValueError("Timestamp value cannot be None")
        try:
            return normalize_required_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp value: {exc}") from exc


####################
# Forms
####################


class GroupResponse(BaseModel):
    """用户组响应模型"""
    id: str = Field(description="组唯一标识符")
    user_id: str = Field(description="用户ID")
    name: str = Field(description="组名称")
    description: str = Field(description="组描述")
    permissions: Optional[dict] = Field(default=None, description="权限设置")
    data: Optional[dict] = Field(default=None, description="数据")
    meta: Optional[dict] = Field(default=None, description="元数据")
    user_ids: List[str] = Field(default=[], description="用户ID列表")
    # 组织关联字段
    organization_id: Optional[str] = Field(default=None, description="所属组织ID")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class GroupForm(BaseModel):
    """用户组表单模型"""
    name: str = Field(description="组名称")
    description: str = Field(description="组描述")
    permissions: Optional[dict] = Field(default=None, description="权限设置")
    # 组织关联字段
    organization_id: Optional[str] = Field(default=None, description="所属组织ID")


class GroupUpdateForm(GroupForm):
    """用户组更新表单模型"""
    user_ids: Optional[List[str]] = Field(default=None, description="用户ID列表")


class GroupTable:
    def insert_new_group(
        self, user_id: str, form_data: GroupForm
    ) -> Optional[GroupModel]:
        with get_db() as db:
            group = GroupModel(
                **{
                    **form_data.model_dump(exclude_none=True),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Group(**group.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return GroupModel.model_validate(result)
                else:
                    return None

            except Exception:
                return None

    def get_groups(self, organization_id: Optional[str] = None) -> List[GroupModel]:
        with get_db() as db:
            query = db.query(Group)
            
            # 如果指定了组织ID，只返回该组织的组
            if organization_id:
                query = query.filter_by(organization_id=organization_id)
                
            return [
                GroupModel.model_validate(group)
                for group in query.order_by(Group.updated_at.desc()).all()
            ]

    def get_groups_by_member_id(self, user_id: str, organization_id: Optional[str] = None) -> List[GroupModel]:
        with get_db() as db:
            query = db.query(Group).filter(Group.user_ids.isnot(None))

            if organization_id:
                query = query.filter_by(organization_id=organization_id)

            groups: List[GroupModel] = []
            for group in query.order_by(Group.updated_at.desc()).all():
                try:
                    group_model = GroupModel.model_validate(group)
                except Exception:
                    continue

                if group_model.user_ids and user_id in group_model.user_ids:
                    groups.append(group_model)

            return groups

    def get_group_by_id(self, id: str) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                group = db.query(Group).filter_by(id=id).first()
                return GroupModel.model_validate(group) if group else None
        except Exception:
            return None

    def get_group_user_ids_by_id(self, id: str) -> Optional[List[str]]:
        group = self.get_group_by_id(id)
        if group:
            return group.user_ids
        else:
            return None

    def update_group_by_id(
        self, id: str, form_data: GroupUpdateForm, overwrite: bool = False
    ) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                db.query(Group).filter_by(id=id).update(
                    {
                        **form_data.model_dump(exclude_none=True),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_group_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    def delete_group_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Group).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_all_groups(self) -> bool:
        with get_db() as db:
            try:
                db.query(Group).delete()
                db.commit()

                return True
            except Exception:
                return False

    def remove_user_from_all_groups(self, user_id: str) -> bool:
        with get_db() as db:
            try:
                groups = self.get_groups_by_member_id(user_id)

                for group in groups:
                    group.user_ids.remove(user_id)
                    db.query(Group).filter_by(id=group.id).update(
                        {
                            "user_ids": group.user_ids,
                            "updated_at": int(time.time()),
                        }
                    )
                    db.commit()

                return True
            except Exception:
                return False

    def create_groups_by_group_names(
        self, user_id: str, group_names: List[str], organization_id: Optional[str] = None
    ) -> List[GroupModel]:

        # check for existing groups
        existing_groups = self.get_groups(organization_id)
        existing_group_names = {group.name for group in existing_groups}

        new_groups = []

        with get_db() as db:
            for group_name in group_names:
                if group_name not in existing_group_names:
                    new_group = GroupModel(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        name=group_name,
                        description="",
                        organization_id=organization_id,
                        created_at=int(time.time()),
                        updated_at=int(time.time()),
                    )
                    try:
                        result = Group(**new_group.model_dump())
                        db.add(result)
                        db.commit()
                        db.refresh(result)
                        new_groups.append(GroupModel.model_validate(result))
                    except Exception as e:
                        log.exception(e)
                        continue
            return new_groups

    def sync_groups_by_group_names(self, user_id: str, group_names: List[str], organization_id: Optional[str] = None) -> bool:
        with get_db() as db:
            try:
                query = db.query(Group).filter(Group.name.in_(group_names))
                
                # 如果指定了组织ID，只在该组织内查找组
                if organization_id:
                    query = query.filter_by(organization_id=organization_id)
                    
                groups = query.all()
                group_ids = [group.id for group in groups]

                # Remove user from groups not in the new list
                existing_groups = self.get_groups_by_member_id(user_id, organization_id)

                for group in existing_groups:
                    if group.id not in group_ids:
                        group.user_ids.remove(user_id)
                        db.query(Group).filter_by(id=group.id).update(
                            {
                                "user_ids": group.user_ids,
                                "updated_at": int(time.time()),
                            }
                        )

                # Add user to new groups
                for group in groups:
                    if user_id not in group.user_ids:
                        group.user_ids.append(user_id)
                        db.query(Group).filter_by(id=group.id).update(
                            {
                                "user_ids": group.user_ids,
                                "updated_at": int(time.time()),
                            }
                        )

                db.commit()
                return True
            except Exception as e:
                log.exception(e)
                return False


Groups = GroupTable()
