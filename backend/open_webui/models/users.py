import time
from typing import List, Optional

from open_webui.internal.db import Base, JSONField, get_db


from open_webui.models.chats import Chats
from open_webui.models.groups import Groups


from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Boolean, Column, String, Text
from sqlalchemy import or_


####################
# User DB Schema
####################


class User(Base):
    __tablename__ = "user"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
    role = Column(String)
    profile_image_url = Column(Text)

    last_active_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

    api_key = Column(String, nullable=True, unique=True)
    settings = Column(JSONField, nullable=True)
    info = Column(JSONField, nullable=True)
    
    # 添加信息收集完成标志位字段
    info_collection_completed = Column(Boolean, default=False, nullable=False)
    
    # 添加公司名称字段
    business_name = Column(String, nullable=True)

    oauth_sub = Column(Text, unique=True)


class UserSettings(BaseModel):
    ui: Optional[dict] = {}
    model_config = ConfigDict(extra="allow")
    pass


class UserModel(BaseModel):
    """用户模型"""
    id: str = Field(description="用户唯一标识符")
    name: str = Field(description="用户名")
    email: str = Field(description="用户邮箱")
    role: str = Field(default="pending", description="用户角色")
    profile_image_url: str = Field(description="用户头像URL")
    last_active_at: int = Field(description="最后活跃时间戳")
    updated_at: int = Field(description="更新时间戳")
    created_at: int = Field(description="创建时间戳")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    settings: Optional[UserSettings] = Field(default=None, description="用户设置")
    info: Optional[dict] = Field(default=None, description="用户信息")
    # 添加信息收集完成标志位字段
    info_collection_completed: bool = Field(default=False, description="信息收集是否完成")
    # 添加公司名称字段
    business_name: Optional[str] = Field(default=None, description="公司名称")
    oauth_sub: Optional[str] = Field(default=None, description="OAuth子标识符")

    model_config = ConfigDict(from_attributes=True, extra="allow")


####################
# Forms
####################


class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: List[UserModel] = Field(description="用户列表")
    total: int = Field(description="用户总数")


class UserResponse(BaseModel):
    """用户信息响应模型"""
    id: str = Field(description="用户唯一标识符")
    name: str = Field(description="用户名")
    email: str = Field(description="用户邮箱")
    role: str = Field(description="用户角色")
    profile_image_url: str = Field(description="用户头像URL")
    business_name: Optional[str] = Field(default=None, description="公司名称")


class UserNameResponse(BaseModel):
    """用户名信息响应模型"""
    id: str = Field(description="用户唯一标识符")
    name: str = Field(description="用户名")
    role: str = Field(description="用户角色")
    profile_image_url: str = Field(description="用户头像URL")


class UserRoleUpdateForm(BaseModel):
    id: str
    role: str


class UserUpdateForm(BaseModel):
    role: str
    name: str
    email: str
    profile_image_url: str
    password: Optional[str] = None
    credit: Optional[float] = None


class UserCreditUpdateForm(BaseModel):
    amount: Optional[float] = None
    credit: Optional[float] = None


