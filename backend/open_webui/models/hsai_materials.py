import logging
import logging
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import BigInteger, Column, String, Text, JSON, ForeignKey, Boolean, Integer
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
    
    # 回收站功能相关字段
    is_deleted = Column(Boolean, default=False)     # 删除标志位（true表示已删除）
    original_directory = Column(String, nullable=True)  # 原始目录（软删除时保存文件原始所在目录）
    deleted_at = Column(BigInteger, nullable=True)      # 删除时间（软删除时间）
    deleted_by = Column(String, nullable=True)          # 删除人ID（软删除操作人）
    
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


class HSAIFileOperationLog(Base):
    """HSAI文件操作日志表"""
    __tablename__ = "hsai_file_operation_logs"
    
    id = Column(String, primary_key=True)
    material_id = Column(String, ForeignKey("hsai_materials.id"), nullable=False)  # 素材ID
    operation_type = Column(String, nullable=False)  # 操作类型（upload/delete/restore/move/modify）
    source_path = Column(String, nullable=False)     # 源文件路径
    target_path = Column(String, nullable=True)      # 目标文件路径
    operator_id = Column(String, nullable=False)     # 操作人ID
    operation_time = Column(BigInteger, nullable=False)  # 操作时间
    details = Column(JSON, nullable=True)            # 操作详情
    enterprise_id = Column(String, nullable=True)    # 企业ID（用于企业级过滤）
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic Models
####################


class HSAIMaterialFolderModel(BaseModel):
    """HSAI素材文件夹模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="文件夹唯一标识符")
    name: str = Field(description="文件夹名称")
    description: Optional[str] = Field(default=None, description="文件夹描述")
    parent_id: Optional[str] = Field(default=None, description="父级文件夹ID")
    user_id: str = Field(description="用户ID")
    settings: Optional[dict] = Field(default=None, description="文件夹配置")
    sort_order: int = Field(default=0, description="排序权重")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")
    
    @field_validator('parent_id', mode='before')
    @classmethod
    def validate_parent_id(cls, v):
        """parent_id字段验证：空字符串转为None"""
        if v == '':
            return None
        return v


class HSAIMaterialModel(BaseModel):
    """HSAI素材文件模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="素材唯一标识符")
    name: str = Field(description="素材名称")
    description: Optional[str] = Field(default=None, description="素材描述")
    material_type: str = Field(description="素材类型：video, image, audio, text, document")
    folder_id: Optional[str] = Field(default=None, description="所属文件夹")
    user_id: str = Field(description="用户ID")
    file_path: Optional[str] = Field(default=None, description="文件路径")
    file_size: Optional[int] = Field(default=None, description="文件大小(字节)")
    file_hash: Optional[str] = Field(default=None, description="文件哈希值")
    mime_type: Optional[str] = Field(default=None, description="MIME类型")
    material_metadata: Optional[dict] = Field(default=None, description="素材元数据")
    tags: Optional[List[str]] = Field(default=None, description="标签数组")
    ai_analysis: Optional[dict] = Field(default=None, description="AI分析结果")
    usage_count: int = Field(default=0, description="使用次数")
    last_used_at: Optional[int] = Field(default=None, description="最后使用时间")
    status: str = Field(default="active", description="状态管理")
    access_control: Optional[dict] = Field(default=None, description="访问控制")
    scene_code: Optional[str] = Field(default=None, description="场景代码")
    technique_code: Optional[str] = Field(default=None, description="手法代码")
    properties_code: Optional[str] = Field(default=None, description="属性代码")
    duration: Optional[int] = Field(default=None, description="视频时长（秒）")
    resolution: Optional[str] = Field(default=None, description="视频分辨率")
    oss_bucket: Optional[str] = Field(default=None, description="OSS Bucket")
    oss_key: Optional[str] = Field(default=None, description="OSS对象键")
    is_deleted: bool = Field(default=False, description="删除标志位")
    original_directory: Optional[str] = Field(default=None, description="原始目录")
    deleted_at: Optional[int] = Field(default=None, description="删除时间")
    deleted_by: Optional[str] = Field(default=None, description="删除人ID")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class HSAIMaterialTagModel(BaseModel):
    """HSAI素材标签模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="标签唯一标识符")
    name: str = Field(description="标签名称")
    color: Optional[str] = Field(default=None, description="标签颜色")
    category: Optional[str] = Field(default=None, description="标签分类")
    user_id: str = Field(description="用户ID")
    usage_count: int = Field(default=0, description="使用统计")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class HSAIMaterialCategoryModel(BaseModel):
    """HSAI素材分类模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(description="分类唯一标识符")
    name: str = Field(description="分类名称（英文）")
    display_name: str = Field(description="显示名称（中文）")
    category_type: str = Field(description="分类类型：scene, technique, property")
    description: Optional[str] = Field(default=None, description="描述")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class HSAIFileOperationLogModel(BaseModel):
    """HSAI文件操作日志模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(description="日志唯一标识符")
    material_id: str = Field(description="素材ID")
    operation_type: str = Field(description="操作类型（upload/delete/restore/move/modify）")
    source_path: str = Field(description="源文件路径")
    target_path: Optional[str] = Field(default=None, description="目标文件路径")
    operator_id: str = Field(description="操作人ID")
    operation_time: int = Field(description="操作时间")
    details: Optional[dict] = Field(default=None, description="操作详情")
    enterprise_id: Optional[str] = Field(default=None, description="企业ID")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


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
    # 回收站相关字段
    is_deleted: bool = False
    original_directory: Optional[str] = None
    deleted_at: Optional[int] = None
    deleted_by: Optional[str] = None


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


class HSAIFileOperationLogForm(BaseModel):
    """文件操作日志表单模型"""
    material_id: str
    operation_type: str
    source_path: str
    target_path: Optional[str] = None
    operation_time: int
    details: Optional[dict] = None
    enterprise_id: Optional[str] = None
    # 移除了 operator_id 字段，直接使用当前登录用户信息


####################
# Response Models
####################


class HSAIMaterialFolderResponse(BaseModel):
    id: str = Field(description="文件夹唯一标识符")
    name: str = Field(description="文件夹名称")
    label: str = Field(description="文件夹标签，与name字段相同，仅供前端使用")
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
    # 回收站相关字段
    is_deleted: bool = Field(default=False, description="删除标志位（true表示已删除）")
    original_directory: Optional[str] = Field(default=None, description="原始目录（软删除时保存文件原始所在目录）")
    deleted_at: Optional[int] = Field(default=None, description="删除时间（软删除时间）")
    deleted_by: Optional[str] = Field(default=None, description="删除人ID（软删除操作人）")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


# 添加分页响应模型
class PaginationData(BaseModel):
    """分页数据模型"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")


class HSAIMaterialCategoryResponse(BaseModel):
    id: str = Field(description="分类唯一标识符")
    name: str = Field(description="分类名称（英文）")
    display_name: str = Field(description="显示名称（中文）")
    category_type: str = Field(description="分类类型：scene, technique, property")
    description: Optional[str] = Field(default=None, description="分类描述")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class HSAIFileOperationLogResponse(BaseModel):
    """文件操作日志响应模型"""
    id: str = Field(description="日志唯一标识符")
    material_id: str = Field(description="素材唯一标识符")
    operation_type: str = Field(description="操作类型（upload/delete/restore/move/modify）")
    source_path: str = Field(description="源文件路径")
    target_path: Optional[str] = Field(default=None, description="目标文件路径")
    operator_id: str = Field(description="操作人ID")
    operation_time: int = Field(description="操作时间")
    details: Optional[dict] = Field(default=None, description="操作详情")
    enterprise_id: Optional[str] = Field(default=None, description="企业ID")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class PaginatedHSAIMaterialResponse(BaseModel):
    """分页的素材响应模型"""
    data: List[HSAIMaterialResponse] = Field(description="素材数据列表")
    pagination: PaginationData = Field(description="分页信息")


