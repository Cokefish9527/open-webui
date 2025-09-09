import logging
import json
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Boolean, Column, Text, String, JSON

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Functions DB Schema
####################


class Function(Base):
    __tablename__ = "function"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    user_id = Column(String)
    name = Column(Text)
    type = Column(Text)
    content = Column(Text)
    meta = Column(JSON)
    valves = Column(JSON)
    is_active = Column(Boolean)
    is_global = Column(Boolean)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class FunctionMeta(BaseModel):
    """函数元数据模型"""
    description: Optional[str] = Field(default=None, description="函数描述")
    manifest: Optional[dict] = Field(default=None, description="函数清单")


class FunctionModel(BaseModel):
    """函数模型"""
    id: str = Field(description="函数唯一标识符")
    user_id: str = Field(description="用户ID")
    name: str = Field(description="函数名称")
    type: str = Field(description="函数类型")
    content: str = Field(description="函数内容")
    meta: FunctionMeta = Field(description="函数元数据")
    is_active: bool = Field(default=False, description="是否激活")
    is_global: bool = Field(default=False, description="是否全局可用")
    updated_at: int = Field(description="更新时间戳")
    created_at: int = Field(description="创建时间戳")

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class FunctionResponse(BaseModel):
    """函数响应模型"""
    id: str = Field(description="函数唯一标识符")
    user_id: str = Field(description="用户ID")
    type: str = Field(description="函数类型")
    name: str = Field(description="函数名称")
    meta: FunctionMeta = Field(description="函数元数据")
    is_active: bool = Field(description="是否激活")
    is_global: bool = Field(description="是否全局可用")
    updated_at: int = Field(description="更新时间戳")
    created_at: int = Field(description="创建时间戳")


class FunctionForm(BaseModel):
    """函数表单模型"""
    id: str = Field(description="函数唯一标识符")
    name: str = Field(description="函数名称")
    content: str = Field(description="函数内容")
    meta: FunctionMeta = Field(description="函数元数据")


class FunctionValves(BaseModel):
    """函数阀门模型"""
    valves: Optional[dict] = Field(default=None, description="阀门配置")


class FunctionsTable:
    def insert_new_function(
        self, user_id: str, type: str, form_data: FunctionForm
    ) -> Optional[FunctionModel]:
        function = FunctionModel(
            **{
                **form_data.model_dump(),
                "user_id": user_id,
                "type": type,
                "updated_at": int(time.time()),
                "created_at": int(time.time()),
            }
        )

        try:
            with get_db() as db:
                result = Function(**function.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return FunctionModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            log.exception(f"Error creating a new function: {e}")
            return None

    def sync_functions(
        self, user_id: str, functions: list[FunctionModel]
    ) -> list[FunctionModel]:
        # Synchronize functions for a user by updating existing ones, inserting new ones, and removing those that are no longer present.
        try:
            with get_db() as db:
                # Get existing functions
                existing_functions = db.query(Function).all()
                existing_ids = {func.id for func in existing_functions}

                # Prepare a set of new function IDs
                new_function_ids = {func.id for func in functions}

                # Update or insert functions
                for func in functions:
                    if func.id in existing_ids:
                        db.query(Function).filter_by(id=func.id).update(
                            {
                                **func.model_dump(),
                                "user_id": user_id,
                                "updated_at": int(time.time()),
                            }
                        )
                    else:
                        new_func = Function(
                            **{
                                **func.model_dump(),
                                "user_id": user_id,
                                "updated_at": int(time.time()),
                            }
                        )
                        db.add(new_func)

                # Remove functions that are no longer present
                for func in existing_functions:
                    if func.id not in new_function_ids:
                        db.delete(func)

                db.commit()

                return [
                    FunctionModel.model_validate(func)
                    for func in db.query(Function).all()
                ]
        except Exception as e:
            log.exception(f"Error syncing functions for user {user_id}: {e}")
            return []

    def get_function_by_id(self, id: str) -> Optional[FunctionModel]:
        try:
            with get_db() as db:
                function = db.get(Function, id)
                return FunctionModel.model_validate(function)
        except Exception:
            return None

    def get_functions(self, active_only=False) -> list[FunctionModel]:
        with get_db() as db:
            if active_only:
                return [
                    FunctionModel.model_validate(function)
                    for function in db.query(Function).filter_by(is_active=True).all()
                ]
            else:
                return [
                    FunctionModel.model_validate(function)
                    for function in db.query(Function).all()
                ]

    def get_functions_by_type(
        self, type: str, active_only=False
    ) -> list[FunctionModel]:
        with get_db() as db:
            if active_only:
                return [
                    FunctionModel.model_validate(function)
                    for function in db.query(Function)
                    .filter_by(type=type, is_active=True)
                    .all()
                ]
            else:
                return [
                    FunctionModel.model_validate(function)
                    for function in db.query(Function).filter_by(type=type).all()
                ]

    def get_global_filter_functions(self) -> list[FunctionModel]:
        with get_db() as db:
            return [
                FunctionModel.model_validate(function)
                for function in db.query(Function)
                .filter_by(type="filter", is_active=True, is_global=True)
                .all()
            ]

    def get_global_action_functions(self) -> list[FunctionModel]:
        with get_db() as db:
            return [
                FunctionModel.model_validate(function)
                for function in db.query(Function)
                .filter_by(type="action", is_active=True, is_global=True)
                .all()
            ]

    def get_function_valves_by_id(self, id: str) -> Optional[dict]:
        with get_db() as db:
            try:
                function = db.get(Function, id)
                return function.valves if function.valves else {}
            except Exception as e:
                log.exception(f"Error getting function valves by id {id}: {e}")
                return None

    def update_function_valves_by_id(
        self, id: str, valves: dict
    ) -> Optional[FunctionValves]:
        with get_db() as db:
            try:
                function = db.get(Function, id)
                function.valves = valves
                function.updated_at = int(time.time())
                db.commit()
                db.refresh(function)
                return self.get_function_by_id(id)
            except Exception:
                return None

    def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "functions" and "valves" settings
            if "functions" not in user_settings:
                user_settings["functions"] = {}
            if "valves" not in user_settings["functions"]:
                user_settings["functions"]["valves"] = {}

            return user_settings["functions"]["valves"].get(id, {})
        except Exception as e:
            log.exception(
                f"Error getting user values by id {id} and user id {user_id}: {e}"
            )
            return None

    def update_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, valves: dict
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "functions" and "valves" settings
            if "functions" not in user_settings:
                user_settings["functions"] = {}
            if "valves" not in user_settings["functions"]:
                user_settings["functions"]["valves"] = {}

            user_settings["functions"]["valves"][id] = valves

            # Update the user settings in the database
            Users.update_user_by_id(user_id, {"settings": user_settings})

            return user_settings["functions"]["valves"][id]
        except Exception as e:
            log.exception(
                f"Error updating user valves by id {id} and user_id {user_id}: {e}"
            )
            return None

    def update_function_by_id(self, id: str, updated: dict) -> Optional[FunctionModel]:
        with get_db() as db:
            try:
                db.query(Function).filter_by(id=id).update(
                    {
                        **updated,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_function_by_id(id)
            except Exception:
                return None

    def deactivate_all_functions(self) -> Optional[bool]:
        with get_db() as db:
            try:
                db.query(Function).update(
                    {
                        "is_active": False,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return True
            except Exception:
                return None

    def delete_function_by_id(self, id: str) -> bool:
        with get_db() as db:
            try:
                db.query(Function).filter_by(id=id).delete()
                db.commit()

                return True
            except Exception:
                return False


Functions = FunctionsTable()