class UsersTable:
    def insert_new_user(
        self,
        id: str,
        name: str,
        email: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: Optional[str] = None,
    ) -> Optional[UserModel]:
        with get_db() as db:
            user = UserModel(
                **{
                    "id": id,
                    "name": name,
                    "email": email,
                    "role": role,
                    "profile_image_url": profile_image_url,
                    "last_active_at": int(time.time()),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "oauth_sub": oauth_sub,
                    # 新用户默认信息收集未完成
                    "info_collection_completed": False,
                    # 新用户默认business_name为None
                    "business_name": None,
                }
            )
            result = User(**user.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return user
            else:
                return None

    def get_user_by_id(self, id: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
                if user:
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    def get_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(api_key=api_key).first()
                if user:
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(email=email).first()
                if user:
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    def get_user_by_oauth_sub(self, sub: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(oauth_sub=sub).first()
                if user:
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    def get_users(
        self,
        filter: Optional[dict] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> UserListResponse:
        with get_db() as db:
            query = db.query(User)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(
                        or_(
                            User.name.ilike(f"%{query_key}%"),
                            User.email.ilike(f"%{query_key}%"),
                        )
                    )

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by == "name":
                    if direction == "asc":
                        query = query.order_by(User.name.asc())
                    else:
                        query = query.order_by(User.name.desc())
                elif order_by == "email":
                    if direction == "asc":
                        query = query.order_by(User.email.asc())
                    else:
                        query = query.order_by(User.email.desc())

                elif order_by == "created_at":
                    if direction == "asc":
                        query = query.order_by(User.created_at.asc())
                    else:
                        query = query.order_by(User.created_at.desc())

                elif order_by == "last_active_at":
                    if direction == "asc":
                        query = query.order_by(User.last_active_at.asc())
                    else:
                        query = query.order_by(User.last_active_at.desc())

                elif order_by == "updated_at":
                    if direction == "asc":
                        query = query.order_by(User.updated_at.asc())
                    else:
                        query = query.order_by(User.updated_at.desc())
                elif order_by == "role":
                    if direction == "asc":
                        query = query.order_by(User.role.asc())
                    else:
                        query = query.order_by(User.role.desc())

            else:
                query = query.order_by(User.created_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            users = query.all()
            return UserListResponse(
                users=[UserModel.model_validate(user) for user in users],
                total=db.query(User).count(),
            )

    def get_users_by_user_ids(self, user_ids: List[str]) -> List[UserModel]:
        with get_db() as db:
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            return [UserModel.model_validate(user) for user in users]

    def get_num_users(self) -> Optional[int]:
        with get_db() as db:
            return db.query(User).count()

    def get_first_user(self) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).order_by(User.created_at).first()
                if user:
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    def get_user_webhook_url_by_id(self, id: str) -> Optional[str]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
                if user and user.settings is not None:
                    return (
                        user.settings.get("ui", {})
                        .get("notifications", {})
                        .get("webhook_url", None)
                    )
                return None
        except Exception:
            return None

    def update_user_role_by_id(self, id: str, role: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({"role": role})
                db.commit()
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_profile_image_url_by_id(
        self, id: str, profile_image_url: str
    ) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update(
                    {"profile_image_url": profile_image_url}
                )
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_last_active_by_id(self, id: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update(
                    {"last_active_at": int(time.time())}
                )
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_oauth_sub_by_id(
        self, id: str, oauth_sub: str
    ) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({"oauth_sub": oauth_sub})
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_by_id(self, id: str, updated: dict) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update(updated)
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
                # return UserModel(**user.dict())
        except Exception:
            return None

    def update_user_settings_by_id(self, id: str, updated: dict) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
                if user:
                    user_settings = user.settings

                    if user_settings is None:
                        user_settings = {}

                    user_settings.update(updated)

                    db.query(User).filter_by(id=id).update({"settings": user_settings})
                    db.commit()

                    updated_user = db.query(User).filter_by(id=id).first()
                    return UserModel.model_validate(updated_user)
                return None
        except Exception:
            return None

    def delete_user_by_id(self, id: str) -> bool:
        try:
            # Remove User from Groups
            Groups.remove_user_from_all_groups(id)

            # Delete User Chats
            result = Chats.delete_chats_by_user_id(id)
            if result:
                with get_db() as db:
                    # Delete User
                    db.query(User).filter_by(id=id).delete()
                    db.commit()

                return True
            else:
                return False
        except Exception:
            return False

    def update_user_api_key_by_id(self, id: str, api_key: str) -> bool:
        try:
            with get_db() as db:
                result = db.query(User).filter_by(id=id).update({"api_key": api_key})
                db.commit()
                return True if result == 1 else False
        except Exception:
            return False

    def get_user_api_key_by_id(self, id: str) -> Optional[str]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
                if user:
                    api_key = user.api_key
                    return str(api_key) if api_key is not None else None
                return None
        except Exception:
            return None

    def get_valid_user_ids(self, user_ids: List[str]) -> List[str]:
        with get_db() as db:
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            return [str(user.id) for user in users]

    def get_super_admin_user(self) -> Optional[UserModel]:
        with get_db() as db:
            user = db.query(User).filter_by(role="admin").first()
            if user:
                return UserModel.model_validate(user)
            else:
                return None

    def update_user_info_collection_status(self, id: str, completed: bool) -> Optional[UserModel]:
        """更新用户信息收集完成状态"""
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({"info_collection_completed": completed})
                db.commit()
                user = db.query(User).filter_by(id=id).first()
                if user:
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None
    
    def update_user_business_name_by_id(self, id: str, business_name: str) -> Optional[UserModel]:
        """更新用户公司名称"""
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({"business_name": business_name})
                db.commit()
                user = db.query(User).filter_by(id=id).first()
                if user:
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None
    
    def is_user_info_collection_completed(self, id: str) -> bool:
        """检查用户信息收集是否完成"""
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
                if user:
                    return bool(user.info_collection_completed)
                return False
        except Exception:
            return False


Users = UsersTable()
