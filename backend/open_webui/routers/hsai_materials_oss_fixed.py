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

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/materials", tags=["hsai_materials"])

# HSAI素材存储配置 - 使用OSS存储
HSAI_MATERIALS_PREFIX = "hsai/materials"  # OSS存储前缀

############################
# 辅助函数
############################

def _determine_material_type(mime_type: str) -> str:
    """根据MIME类型确定素材类型"""
    if not mime_type:
        return "document"
    
    if mime_type.startswith("image/"):
        return "image"
    elif mime_type.startswith("video/"):
        return "video"
    elif mime_type.startswith("audio/"):
        return "audio"
    elif mime_type.startswith("text/"):
        return "text"
    elif mime_type in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        return "document"
    else:
        return "document"

async def _schedule_ai_analysis(material_id: str, oss_url: str, material_type: str, user_id: str):
    """异步调度AI分析任务"""
    # 这里可以集成AI分析服务
    # 例如：图片识别、视频内容分析、文档OCR等
    log.info(f"Scheduling AI analysis for material {material_id} of type {material_type}")
    pass

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

############################
# 素材上传 - OSS集成版本
############################

@router.post("/upload", response_model=HSAIMaterialResponse, summary="上传素材到OSS")
async def upload_material(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    folder_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON字符串
    auto_analyze: bool = Form(True),
    user=Depends(get_verified_user)
):
    """
    上传素材文件到阿里云OSS。
    
    支持多种文件格式的上传，包括图片、视频、音频、文档等。
    文件将直接上传到阿里云OSS存储，上传后可选择进行AI自动分析。
    
    Args:
        file (UploadFile): 要上传的文件
        name (str, optional): 素材名称，默认使用文件名
        description (str, optional): 素材描述
        folder_id (str, optional): 目标文件夹ID
        tags (str, optional): 标签列表，JSON格式字符串
        auto_analyze (bool): 是否自动进行AI分析，默认True
        user: 已认证的用户对象
        
    Returns:
        HSAIMaterialResponse: 上传成功的素材信息
        - id: 素材ID
        - name: 素材名称
        - file_path: OSS存储路径
        - file_size: 文件大小
        - mime_type: 文件MIME类型
        - material_type: 素材类型
        - upload_url: OSS文件访问URL
        
    Raises:
        HTTPException: 400 - 文件格式不支持或文件过大
        HTTPException: 500 - 上传失败或服务器错误
    """
    try:
        # 验证文件
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # 检查文件大小（100MB限制）
        content = await file.read()
        file_size = len(content)
        
        if file_size > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 100MB limit"
            )
        
        # 重置文件指针
        await file.seek(0)
        
        # 生成文件哈希
        file_hash = hashlib.md5(content).hexdigest()
        
        # 确定文件类型
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        material_type = _determine_material_type(mime_type)
        
        # 生成OSS存储路径
        file_extension = Path(file.filename).suffix
        storage_filename = f"{file_hash}{file_extension}"
        
        # 上传文件到OSS
        try:
            # 使用Storage provider上传到OSS
            oss_url, oss_path = Storage.upload_file(
                file=file.file,
                filename=storage_filename,
                tags={
                    "user_id": user.id,
                    "material_type": material_type,
                    "hsai_module": "materials",
                    "original_filename": file.filename
                }
            )
            
            log.info(f"Material uploaded to OSS: {oss_path}")
            
        except Exception as upload_error:
            log.error(f"OSS upload failed: {upload_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to OSS: {str(upload_error)}"
            )
        
        # 创建素材记录
        material_data = HSAIMaterialForm(
            name=name or Path(file.filename).stem,
            description=description,
            material_type=material_type,
            folder_id=folder_id,
            file_path=oss_path,  # 存储OSS路径
            file_size=file_size,
            file_hash=file_hash,
            mime_type=mime_type,
            tags=json.loads(tags) if tags else None,
            material_metadata={
                "original_filename": file.filename,
                "upload_time": int(time.time()),
                "oss_url": oss_url,
                "storage_provider": "oss"
            }
        )
        
        material = HSAIMaterials.insert_new_material(user.id, material_data)
        if not material:
            # 如果数据库记录创建失败，尝试删除OSS文件
            try:
                Storage.delete_file(oss_path)
            except:
                log.warning(f"Failed to cleanup OSS file after database error: {oss_path}")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create material record"
            )
        
        # 如果启用自动分析，异步执行AI分析
        if auto_analyze:
            try:
                await _schedule_ai_analysis(material.id, oss_url, material_type, user.id)
            except Exception as ai_error:
                log.warning(f"Failed to schedule AI analysis: {ai_error}")
        
        return HSAIMaterialResponse(
            **material.model_dump(),
            upload_url=oss_url,  # 返回OSS访问URL
            thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material_type in ["image", "video"] else None,
            download_url=oss_url  # 直接使用OSS URL进行下载
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error uploading material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 素材下载 - OSS集成版本
############################

@router.get("/{material_id}/download", summary="获取素材下载链接")
async def get_material_download_url(
    material_id: str,
    user=Depends(get_verified_user)
):
    """
    获取素材的OSS下载链接。
    
    返回可直接访问的OSS URL，支持CDN加速。
    
    Args:
        material_id (str): 素材ID
        user: 已认证的用户对象
        
    Returns:
        dict: 包含下载URL和文件信息
        - download_url: OSS访问URL
        - filename: 文件名
        - file_size: 文件大小
        - mime_type: 文件MIME类型
        
    Raises:
        HTTPException: 404 - 素材不存在或无权限访问
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 每次访问会增加素材的使用次数统计
        - 只能访问属于当前用户的素材
        - 返回的是OSS直链，支持CDN加速
    """
    try:
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        # 增加使用次数
        HSAIMaterials.increment_usage_count(material_id)
        
        # 如果存储的是OSS路径，直接返回
        if material.file_path.startswith(('http://', 'https://', 's3://', 'gs://')):
            return {
                "download_url": material.file_path,
                "filename": material.name,
                "file_size": material.file_size,
                "mime_type": material.mime_type
            }
        
        # 如果是本地路径，需要通过Storage获取
        try:
            download_url = Storage.get_file(material.file_path)
            return {
                "download_url": download_url,
                "filename": material.name,
                "file_size": material.file_size,
                "mime_type": material.mime_type
            }
        except Exception as e:
            log.error(f"Failed to get download URL: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 素材管理
############################

@router.get("/", response_model=List[HSAIMaterialResponse], summary="获取素材列表")
async def get_materials(
    folder_id: Optional[str] = Query(None, description="文件夹ID，为空则获取根目录素材"),
    material_type: Optional[str] = Query(None, description="素材类型过滤"),
    limit: int = Query(20, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    user=Depends(get_verified_user)
):
    """
    获取用户的素材列表。
    
    支持按文件夹和类型过滤，支持分页查询。
    """
    try:
        materials = HSAIMaterials.get_materials_by_user_id(
            user.id, 
            folder_id=folder_id,
            material_type=material_type,
            limit=limit,
            offset=offset
        )
        
        responses = []
        for material in materials:
            # 确保返回OSS URL
            download_url = material.file_path
            if not download_url.startswith(('http://', 'https://')):
                # 如果不是完整URL，尝试构建OSS URL
                download_url = f"/hsai/materials/{material.id}/download"
            
            response = HSAIMaterialResponse(
                **material.model_dump(),
                upload_url=download_url,
                thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
                download_url=download_url
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        log.exception(f"Error getting materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/{material_id}", response_model=HSAIMaterialResponse, summary="获取素材详情")
async def get_material(
    material_id: str,
    user=Depends(get_verified_user)
):
    """
    获取指定素材的详细信息。
    """
    try:
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        # 确保返回OSS URL
        download_url = material.file_path
        if not download_url.startswith(('http://', 'https://')):
            download_url = f"/hsai/materials/{material.id}/download"
        
        return HSAIMaterialResponse(
            **material.model_dump(),
            upload_url=download_url,
            thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
            download_url=download_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting material: {e}")
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
    删除指定的素材文件。
    
    会同时删除OSS中的文件和数据库记录。
    """
    try:
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        # 删除OSS文件
        try:
            Storage.delete_file(material.file_path)
        except Exception as e:
            log.warning(f"Failed to delete OSS file {material.file_path}: {e}")
        
        # 删除数据库记录
        result = HSAIMaterials.delete_material_by_id(material_id)
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
# 素材搜索
############################

@router.get("/search", response_model=List[HSAIMaterialResponse], summary="搜索素材")
async def search_materials(
    query: str = Query(..., description="搜索关键词"),
    material_type: Optional[str] = Query(None, description="素材类型过滤"),
    limit: int = Query(20, description="返回数量限制"),
    user=Depends(get_verified_user)
):
    """
    根据关键词搜索素材。
    
    支持按名称、描述、标签等字段进行模糊搜索。
    """
    try:
        materials = HSAIMaterials.search_materials(
            user.id, 
            query=query, 
            material_type=material_type,
            limit=limit
        )
        
        responses = []
        for material in materials:
            download_url = material.file_path
            if not download_url.startswith(('http://', 'https://')):
                download_url = f"/hsai/materials/{material.id}/download"
            
            response = HSAIMaterialResponse(
                **material.model_dump(),
                upload_url=download_url,
                thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
                download_url=download_url
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        log.exception(f"Error searching materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 素材统计
############################

@router.get("/stats", summary="获取素材统计")
async def get_material_stats(user=Depends(get_verified_user)):
    """
    获取用户的素材统计信息。
    
    包括总数量、各类型数量、存储使用量等。
    """
    try:
        materials = HSAIMaterials.get_materials_by_user_id(user.id)
        folders = HSAIMaterialFolders.get_folders_by_user_id(user.id)
        
        # 统计各类型数量
        type_stats = {}
        total_size = 0
        recent_uploads = 0
        current_time = int(time.time())
        week_ago = current_time - (7 * 24 * 3600)
        
        for material in materials:
            # 类型统计
            material_type = material.material_type
            type_stats[material_type] = type_stats.get(material_type, 0) + 1
            
            # 大小统计
            if material.file_size:
                total_size += material.file_size
            
            # 最近上传统计
            if material.created_at > week_ago:
                recent_uploads += 1
        
        return {
            "total_materials": len(materials),
            "folders_count": len(folders),
            "type_distribution": type_stats,
            "total_size_mb": total_size // (1024 * 1024),
            "recent_uploads": recent_uploads
        }
        
    except Exception as e:
        log.exception(f"Error getting material stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )