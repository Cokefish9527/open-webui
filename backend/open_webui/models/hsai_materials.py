import logging
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# HSAI Materials DB Schema
####################


class HSAIMaterialFolder(Base):
    """HSAI素材文件夹表"""
    __tablename__ = "hsai_material_folders"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # 父级文件夹ID，支持树形结构
    parent_id = Column(String, ForeignKey("hsai_material_folders.id"), nullable=True)
    
    # 所属用户
    user_id = Column(String, nullable=False)
    
    # 文件夹配置
    settings = Column(JSON, nullable=True)
    
    # 排序权重
    sort_order = Column(BigInteger, default=0)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class HSAIMaterial(Base):
    """HSAI素材文件表"""
    __tablename__ = "hsai_materials"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # 素材类型：video, image, audio, text, document
    material_type = Column(String, nullable=False)
    
    # 所属文件夹
    folder_id = Column(String, ForeignKey("hsai_material_folders.id"), nullable=True)
    
    # 所属用户
    user_id = Column(String, nullable=False)
    
    # 文件相关信息
    file_path = Column(String, nullable=True)  # 实际文件路径
    file_size = Column(BigInteger, nullable=True)  # 文件大小(字节)
    file_hash = Column(String, nullable=True)  # 文件哈希值
    mime_type = Column(String, nullable=True)  # MIME类型
    
    # 素材元数据
    material_metadata = Column(JSON, nullable=True)  # 视频分辨率、时长等
    
    # 标签系统
    tags = Column(JSON, nullable=True)  # 标签数组
    
    # AI分析结果
    ai_analysis = Column(JSON, nullable=True)  # AI分析的结果
    
    # 使用统计
    usage_count = Column(BigInteger, default=0)  # 使用次数
    last_used_at = Column(BigInteger, nullable=True)  # 最后使用时间
    
    # 状态管理
    status = Column(String, default="active")  # active, archived, deleted
    
    # 访问控制
    access_control = Column(JSON, nullable=True)
    
    # 文件属性（用于文件名拼接）
    scene_code = Column(String, nullable=True)      # 场景代码
    technique_code = Column(String, nullable=True)  # 手法代码
    properties_code = Column(String, nullable=True) # 属性代码（多个属性用下划线分隔）
    
    # 视频元数据
    duration = Column(Integer, nullable=True)       # 视频时长（秒）
    resolution = Column(String, nullable=True)      # 视频分辨率
    
    # OSS信息
    oss_bucket = Column(String, nullable=True)
    oss_key = Column(String, nullable=True)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class HSAIMaterialTag(Base):
    """HSAI素材标签表"""
    __tablename__ = "hsai_material_tags"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    color = Column(String, nullable=True)  # 标签颜色
    category = Column(String, nullable=True)  # 标签分类
    
    # 所属用户
    user_id = Column(String, nullable=False)
    
    # 使用统计
    usage_count = Column(BigInteger, default=0)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class HSAIMaterialCategory(Base):
    """HSAI素材分类表"""
    __tablename__ = "hsai_material_categories"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)        # 分类名称（英文）
    display_name = Column(String, nullable=False) # 显示名称（中文）
    category_type = Column(String, nullable=False) # 分类类型：scene, technique, property
    description = Column(Text, nullable=True)    # 描述
    is_active = Column(Boolean, default=True)    # 是否启用
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic Models
####################


class HSAIMaterialFolderModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    user_id: str
    settings: Optional[dict] = None
    sort_order: int = 0
    created_at: int
    updated_at: int


class HSAIMaterialModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    material_type: str
    folder_id: Optional[str] = None
    user_id: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    mime_type: Optional[str] = None
    material_metadata: Optional[dict] = None
    tags: Optional[List[str]] = None
    ai_analysis: Optional[dict] = None
    usage_count: int = 0
    last_used_at: Optional[int] = None
    status: str = "active"
    access_control: Optional[dict] = None
    # 新增字段
    scene_code: Optional[str] = None
    technique_code: Optional[str] = None
    properties_code: Optional[str] = None
    duration: Optional[int] = None
    resolution: Optional[str] = None
    oss_bucket: Optional[str] = None
    oss_key: Optional[str] = None
    created_at: int
    updated_at: int


class HSAIMaterialTagModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    color: Optional[str] = None
    category: Optional[str] = None
    user_id: str
    usage_count: int = 0
    created_at: int
    updated_at: int


class HSAIMaterialCategoryModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    display_name: str
    category_type: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: int
    updated_at: int


####################
# Forms
####################


class HSAIMaterialFolderForm(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    settings: Optional[dict] = None
    sort_order: Optional[int] = 0


class HSAIMaterialForm(BaseModel):
    name: str
    description: Optional[str] = None
    material_type: str
    folder_id: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    mime_type: Optional[str] = None
    material_metadata: Optional[dict] = None
    tags: Optional[List[str]] = None
    access_control: Optional[dict] = None
    # 新增字段
    scene_code: Optional[str] = None
    technique_code: Optional[str] = None
    properties_code: Optional[str] = None
    duration: Optional[int] = None
    resolution: Optional[str] = None
    oss_bucket: Optional[str] = None
    oss_key: Optional[str] = None


class HSAIMaterialTagForm(BaseModel):
    name: str
    color: Optional[str] = None
    category: Optional[str] = None


class HSAIMaterialCategoryForm(BaseModel):
    name: str
    display_name: str
    category_type: str
    description: Optional[str] = None
    is_active: bool = True


####################
# Response Models
####################


class HSAIMaterialFolderResponse(BaseModel):
    id: str = Field(description="文件夹唯一标识符")
    name: str = Field(description="文件夹名称")
    description: Optional[str] = Field(default=None, description="文件夹描述")
    parent_id: Optional[str] = Field(default=None, description="父文件夹ID")
    settings: Optional[dict] = Field(default=None, description="文件夹配置")
    sort_order: int = Field(default=0, description="排序权重")
    children: Optional[List['HSAIMaterialFolderResponse']] = Field(default=None, description="子文件夹列表")
    material_count: Optional[int] = Field(default=None, description="文件夹内素材数量")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class HSAIMaterialResponse(BaseModel):
    id: str = Field(description="素材唯一标识符")
    name: str = Field(description="素材名称")
    description: Optional[str] = Field(default=None, description="素材描述")
    material_type: str = Field(description="素材类型 (video, image, audio, text, document)")
    folder_id: Optional[str] = Field(default=None, description="所属文件夹ID")
    file_path: Optional[str] = Field(default=None, description="文件路径")
    file_size: Optional[int] = Field(default=None, description="文件大小(字节)")
    mime_type: Optional[str] = Field(default=None, description="MIME类型")
    material_metadata: Optional[dict] = Field(default=None, description="素材元数据(分辨率、时长等)")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    ai_analysis: Optional[dict] = Field(default=None, description="AI分析结果")
    usage_count: int = Field(default=0, description="使用次数")
    last_used_at: Optional[int] = Field(default=None, description="最后使用时间戳")
    status: str = Field(default="active", description="状态 (active, archived, deleted)")
    thumbnail_url: Optional[str] = Field(default=None, description="缩略图URL")
    download_url: Optional[str] = Field(default=None, description="下载URL")
    # 新增字段
    scene_code: Optional[str] = Field(default=None, description="场景代码")
    technique_code: Optional[str] = Field(default=None, description="手法代码")
    properties_code: Optional[List[str]] = Field(default=None, description="属性代码列表")
    duration: Optional[int] = Field(default=None, description="视频时长（秒）")
    resolution: Optional[str] = Field(default=None, description="视频分辨率")
    oss_bucket: Optional[str] = Field(default=None, description="OSS Bucket")
    oss_key: Optional[str] = Field(default=None, description="OSS对象键")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


# 添加分类响应模型
class HSAIMaterialCategoryResponse(BaseModel):
    id: str = Field(description="分类唯一标识符")
    name: str = Field(description="分类名称（英文）")
    display_name: str = Field(description="显示名称（中文）")
    category_type: str = Field(description="分类类型：scene, technique, property")
    description: Optional[str] = Field(default=None, description="分类描述")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


####################
# Database Tables
####################


class HSAIMaterialFoldersTable:
    def insert_new_folder(
        self, user_id: str, form_data: HSAIMaterialFolderForm
    ) -> Optional[HSAIMaterialFolderModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            folder = HSAIMaterialFolderModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = HSAIMaterialFolder(**folder.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return HSAIMaterialFolderModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating folder: {e}")
                return None

    def get_folders_by_user_id(self, user_id: str) -> List[HSAIMaterialFolderModel]:
        with get_db() as db:
            try:
                folders = db.query(HSAIMaterialFolder).filter_by(user_id=user_id).all()
                return [HSAIMaterialFolderModel.model_validate(folder) for folder in folders]
            except Exception as e:
                log.exception(f"Error getting folders: {e}")
                return []

    def get_folder_by_id(self, folder_id: str) -> Optional[HSAIMaterialFolderModel]:
        with get_db() as db:
            try:
                folder = db.get(HSAIMaterialFolder, folder_id)
                return HSAIMaterialFolderModel.model_validate(folder) if folder else None
            except Exception:
                return None

    def update_folder_by_id(
        self, folder_id: str, form_data: HSAIMaterialFolderForm
    ) -> Optional[HSAIMaterialFolderModel]:
        with get_db() as db:
            try:
                folder = db.get(HSAIMaterialFolder, folder_id)
                if folder:
                    for key, value in form_data.model_dump(exclude_unset=True).items():
                        setattr(folder, key, value)
                    folder.updated_at = int(time.time())
                    db.commit()
                    db.refresh(folder)
                    return HSAIMaterialFolderModel.model_validate(folder)
                return None
            except Exception as e:
                log.exception(f"Error updating folder: {e}")
                return None

    def delete_folder_by_id(self, folder_id: str) -> bool:
        with get_db() as db:
            try:
                folder = db.get(HSAIMaterialFolder, folder_id)
                if folder:
                    db.delete(folder)
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error deleting folder: {e}")
                return False


class HSAIMaterialsTable:
    def insert_new_material(
        self, user_id: str, form_data: HSAIMaterialForm
    ) -> Optional[HSAIMaterialModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            material = HSAIMaterialModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = HSAIMaterial(**material.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return HSAIMaterialModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating material: {e}")
                return None

    def get_materials_by_user_id(
        self, user_id: str, folder_id: Optional[str] = None, material_type: Optional[str] = None
    ) -> List[HSAIMaterialModel]:
        with get_db() as db:
            try:
                query = db.query(HSAIMaterial).filter_by(user_id=user_id, status="active")
                
                if folder_id:
                    query = query.filter_by(folder_id=folder_id)
                if material_type:
                    query = query.filter_by(material_type=material_type)
                    
                materials = query.order_by(HSAIMaterial.updated_at.desc()).all()
                return [HSAIMaterialModel.model_validate(material) for material in materials]
            except Exception as e:
                log.exception(f"Error getting materials: {e}")
                return []

    def get_material_by_id(self, material_id: str) -> Optional[HSAIMaterialModel]:
        with get_db() as db:
            try:
                material = db.get(HSAIMaterial, material_id)
                return HSAIMaterialModel.model_validate(material) if material else None
            except Exception:
                return None

    def update_material_by_id(
        self, material_id: str, form_data: HSAIMaterialForm
    ) -> Optional[HSAIMaterialModel]:
        with get_db() as db:
            try:
                material = db.get(HSAIMaterial, material_id)
                if material:
                    for key, value in form_data.model_dump(exclude_unset=True).items():
                        setattr(material, key, value)
                    material.updated_at = int(time.time())
                    db.commit()
                    db.refresh(material)
                    return HSAIMaterialModel.model_validate(material)
                return None
            except Exception as e:
                log.exception(f"Error updating material: {e}")
                return None

    def increment_usage_count(self, material_id: str) -> bool:
        """增加素材使用次数"""
        with get_db() as db:
            try:
                material = db.get(HSAIMaterial, material_id)
                if material:
                    material.usage_count += 1
                    material.last_used_at = int(time.time())
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error incrementing usage count: {e}")
                return False

    def search_materials(
        self, user_id: str, query: str, material_type: Optional[str] = None
    ) -> List[HSAIMaterialModel]:
        """搜索素材"""
        with get_db() as db:
            try:
                search_query = db.query(HSAIMaterial).filter_by(user_id=user_id, status="active")
                
                if material_type:
                    search_query = search_query.filter_by(material_type=material_type)
                
                # 搜索名称和描述
                search_query = search_query.filter(
                    HSAIMaterial.name.ilike(f"%{query}%") |
                    HSAIMaterial.description.ilike(f"%{query}%")
                )
                
                materials = search_query.order_by(HSAIMaterial.updated_at.desc()).all()
                return [HSAIMaterialModel.model_validate(material) for material in materials]
            except Exception as e:
                log.exception(f"Error searching materials: {e}")
                return []

    def delete_material_by_id(self, material_id: str) -> bool:
        """软删除素材"""
        with get_db() as db:
            try:
                material = db.get(HSAIMaterial, material_id)
                if material:
                    material.status = "deleted"
                    material.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error deleting material: {e}")
                return False


class HSAIMaterialCategoriesTable:
    def insert_new_category(
        self, form_data: HSAIMaterialCategoryForm
    ) -> Optional[HSAIMaterialCategoryModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            category = HSAIMaterialCategoryModel(
                **{
                    "id": id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = HSAIMaterialCategory(**category.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return HSAIMaterialCategoryModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating category: {e}")
                return None

    def get_categories_by_type(self, category_type: str) -> List[HSAIMaterialCategoryModel]:
        with get_db() as db:
            try:
                categories = db.query(HSAIMaterialCategory).filter_by(category_type=category_type, is_active=True).all()
                return [HSAIMaterialCategoryModel.model_validate(category) for category in categories]
            except Exception as e:
                log.exception(f"Error getting categories: {e}")
                return []

    def get_all_categories(self) -> List[HSAIMaterialCategoryModel]:
        with get_db() as db:
            try:
                categories = db.query(HSAIMaterialCategory).filter_by(is_active=True).all()
                return [HSAIMaterialCategoryModel.model_validate(category) for category in categories]
            except Exception as e:
                log.exception(f"Error getting all categories: {e}")
                return []

    def get_category_by_id(self, category_id: str) -> Optional[HSAIMaterialCategoryModel]:
        with get_db() as db:
            try:
                category = db.get(HSAIMaterialCategory, category_id)
                return HSAIMaterialCategoryModel.model_validate(category) if category else None
            except Exception:
                return None

    def update_category_by_id(
        self, category_id: str, form_data: HSAIMaterialCategoryForm
    ) -> Optional[HSAIMaterialCategoryModel]:
        with get_db() as db:
            try:
                category = db.get(HSAIMaterialCategory, category_id)
                if category:
                    for key, value in form_data.model_dump(exclude_unset=True).items():
                        setattr(category, key, value)
                    category.updated_at = int(time.time())
                    db.commit()
                    db.refresh(category)
                    return HSAIMaterialCategoryModel.model_validate(category)
                return None
            except Exception as e:
                log.exception(f"Error updating category: {e}")
                return None

    def delete_category_by_id(self, category_id: str) -> bool:
        with get_db() as db:
            try:
                category = db.get(HSAIMaterialCategory, category_id)
                if category:
                    category.is_active = False
                    category.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error deleting category: {e}")
                return False


# 全局实例
HSAIMaterialFolders = HSAIMaterialFoldersTable()
HSAIMaterials = HSAIMaterialsTable()
HSAIMaterialCategories = HSAIMaterialCategoriesTable()