class PaginatedHSAIMaterialCategoryResponse(BaseModel):
    """分页的素材分类响应模型"""
    data: List[HSAIMaterialCategoryResponse] = Field(description="素材分类数据列表")
    pagination: PaginationData = Field(description="分页信息")


class PaginatedHSAIFileOperationLogResponse(BaseModel):
    """分页的文件操作日志响应模型"""
    data: List[HSAIFileOperationLogResponse] = Field(description="文件操作日志数据列表")
    pagination: PaginationData = Field(description="分页信息")


####################
# Database Tables
####################


class HSAIMaterialFoldersTable:
    def insert_new_folder(
        self, user_id: str, form_data: HSAIMaterialFolderForm
    ) -> Optional[HSAIMaterialFolderModel]:
        with get_db() as db:
            # 验证 parent_id 是否有效（如果提供了的话）
            if form_data.parent_id:
                parent_folder = db.query(HSAIMaterialFolder).filter_by(
                    id=form_data.parent_id, user_id=user_id
                ).first()
                if not parent_folder:
                    log.error(f"Invalid parent_id: {form_data.parent_id} for user {user_id}")
                    return None
            
            # 检查同一父目录下是否已有同名文件夹
            existing_folder = db.query(HSAIMaterialFolder).filter_by(
                name=form_data.name,
                parent_id=form_data.parent_id,
                user_id=user_id
            ).first()
            if existing_folder:
                log.error(f"Folder with name '{form_data.name}' already exists in the same parent directory")
                return None
            
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
                db.rollback()
                log.exception(f"Error creating folder: {e}")
                return None

    def get_folders_by_user_id(self, user_id: str) -> List[HSAIMaterialFolderModel]:
        with get_db() as db:
            try:
                folders = db.query(HSAIMaterialFolder).filter_by(user_id=user_id).all()
                
                # 调试信息：检查数据库原始数据
                log.info(f"Raw DB query returned {len(folders)} folders for user {user_id}")
                
                raw_root_count = sum(1 for f in folders if f.parent_id is None)
                raw_child_count = sum(1 for f in folders if f.parent_id is not None)
                log.info(f"Raw DB data: {raw_root_count} roots, {raw_child_count} children")
                
                # 显示一些有parent_id的示例
                children_examples = [f for f in folders if f.parent_id is not None][:3]
                for example in children_examples:
                    log.info(f"DB child example: {example.name} (ID: {example.id}) -> parent: {example.parent_id}")
                
                # 跳过Pydantic验证，直接构建字典并手动验证
                result = []
                for folder in folders:
                    try:
                        # 手动处理parent_id
                        parent_id = folder.parent_id
                        if parent_id == '':
                            parent_id = None
                        
                        folder_dict = {
                            "id": folder.id,
                            "name": folder.name,
                            "description": folder.description,
                            "parent_id": parent_id,  # 手动处理的parent_id
                            "user_id": folder.user_id,
                            "settings": folder.settings,
                            "sort_order": folder.sort_order or 0,
                            "created_at": folder.created_at,
                            "updated_at": folder.updated_at
                        }
                        
                        # 使用字典直接创建Pydantic模型
                        validated_folder = HSAIMaterialFolderModel(**folder_dict)
                        result.append(validated_folder)
                        
                        # 调试：检查parent_id是否正确
                        if folder.parent_id != validated_folder.parent_id:
                            log.info(f"PARENT_ID CLEANED: DB='{folder.parent_id}' -> Pydantic='{validated_folder.parent_id}' for folder {folder.name}")
                    except Exception as e:
                        log.error(f"Failed to validate folder {folder.name}: {e}")
                        continue
                
                # 调试信息：检查转换后的数据
                validated_root_count = sum(1 for f in result if f.parent_id is None)
                validated_child_count = sum(1 for f in result if f.parent_id is not None)
                log.info(f"After manual validation: {validated_root_count} roots, {validated_child_count} children")
                
                if validated_child_count != raw_child_count:
                    log.error(f"MANUAL CONVERSION ISSUE: Expected {raw_child_count} children, got {validated_child_count}")
                else:
                    log.info(f"SUCCESS: Manual conversion preserved all {validated_child_count} children")
                
                return result
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

    def update_folder_name_by_id(
        self, folder_id: str, name: str
    ) -> Optional[HSAIMaterialFolderModel]:
        """
        更新素材文件夹名称
        
        Args:
            folder_id (str): 文件夹ID
            name (str): 新的文件夹名称
            
        Returns:
            Optional[HSAIMaterialFolderModel]: 更新后的文件夹模型
        """
        with get_db() as db:
            try:
                # 获取文件夹信息（后续在路由层验证所有权）
                folder = db.query(HSAIMaterialFolder).filter_by(id=folder_id).first()
                
                if not folder:
                    return None
                
                # 检查同一父目录下是否已有同名文件夹
                existing_folder = db.query(HSAIMaterialFolder).filter_by(
                    name=name,
                    parent_id=folder.parent_id,
                    user_id=folder.user_id
                ).first()
                
                if existing_folder and existing_folder.id != folder_id:
                    # 同名文件夹已存在
                    return None
                
                # 更新文件夹名称
                folder.name = name
                folder.updated_at = int(time.time())
                db.commit()
                db.refresh(folder)
                return HSAIMaterialFolderModel.model_validate(folder)
            except Exception as e:
                log.exception(f"Error updating folder name: {e}")
                db.rollback()
                return None


