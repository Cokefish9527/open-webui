import logging
import time
import uuid
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from open_webui.models.hsai_materials import (
    HSAIMaterialFolder,
    HSAIMaterial,
    HSAIMaterialTag,
    HSAIMaterialFolders,
    HSAIMaterials,
    HSAIMaterialFolderForm,
    HSAIMaterialForm,
    HSAIMaterialTagForm,
    HSAIMaterialFolderResponse,
    HSAIMaterialResponse
)

from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.config import UPLOAD_DIR

import aiofiles
import os
import hashlib
import mimetypes
import json
from open_webui.storage.provider import Storage
import json
from open_webui.storage.provider import Storage
from open_webui.storage.provider import Storage

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/materials", tags=["hsai_materials"])

# HSAI素材存储配置
HSAI_MATERIALS_PREFIX = "hsai/materials"  # OSS存储前缀

############################
# 文件夹管理
############################

@router.get("/folders", response_model=List[HSAIMaterialFolderResponse], summary="获取素材文件夹")
async def get_material_folders(user=Depends(get_verified_user)):
    """
    获取用户的素材文件夹树形结构，包含子文件夹和素材数量统计。
    """
    try:
        folders = HSAIMaterialFolders.get_folders_by_user_id(user.id)
        
        # 构建树形结构
        folder_dict = {folder.id: folder for folder in folders}
        root_folders = []
        
        for folder in folders:
            folder_response = HSAIMaterialFolderResponse(
                **folder.model_dump(),
                children=[],
                material_count=0  # 后续可以优化为实际统计
            )
            
            if folder.parent_id is None:
                root_folders.append(folder_response)
            else:
                parent = folder_dict.get(folder.parent_id)
                if parent and hasattr(parent, 'children'):
                    parent.children.append(folder_response)
        
        return root_folders
        
    except Exception as e:
        log.exception(f"Error getting material folders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/folders", response_model=HSAIMaterialFolderResponse, summary="创建素材文件夹")
async def create_material_folder(
    form_data: HSAIMaterialFolderForm,
    user=Depends(get_verified_user)
):
    """
    创建新的素材文件夹。
    """
    try:
        folder = HSAIMaterialFolders.insert_new_folder(user.id, form_data)
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create folder"
            )
        
        return HSAIMaterialFolderResponse(
            **folder.model_dump(),
            children=[],
            material_count=0
        )
        
    except Exception as e:
        log.exception(f"Error creating material folder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/folders/{folder_id}", response_model=HSAIMaterialFolderResponse, summary="更新素材文件夹")