class HSAIMaterialsTable:
    def insert_new_material(
        self, user_id: str, form_data: HSAIMaterialForm
    ) -> Optional[HSAIMaterialModel]:
        with get_db() as db:
            try:
                id = str(uuid.uuid4())
                material_data = {
                    "id": id,
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
                
                # 确保所有必填字段都有值
                if material_data.get("material_type") is None:
                    log.error("Missing required field: material_type")
                    log.error(f"Form data: {form_data}")
                    return None
                    
                if material_data.get("name") is None:
                    log.error("Missing required field: name")
                    log.error(f"Form data: {form_data}")
                    return None
                
                log.info(f"Creating material record for user {user_id}")
                log.info(f"Material data: {material_data}")
                
                # 验证数据
                try:
                    validated_data = HSAIMaterial(**material_data)
                    log.info("Data validation passed")
                except Exception as e:
                    log.error(f"Data validation failed: {e}")
                    log.error(f"Material data that failed validation: {material_data}")
                    return None
                
                result = HSAIMaterial(**material_data)
                db.add(result)
                db.commit()
                db.refresh(result)
                log.info(f"Material record created successfully with ID: {result.id}")
                return HSAIMaterialModel.model_validate(result) if result else None
            except Exception as e:
                db.rollback()
                log.exception(f"Error creating material: {e}")
                log.error(f"Material data that caused error: {material_data}")
                log.error(f"Form data: {form_data}")
                return None

    def get_materials_by_user_id(
        self, user_id: str, folder_id: Optional[str] = None, material_type: Optional[str] = None,
        limit: int = 20, offset: int = 0
    ) -> List[HSAIMaterialModel]:
        with get_db() as db:
            try:
                query = db.query(HSAIMaterial).filter_by(user_id=user_id, status="active")
                
                if folder_id:
                    query = query.filter_by(folder_id=folder_id)
                if material_type:
                    query = query.filter_by(material_type=material_type)
                    
                materials = query.order_by(HSAIMaterial.updated_at.desc()).limit(limit).offset(offset).all()
                return [HSAIMaterialModel.model_validate(material) for material in materials]
            except Exception as e:
                log.exception(f"Error getting materials: {e}")
                return []

    def get_materials_count(
        self, user_id: str, folder_id: Optional[str] = None, material_type: Optional[str] = None
    ) -> int:
        """获取素材总数"""
        with get_db() as db:
            try:
                query = db.query(HSAIMaterial).filter_by(user_id=user_id, status="active")
                
                if folder_id:
                    query = query.filter_by(folder_id=folder_id)
                if material_type:
                    query = query.filter_by(material_type=material_type)
                    
                return query.count()
            except Exception as e:
                log.exception(f"Error counting materials: {e}")
                return 0

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
        self, user_id: str, query: str, material_type: Optional[str] = None, limit: int = 20, offset: int = 0
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
                
                materials = search_query.order_by(HSAIMaterial.updated_at.desc()).limit(limit).offset(offset).all()
                return [HSAIMaterialModel.model_validate(material) for material in materials]
            except Exception as e:
                log.exception(f"Error searching materials: {e}")
                return []

    def count_search_materials(
        self, user_id: str, query: str, material_type: Optional[str] = None
    ) -> int:
        """获取搜索结果总数"""
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
                
                return search_query.count()
            except Exception as e:
                log.exception(f"Error counting search materials: {e}")
                return 0

    def get_deleted_materials_by_user_id(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> List[HSAIMaterialModel]:
        """获取用户已删除的素材列表"""
        with get_db() as db:
            try:
                materials = db.query(HSAIMaterial).filter_by(user_id=user_id, is_deleted=True).order_by(HSAIMaterial.deleted_at.desc()).limit(limit).offset(offset).all()
                return [HSAIMaterialModel.model_validate(material) for material in materials]
            except Exception as e:
                log.exception(f"Error getting deleted materials: {e}")
                return []

    def count_deleted_materials_by_user_id(self, user_id: str) -> int:
        """获取用户已删除的素材总数"""
        with get_db() as db:
            try:
                return db.query(HSAIMaterial).filter_by(user_id=user_id, is_deleted=True).count()
            except Exception as e:
                log.exception(f"Error counting deleted materials: {e}")
                return 0

    def get_deleted_materials_by_enterprise(
        self, enterprise_id: str, limit: int = 20, offset: int = 0
    ) -> List[HSAIMaterialModel]:
        """获取企业已删除的素材列表"""
        with get_db() as db:
            try:
                # 注意：这里假设enterprise_id存储在user_id字段中
                # 在实际实现中，可能需要根据具体的数据结构进行调整
                materials = db.query(HSAIMaterial).filter_by(user_id=enterprise_id, is_deleted=True).order_by(HSAIMaterial.deleted_at.desc()).limit(limit).offset(offset).all()
                return [HSAIMaterialModel.model_validate(material) for material in materials]
            except Exception as e:
                log.exception(f"Error getting deleted materials by enterprise: {e}")
                return []

    def count_deleted_materials_by_enterprise(self, enterprise_id: str) -> int:
        """获取企业已删除的素材总数"""
        with get_db() as db:
            try:
                # 注意：这里假设enterprise_id存储在user_id字段中
                # 在实际实现中，可能需要根据具体的数据结构进行调整
                return db.query(HSAIMaterial).filter_by(user_id=enterprise_id, is_deleted=True).count()
            except Exception as e:
                log.exception(f"Error counting deleted materials by enterprise: {e}")
                return 0

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

    def get_categories_by_type(self, category_type: str, limit: int = 20, offset: int = 0) -> List[HSAIMaterialCategoryModel]:
        with get_db() as db:
            try:
                categories = db.query(HSAIMaterialCategory).filter_by(category_type=category_type, is_active=True).limit(limit).offset(offset).all()
                return [HSAIMaterialCategoryModel.model_validate(category) for category in categories]
            except Exception as e:
                log.exception(f"Error getting categories: {e}")
                return []

    def get_all_categories(self, limit: int = 20, offset: int = 0) -> List[HSAIMaterialCategoryModel]:
        with get_db() as db:
            try:
                categories = db.query(HSAIMaterialCategory).filter_by(is_active=True).limit(limit).offset(offset).all()
                return [HSAIMaterialCategoryModel.model_validate(category) for category in categories]
            except Exception as e:
                log.exception(f"Error getting all categories: {e}")
                return []

    def get_categories_count(self, category_type: Optional[str] = None) -> int:
        """获取分类总数"""
        with get_db() as db:
            try:
                query = db.query(HSAIMaterialCategory).filter_by(is_active=True)
                
                if category_type:
                    query = query.filter_by(category_type=category_type)
                    
                return query.count()
            except Exception as e:
                log.exception(f"Error counting categories: {e}")
                return 0

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


class HSAIFileOperationLogsTable:
    def insert_new_log(
        self, form_data: HSAIFileOperationLogForm
    ) -> Optional[HSAIFileOperationLogModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            log_entry = HSAIFileOperationLogModel(
                **{
                    "id": id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            try:
                result = HSAIFileOperationLog(**log_entry.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return HSAIFileOperationLogModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error creating file operation log: {e}")
                return None

    def get_logs(
        self, 
        material_id: Optional[str] = None,
        enterprise_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        operator_id: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 20, 
        offset: int = 0
    ) -> List[HSAIFileOperationLogModel]:
        """获取文件操作日志列表"""
        with get_db() as db:
            try:
                query = db.query(HSAIFileOperationLog)
                
                if material_id:
                    query = query.filter_by(material_id=material_id)
                if enterprise_id:
                    query = query.filter_by(enterprise_id=enterprise_id)
                if operation_type:
                    query = query.filter_by(operation_type=operation_type)
                if operator_id:
                    query = query.filter_by(operator_id=operator_id)
                if start_time:
                    query = query.filter(HSAIFileOperationLog.operation_time >= start_time)
                if end_time:
                    query = query.filter(HSAIFileOperationLog.operation_time <= end_time)
                
                logs = query.order_by(HSAIFileOperationLog.operation_time.desc()).limit(limit).offset(offset).all()
                return [HSAIFileOperationLogModel.model_validate(log) for log in logs]
            except Exception as e:
                log.exception(f"Error getting file operation logs: {e}")
                return []

    def get_logs_count(
        self,
        material_id: Optional[str] = None,
        enterprise_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        operator_id: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> int:
        """获取文件操作日志总数"""
        with get_db() as db:
            try:
                query = db.query(HSAIFileOperationLog)
                
                if material_id:
                    query = query.filter_by(material_id=material_id)
                if enterprise_id:
                    query = query.filter_by(enterprise_id=enterprise_id)
                if operation_type:
                    query = query.filter_by(operation_type=operation_type)
                if operator_id:
                    query = query.filter_by(operator_id=operator_id)
                if start_time:
                    query = query.filter(HSAIFileOperationLog.operation_time >= start_time)
                if end_time:
                    query = query.filter(HSAIFileOperationLog.operation_time <= end_time)
                
                return query.count()
            except Exception as e:
                log.exception(f"Error counting file operation logs: {e}")
                return 0

    def get_log_by_id(self, log_id: str) -> Optional[HSAIFileOperationLogModel]:
        """根据ID获取文件操作日志"""
        with get_db() as db:
            try:
                log_entry = db.get(HSAIFileOperationLog, log_id)
                return HSAIFileOperationLogModel.model_validate(log_entry) if log_entry else None
            except Exception:
                return None

# 全局实例
HSAIMaterialFolders = HSAIMaterialFoldersTable()
HSAIMaterials = HSAIMaterialsTable()
HSAIMaterialCategories = HSAIMaterialCategoriesTable()
HSAIFileOperationLogs = HSAIFileOperationLogsTable()