async def update_material_folder(
    folder_id: str,
    form_data: HSAIMaterialFolderForm,
    user=Depends(get_verified_user)
):
    """
    更新素材文件夹信息。
    """
    try:
        # 验证文件夹所有权
        existing_folder = HSAIMaterialFolders.get_folder_by_id(folder_id)
        if not existing_folder or existing_folder.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )
        
        folder = HSAIMaterialFolders.update_folder_by_id(folder_id, form_data)
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update folder"
            )
        
        return HSAIMaterialFolderResponse(
            **folder.model_dump(),
            children=[],
            material_count=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating material folder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.delete("/folders/{folder_id}", response_model=bool, summary="删除素材文件夹")
async def delete_material_folder(
    folder_id: str,
    user=Depends(get_verified_user)
):
    """
    删除素材文件夹。
    
    注意：只能删除空文件夹，如果文件夹中包含素材，需要先移动或删除所有素材。
    
    Args:
        folder_id (str): 要删除的文件夹ID
        user: 已认证的用户对象
        
    Returns:
        bool: 删除是否成功
        
    Raises:
        HTTPException: 404 - 文件夹不存在或无权限访问
        HTTPException: 400 - 文件夹非空，无法删除
        HTTPException: 500 - 服务器内部错误
    """
    try:
        # 验证文件夹所有权
        existing_folder = HSAIMaterialFolders.get_folder_by_id(folder_id)
        if not existing_folder or existing_folder.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )
        
        # 检查文件夹是否为空
        materials = HSAIMaterials.get_materials_by_user_id(user.id, folder_id=folder_id)
        if materials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete folder with materials. Please move or delete materials first."
            )
        
        result = HSAIMaterialFolders.delete_folder_by_id(folder_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error deleting material folder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# 素材管理
############################

@router.get("/", response_model=List[HSAIMaterialResponse], summary="获取素材列表")
async def get_materials(
    folder_id: Optional[str] = Query(None, description="文件夹ID，为空则获取所有素材"),
    material_type: Optional[str] = Query(None, description="素材类型过滤：image(图片)、video(视频)、audio(音频)、text(文本)、document(文档)"),
    user=Depends(get_verified_user)
):
    """
    获取用户的素材列表。
    
    支持按文件夹和素材类型进行过滤。
    
    Args:
        folder_id (Optional[str]): 文件夹ID，为空则获取所有素材
        material_type (Optional[str]): 素材类型过滤
        - "image": 图片素材
        - "video": 视频素材
        - "audio": 音频素材
        - "text": 文本素材
        - "document": 文档素材
        user: 已认证的用户对象
        
    Returns:
        List[HSAIMaterialResponse]: 素材列表
        - id: 素材唯一标识
        - name: 素材名称
        - description: 素材描述
        - material_type: 素材类型
        - file_size: 文件大小（字节）
        - mime_type: MIME类型
        - thumbnail_url: 缩略图URL（图片/视频素材）
        - download_url: 下载URL
        - tags: 标签列表
        - usage_count: 使用次数
        - created_at: 创建时间
        - updated_at: 更新时间
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        materials = HSAIMaterials.get_materials_by_user_id(
            user.id, 
            folder_id=folder_id, 
            material_type=material_type
        )
        
        responses = []
        for material in materials:
            response = HSAIMaterialResponse(
                **material.model_dump(),
                thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
                download_url=f"/hsai/materials/{material.id}/download"
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        log.exception(f"Error getting materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/search", response_model=List[HSAIMaterialResponse], summary="搜索素材")
async def search_materials(
    query: str = Query(..., description="搜索关键词，用于匹配素材名称、描述和标签"),
    material_type: Optional[str] = Query(None, description="素材类型过滤：image(图片)、video(视频)、audio(音频)、text(文本)、document(文档)"),
    user=Depends(get_verified_user)
):
    """
    搜索素材。
    
    根据关键词搜索素材名称、描述和标签，支持按类型过滤。
    
    Args:
        query (str): 搜索关键词
        material_type (Optional[str]): 素材类型过滤（可选）
        - "image": 图片素材
        - "video": 视频素材
        - "audio": 音频素材
        - "text": 文本素材
        - "document": 文档素材
        user: 已认证的用户对象
        
    Returns:
        List[HSAIMaterialResponse]: 匹配的素材列表
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        materials = HSAIMaterials.search_materials(
            user.id, 
            query=query, 
            material_type=material_type
        )
        
        responses = []
        for material in materials:
            response = HSAIMaterialResponse(
                **material.model_dump(),
                thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
                download_url=f"/hsai/materials/{material.id}/download"
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        log.exception(f"Error searching materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


async def calculate_file_hash(file_path: Path) -> str:
    """计算文件哈希值"""
    hash_md5 = hashlib.md5()
    async with aiofiles.open(file_path, 'rb') as f:
        async for chunk in f:
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


@router.post("/upload", response_model=HSAIMaterialResponse, summary="上传素材")
async def upload_material(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    folder_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    user=Depends(get_verified_user)
):
    """
    上传素材文件。
    
    支持上传各种类型的文件，系统会自动识别文件类型并生成相应的素材记录。
    
    Args:
        file (UploadFile): 要上传的文件（必填）
        name (Optional[str]): 素材名称（可选，默认使用文件名）
        description (Optional[str]): 素材描述（可选）
        folder_id (Optional[str]): 目标文件夹ID（可选，为空则放在根目录）
        tags (Optional[str]): 标签，多个标签用逗号分隔（可选）
        user: 已认证的用户对象
        
    Returns:
        HSAIMaterialResponse: 创建的素材信息
        - id: 素材唯一标识
        - name: 素材名称
        - material_type: 自动识别的素材类型
        - file_size: 文件大小
        - file_hash: 文件MD5哈希值
        - thumbnail_url: 缩略图URL（如适用）
        - download_url: 下载URL
        
    Raises:
        HTTPException: 400 - 文件无效或创建失败
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 支持的文件类型：图片、视频、音频、文本、文档等
        - 文件会保存在用户专属目录中
        - 系统会自动计算文件哈希值用于去重
    """
    try:
        # 验证文件
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # 确定文件类型
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        material_type = "document"  # 默认类型
        
        if mime_type:
            if mime_type.startswith("image/"):
                material_type = "image"
            elif mime_type.startswith("video/"):
                material_type = "video"
            elif mime_type.startswith("audio/"):
                material_type = "audio"
            elif mime_type.startswith("text/"):
                material_type = "text"
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        file_name = f"{file_id}{file_extension}"
        
        # 创建用户专属目录
        user_dir = HSAI_MATERIALS_DIR / user.id
        user_dir.mkdir(exist_ok=True)
        
        file_path = user_dir / file_name
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 计算文件哈希和大小
        file_size = len(content)
        file_hash = hashlib.md5(content).hexdigest()
        
        # 解析标签
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # 创建素材记录
        material_form = HSAIMaterialForm(
            name=name or file.filename,
            description=description,
            material_type=material_type,
            folder_id=folder_id,
            file_path=str(file_path),
            file_size=file_size,
            file_hash=file_hash,
            mime_type=mime_type,
            tags=tag_list,
            metadata={
                "original_filename": file.filename,
                "upload_time": int(time.time())
            }
        )
        
        material = HSAIMaterials.insert_new_material(user.id, material_form)
        if not material:
            # 删除已上传的文件
            try:
                os.remove(file_path)
            except:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create material record"
            )
        
        return HSAIMaterialResponse(
            **material.model_dump(),
            thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material_type in ["image", "video"] else None,
            download_url=f"/hsai/materials/{material.id}/download"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error uploading material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{material_id}/download", summary="下载素材")
async def download_material(
    material_id: str,
    user=Depends(get_verified_user)
):
    """
    下载素材文件。
    
    提供素材文件的直接下载服务，会自动增加使用次数统计。
    
    Args:
        material_id (str): 素材ID
        user: 已认证的用户对象
        
    Returns:
        FileResponse: 文件下载响应
        - 包含正确的文件名和MIME类型
        - 支持浏览器下载和预览
        
    Raises:
        HTTPException: 404 - 素材不存在、无权限访问或文件不存在
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 每次下载会增加素材的使用次数统计
        - 只能下载属于当前用户的素材
    """
    try:
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        file_path = Path(material.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk"
            )
        
        # 增加使用次数
        HSAIMaterials.increment_usage_count(material_id)
        
        return FileResponse(
            path=str(file_path),
            filename=material.name,
            media_type=material.mime_type or 'application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error downloading material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{material_id}/thumbnail", summary="获取素材缩略图")
async def get_material_thumbnail(
    material_id: str,
    user=Depends(get_verified_user)
):
    """
    获取素材缩略图。
    
    为图片和视频素材提供缩略图服务，用于快速预览。
    
    Args:
        material_id (str): 素材ID
        user: 已认证的用户对象
        
    Returns:
        FileResponse: 缩略图文件响应
        
    Raises:
        HTTPException: 404 - 素材不存在、无权限访问或缩略图不可用
        HTTPException: 400 - 该素材类型不支持缩略图
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 目前仅支持图片和视频素材的缩略图
        - 图片素材直接返回原图（简化实现）
        - 视频素材需要生成真实缩略图（待实现）
        - 其他类型素材不支持缩略图功能
    """
    try:
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        if material.material_type not in ["image", "video"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thumbnail not available for this material type"
            )
        
        # 简化版本：对于图片直接返回原图，视频返回占位符
        # 实际应用中应该生成真实的缩略图
        if material.material_type == "image":
            file_path = Path(material.file_path)
            if file_path.exists():
                return FileResponse(
                    path=str(file_path),
                    media_type=material.mime_type or 'image/jpeg'
                )
        
        # 返回默认缩略图占位符
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting material thumbnail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/{material_id}", response_model=HSAIMaterialResponse, summary="更新素材信息")
async def update_material(
    material_id: str,
    form_data: HSAIMaterialForm,
    user=Depends(get_verified_user)
):
    """
    更新素材信息。
    
    允许修改素材的元数据信息，如名称、描述、标签等，但不能修改文件本身。
    
    Args:
        material_id (str): 要更新的素材ID
        form_data (HSAIMaterialForm): 更新表单数据
        - name: 新的素材名称
        - description: 新的素材描述
        - folder_id: 新的文件夹ID（可用于移动素材）
        - tags: 新的标签列表
        - metadata: 新的元数据信息
        user: 已认证的用户对象
        
    Returns:
        HSAIMaterialResponse: 更新后的素材信息
        
    Raises:
        HTTPException: 404 - 素材不存在或无权限访问
        HTTPException: 400 - 更新失败
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 只能更新属于当前用户的素材
        - 文件内容和类型不能通过此接口修改
    """
    try:
        # 验证素材所有权
        existing_material = HSAIMaterials.get_material_by_id(material_id)
        if not existing_material or existing_material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        material = HSAIMaterials.update_material_by_id(material_id, form_data)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update material"
            )
        
        return HSAIMaterialResponse(
            **material.model_dump(),
            thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
            download_url=f"/hsai/materials/{material.id}/download"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.delete("/{material_id}", response_model=bool, summary="删除素材")
async def delete_material(
    material_id: str,
    user=Depends(get_verified_user)
):
    """
    删除素材。
    
    执行软删除操作，素材记录会被标记为已删除，但文件仍保留在磁盘上。
    
    Args:
        material_id (str): 要删除的素材ID
        user: 已认证的用户对象
        
    Returns:
        bool: 删除是否成功
        
    Raises:
        HTTPException: 404 - 素材不存在或无权限访问
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 当前实现为软删除，文件不会从磁盘删除
        - 只能删除属于当前用户的素材
        - 删除后素材将不再出现在列表中
        - 如需彻底删除文件，需要管理员手动清理
    """
    try:
        # 验证素材所有权
        existing_material = HSAIMaterials.get_material_by_id(material_id)
        if not existing_material or existing_material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        result = HSAIMaterials.delete_material_by_id(material_id)
        
        # 可选：实际删除文件（当前只做软删除）
        # if result and existing_material.file_path:
        #     try:
        #         os.remove(existing_material.file_path)
        #     except:
        #         pass
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error deleting material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# 素材统计
############################

class MaterialStatsResponse(BaseModel):
    total_materials: int
    materials_by_type: dict
    total_size: int
    folders_count: int
    recent_uploads: int


@router.get("/stats", response_model=MaterialStatsResponse, summary="获取素材统计")
async def get_material_stats(user=Depends(get_verified_user)):
    """
    获取素材统计信息。
    
    提供用户素材库的详细统计数据，用于仪表板展示和存储管理。
    
    Args:
        user: 已认证的用户对象
        
    Returns:
        MaterialStatsResponse: 统计信息
        - total_materials: 素材总数量
        - materials_by_type: 按类型分组的素材数量
          - image: 图片素材数量
          - video: 视频素材数量
          - audio: 音频素材数量
          - text: 文本素材数量
          - document: 文档素材数量
        - total_size: 所有素材文件的总大小（字节）
        - folders_count: 文件夹总数量
        - recent_uploads: 最近一周上传的素材数量
        
    Raises:
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 统计数据仅包含当前用户的素材
        - 文件大小统计基于上传时记录的大小
        - 最近上传统计基于最近7天的数据
    """
    try:
        materials = HSAIMaterials.get_materials_by_user_id(user.id)
        folders = HSAIMaterialFolders.get_folders_by_user_id(user.id)
        
        # 统计各类型素材数量
        materials_by_type = {}
        total_size = 0
        recent_uploads = 0
        current_time = int(time.time())
        week_ago = current_time - (7 * 24 * 60 * 60)
        
        for material in materials:
            # 按类型统计
            if material.material_type not in materials_by_type:
                materials_by_type[material.material_type] = 0
            materials_by_type[material.material_type] += 1
            
            # 累计文件大小
            if material.file_size:
                total_size += material.file_size
            
            # 最近一周上传数量
            if material.created_at > week_ago:
                recent_uploads += 1
        
        return MaterialStatsResponse(
            total_materials=len(materials),
            materials_by_type=materials_by_type,
            total_size=total_size,
            folders_count=len(folders),
            recent_uploads=recent_uploads
        )
        
    except Exception as e:
        log.exception(f"Error getting material stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )