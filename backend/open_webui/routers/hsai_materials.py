import logging
import time
import uuid
import re
import zipfile
import tempfile
import os
from typing import Optional, List
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydantic import Field

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
    HSAIMaterialResponse,
    # 添加分类相关的导入
    HSAIMaterialCategory,
    HSAIMaterialCategories,
    HSAIMaterialCategoryForm,
    HSAIMaterialCategoryModel,
    HSAIMaterialCategoryResponse,
    # 添加分页相关的导入
    PaginationData,
    PaginatedHSAIMaterialResponse,
    PaginatedHSAIMaterialCategoryResponse,
    # 添加文件操作日志相关的导入
    HSAIFileOperationLogForm,
    HSAIFileOperationLogResponse,
    HSAIFileOperationLogs
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

router = APIRouter(prefix="/hsai/materials", tags=["HSAI 素材管理"])

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

def _generate_filename_with_codes(material_name: str, scene_code: Optional[str], technique_code: Optional[str], properties_code: Optional[List[str]]) -> str:
    """
    根据分类代码生成文件名
    
    Args:
        material_name: 素材名称
        scene_code: 场景代码
        technique_code: 手法代码
        properties_code: 属性代码列表
        
    Returns:
        str: 生成的文件名
    """
    # 清理素材名称，移除特殊字符并确保使用英文字符
    clean_name = "".join(c for c in material_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    clean_name = clean_name.replace(' ', '_')
    
    # 确保所有组件都是英文字符
    if scene_code:
        scene_code = re.sub(r'[^a-zA-Z0-9_]', '', scene_code)
    
    if technique_code:
        technique_code = re.sub(r'[^a-zA-Z0-9_]', '', technique_code)
    
    if properties_code:
        # 确保属性代码列表中的每个元素都是英文字符
        properties_code = [re.sub(r'[^a-zA-Z0-9_]', '', prop) for prop in properties_code]
        # 过滤掉空字符串
        properties_code = [prop for prop in properties_code if prop]
    
    # 构建文件名组件
    filename_parts = [clean_name]
    
    if scene_code:
        filename_parts.append(scene_code)
    
    if technique_code:
        filename_parts.append(technique_code)
    
    if properties_code:
        # 将属性代码列表合并为单个字符串
        properties_str = "_".join(properties_code)
        filename_parts.append(properties_str)
    
    # 用下划线连接所有部分
    filename_base = "_".join(filename_parts)
    
    # 限制总长度以避免文件名过长
    if len(filename_base) > 100:
        filename_base = filename_base[:100]
    
    return filename_base

def _parse_filename_for_codes(filename: str) -> dict:
    """
    从文件名中解析分类代码信息
    
    Args:
        filename (str): 文件名
        
    Returns:
        dict: 包含解析出的分类代码信息
    """
    # 移除文件扩展名
    stem = Path(filename).stem
    
    # 尝试从文件名中提取哈希值（假设是文件名最后32个字符）
    hash_pattern = re.compile(r'([a-fA-F0-9]{32})$')
    hash_match = hash_pattern.search(stem)
    
    if hash_match:
        # 如果找到哈希值，移除它以获取基础文件名
        hash_value = hash_match.group(1)
        base_name = stem[:hash_match.start()]
        # 移除可能的尾部下划线
        if base_name.endswith('_'):
            base_name = base_name[:-1]
    else:
        base_name = stem
    
    # 分割文件名组件
    parts = base_name.split('_')
    
    if len(parts) < 2:
        # 文件名格式不符合预期
        return {
            "name": base_name,
            "scene_code": None,
            "technique_code": None,
            "properties_code": None
        }
    
    # 第一个部分是素材名称
    material_name = parts[0]
    
    # 其余部分可能是分类代码
    codes = parts[1:] if len(parts) > 1 else []
    
    # 简单的启发式解析（实际应用中可能需要更复杂的逻辑）
    scene_code = codes[0] if len(codes) > 0 else None
    technique_code = codes[1] if len(codes) > 1 else None
    properties_code = codes[2:] if len(codes) > 2 else None
    
    return {
        "name": material_name,
        "scene_code": scene_code,
        "technique_code": technique_code,
        "properties_code": properties_code
    }

def _process_zip_file(zip_file: UploadFile, user_id: str, base_scene_code: Optional[str], base_technique_code: Optional[str], base_properties_code: Optional[str]) -> List[dict]:
    """
    处理压缩包文件，解析目录结构并重命名文件
    
    Args:
        zip_file: 上传的压缩包文件
        user_id: 用户ID
        base_scene_code: 基础场景代码
        base_technique_code: 基础手法代码
        base_properties_code: 基属性代码
        
    Returns:
        List[dict]: 处理后的文件信息列表
    """
    processed_files = []
    
    # 创建临时目录来解压文件
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_path = temp_path / zip_file.filename
        
        # 保存压缩包到临时文件
        with open(zip_path, "wb") as f:
            content = zip_file.file.read()
            f.write(content)
        
        # 重置文件指针
        zip_file.file.seek(0)
        
        try:
            # 解压压缩包
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            
            # 遍历解压后的文件
            for root, dirs, files in os.walk(temp_path):
                for file in files:
                    file_path = Path(root) / file
                    # 跳过压缩包本身
                    if file_path == zip_path:
                        continue
                    
                    # 获取相对路径
                    relative_path = file_path.relative_to(temp_path)
                    
                    # 根据目录结构确定分类代码
                    scene_code = base_scene_code
                    technique_code = base_technique_code
                    properties_code = base_properties_code
                    
                    # 如果目录结构包含分类信息，可以从中提取
                    # 这里是一个简单的示例，实际应用中可能需要更复杂的逻辑
                    path_parts = relative_path.parts[:-1]  # 排除文件名
                    if len(path_parts) > 0:
                        # 假设第一层目录是场景
                        if not scene_code and len(path_parts) > 0:
                            scene_code = re.sub(r'[^a-zA-Z0-9_]', '', path_parts[0])[:10]
                        
                        # 假设第二层目录是手法
                        if not technique_code and len(path_parts) > 1:
                            technique_code = re.sub(r'[^a-zA-Z0-9_]', '', path_parts[1])[:10]
                    
                    # 生成文件名
                    file_name = file_path.stem
                    file_extension = file_path.suffix
                    new_filename = _generate_filename_with_codes(file_name, scene_code, technique_code, 
                                                                [properties_code] if properties_code else None)
                    new_filename = f"{new_filename}{file_extension}"
                    
                    # 读取文件内容
                    with open(file_path, "rb") as f:
                        file_content = f.read()
                    
                    # 创建文件信息
                    file_info = {
                        "original_filename": str(relative_path),
                        "new_filename": new_filename,
                        "content": file_content,
                        "scene_code": scene_code,
                        "technique_code": technique_code,
                        "properties_code": properties_code
                    }
                    
                    processed_files.append(file_info)
                    
        except Exception as e:
            log.error(f"Error processing zip file: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process zip file: {str(e)}"
            )
    
    return processed_files

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

@router.post("/upload", response_model=List[HSAIMaterialResponse], summary="上传素材到OSS")
async def upload_material(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    folder_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON字符串
    auto_analyze: bool = Form(True),
    # 新增分类代码参数
    scene_code: Optional[str] = Form(None),
    technique_code: Optional[str] = Form(None),
    properties_code: Optional[str] = Form(None),  # JSON字符串
    user=Depends(get_verified_user)
):
    """
    上传素材文件到阿里云OSS。
    
    支持多种文件格式的上传，包括图片、视频、音频、文档等。
    支持压缩包上传，系统会自动解析压缩包内的文件并按规则重命名。
    文件将直接上传到阿里云OSS存储，上传后可选择进行AI自动分析。
    
    Args:
        file (UploadFile): 要上传的文件（支持单个文件或压缩包）
        name (str, optional): 素材名称，默认使用文件名
        description (str, optional): 素材描述
        folder_id (str, optional): 目标文件夹ID
        tags (str, optional): 标签列表，JSON格式字符串
        auto_analyze (bool): 是否自动进行AI分析，默认True
        scene_code (str, optional): 场景代码
        technique_code (str, optional): 手法代码
        properties_code (str, optional): 属性代码，JSON格式字符串
        user: 已认证的用户对象
        
    Returns:
        List[HSAIMaterialResponse]: 上传成功的素材信息列表
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
        
        # 检查是否是压缩包
        is_zip = file.filename.lower().endswith(('.zip'))
        
        if is_zip:
            # 处理压缩包
            processed_files = _process_zip_file(file, user.id, scene_code, technique_code, properties_code)
            responses = []
            
            # 逐个上传处理后的文件
            for file_info in processed_files:
                # 生成文件哈希
                file_hash = hashlib.md5(file_info["content"]).hexdigest()
                
                # 确定文件类型
                mime_type = mimetypes.guess_type(file_info["new_filename"])[0]
                material_type = _determine_material_type(mime_type)
                
                # 生成OSS存储路径
                storage_filename = f"{Path(file_info['new_filename']).stem}_{file_hash}{Path(file_info['new_filename']).suffix}"
                
                # 上传文件到OSS
                try:
                    # 使用Storage provider上传到OSS
                    from io import BytesIO
                    file_like = BytesIO(file_info["content"])
                    
                    oss_url, oss_path = Storage.upload_file(
                        file=file_like,
                        filename=storage_filename,
                        tags={
                            "user_id": user.id,
                            "material_type": material_type,
                            "hsai_module": "materials",
                            "original_filename": file_info["original_filename"]
                        }
                    )
                    
                    log.info(f"Material uploaded to OSS: {oss_path}")
                    
                except Exception as upload_error:
                    log.error(f"OSS upload failed: {upload_error}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to upload file to OSS: {str(upload_error)}"
                    )
                
                # 提取文件元数据
                material_metadata = {
                    "original_filename": file_info["original_filename"],
                    "upload_time": int(time.time()),
                    "oss_url": oss_url,
                    "storage_provider": "oss"
                }
                
                # 初始化视频元数据
                duration = None
                resolution = None
                
                # 如果是视频文件，提取视频元数据
                if material_type == "video":
                    try:
                        # 保存到临时文件以提取元数据
                        with tempfile.NamedTemporaryFile(suffix=Path(file_info['new_filename']).suffix, delete=False) as tmp_file:
                            tmp_file.write(file_info["content"])
                            tmp_file_path = Path(tmp_file.name)
                        
                        try:
                            # 使用文件处理器提取元数据
                            from open_webui.utils.hsai_file_processor import HSAIFileProcessor
                            processor = HSAIFileProcessor(str(tmp_file_path.parent))
                            metadata = processor.extract_metadata(tmp_file_path, material_type)
                            
                            # 更新元数据
                            material_metadata.update(metadata)
                            
                            # 提取视频特定元数据
                            if "duration" in metadata:
                                duration = int(metadata["duration"])
                            if "width" in metadata and "height" in metadata:
                                resolution = f"{metadata['width']}x{metadata['height']}"
                        finally:
                            # 清理临时文件
                            tmp_file_path.unlink(missing_ok=True)
                    except Exception as meta_error:
                        log.warning(f"Failed to extract video metadata: {meta_error}")
                
                # 处理属性代码
                properties_list = None
                if file_info["properties_code"]:
                    properties_list = [file_info["properties_code"]]
                
                # 创建素材记录
                material_data = HSAIMaterialForm(
                    name=Path(file_info["new_filename"]).stem,
                    description=description,
                    material_type=material_type,
                    folder_id=folder_id,
                    file_path=oss_path,  # 存储OSS路径
                    file_size=len(file_info["content"]),
                    file_hash=file_hash,
                    mime_type=mime_type,
                    tags=json.loads(tags) if tags else None,
                    # 分类字段
                    scene_code=file_info["scene_code"],
                    technique_code=file_info["technique_code"],
                    properties_code="_".join(properties_list) if properties_list else None,
                    duration=duration,
                    resolution=resolution,
                    material_metadata=material_metadata
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
                
                response = HSAIMaterialResponse(
                    **material.model_dump(),
                    upload_url=oss_url,  # 返回OSS访问URL
                    thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material_type in ["image", "video"] else None,
                    download_url=oss_url  # 直接使用OSS URL进行下载
                )
                
                responses.append(response)
            
            return responses
        else:
            # 处理单个文件（原有逻辑）
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
            
            # 处理属性代码
            properties_list = None
            if properties_code:
                try:
                    properties_list = json.loads(properties_code)
                    # 确保是列表格式
                    if isinstance(properties_list, str):
                        properties_list = [properties_list]
                    elif not isinstance(properties_list, list):
                        properties_list = None
                except json.JSONDecodeError:
                    properties_list = None
            
            # 生成包含分类代码的文件名
            base_name = name or Path(file.filename).stem
            filename_base = _generate_filename_with_codes(base_name, scene_code, technique_code, properties_list)
            
            # 生成OSS存储路径
            file_extension = Path(file.filename).suffix
            storage_filename = f"{filename_base}_{file_hash}{file_extension}"
            
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
            
            # 提取文件元数据
            material_metadata = {
                "original_filename": file.filename,
                "upload_time": int(time.time()),
                "oss_url": oss_url,
                "storage_provider": "oss"
            }
            
            # 初始化视频元数据
            duration = None
            resolution = None
            
            # 如果是视频文件，提取视频元数据
            if material_type == "video":
                try:
                    # 这里应该调用文件处理器来提取元数据
                    # 由于我们是在内存中处理文件，我们需要先保存到临时文件
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp_file:
                        tmp_file.write(content)
                        tmp_file_path = Path(tmp_file.name)
                    
                    try:
                        # 使用文件处理器提取元数据
                        from open_webui.utils.hsai_file_processor import HSAIFileProcessor
                        processor = HSAIFileProcessor(str(tmp_file_path.parent))
                        metadata = processor.extract_metadata(tmp_file_path, material_type)
                        
                        # 更新元数据
                        material_metadata.update(metadata)
                        
                        # 提取视频特定元数据
                        if "duration" in metadata:
                            duration = int(metadata["duration"])
                        if "width" in metadata and "height" in metadata:
                            resolution = f"{metadata['width']}x{metadata['height']}"
                    finally:
                        # 清理临时文件
                        tmp_file_path.unlink(missing_ok=True)
                except Exception as meta_error:
                    log.warning(f"Failed to extract video metadata: {meta_error}")
            
            # 创建素材记录
            material_data = HSAIMaterialForm(
                name=base_name,
                description=description,
                material_type=material_type,
                folder_id=folder_id,
                file_path=oss_path,  # 存储OSS路径
                file_size=file_size,
                file_hash=file_hash,
                mime_type=mime_type,
                tags=json.loads(tags) if tags else None,
                # 新增字段
                scene_code=scene_code,
                technique_code=technique_code,
                properties_code="_".join(properties_list) if properties_list else None,
                duration=duration,
                resolution=resolution,
                material_metadata=material_metadata
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
            
            return [HSAIMaterialResponse(
                **material.model_dump(),
                upload_url=oss_url,  # 返回OSS访问URL
                thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material_type in ["image", "video"] else None,
                download_url=oss_url  # 直接使用OSS URL进行下载
            )]
        
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

@router.get("/", response_model=PaginatedHSAIMaterialResponse, summary="获取素材列表")
async def get_materials(
    folder_id: Optional[str] = Query(None, description="文件夹ID，为空则获取根目录素材"),
    material_type: Optional[str] = Query(None, description="素材类型过滤"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取用户的素材列表（分页）。
    
    支持按文件夹和类型过滤，支持分页查询。
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        materials = HSAIMaterials.get_materials_by_user_id(
            user.id, 
            folder_id=folder_id,
            material_type=material_type,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = HSAIMaterials.get_materials_count(
            user.id,
            folder_id=folder_id,
            material_type=material_type
        )
        
        responses = []
        for material in materials:
            # 确保返回OSS URL
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
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIMaterialResponse(
            data=responses,
            pagination=pagination
        )
        
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
        
        # 处理属性代码，将其转换为列表格式
        properties_list = None
        if material.properties_code:
            properties_list = material.properties_code.split("_")
        
        return HSAIMaterialResponse(
            id=material.id,
            name=material.name,
            description=material.description,
            material_type=material.material_type,
            folder_id=material.folder_id,
            file_path=material.file_path,
            file_size=material.file_size,
            mime_type=material.mime_type,
            material_metadata=material.material_metadata,
            tags=material.tags,
            ai_analysis=material.ai_analysis,
            usage_count=material.usage_count,
            last_used_at=material.last_used_at,
            status=material.status,
            scene_code=material.scene_code,
            technique_code=material.technique_code,
            properties_code=properties_list,  # 返回列表格式
            duration=material.duration,
            resolution=material.resolution,
            oss_bucket=material.oss_bucket,
            oss_key=material.oss_key,
            created_at=material.created_at,
            updated_at=material.updated_at,
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

@router.get("/search", response_model=PaginatedHSAIMaterialResponse, summary="搜索素材")
async def search_materials(
    query: str = Query(..., description="搜索关键词"),
    material_type: Optional[str] = Query(None, description="素材类型过滤"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    根据关键词搜索素材（分页）。
    
    支持按名称、描述、标签等字段进行模糊搜索。
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        materials = HSAIMaterials.search_materials(
            user.id, 
            query=query, 
            material_type=material_type,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        # 注意：当前search_materials方法不支持获取总数，需要修改数据库方法
        
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
        
        # 获取总数
        total = HSAIMaterials.count_search_materials(
            user.id,
            query=query,
            material_type=material_type
        )
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIMaterialResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error searching materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 素材统计
############################

class MaterialStatsResponse(BaseModel):
    total_materials: int
    folders_count: int
    type_distribution: dict
    total_size_mb: int
    recent_uploads: int


@router.get("/statistics", summary="获取素材统计")
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
        
        return MaterialStatsResponse(
            total_materials=len(materials),
            folders_count=len(folders),
            type_distribution=type_stats,
            total_size_mb=total_size // (1024 * 1024),
            recent_uploads=recent_uploads
        )
        
    except Exception as e:
        log.exception(f"Error getting material stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 素材属性查询
############################

# 调试语句，确认Field是否可用
# print(f"Field is available: {Field}")

class MaterialPropertiesResponse(BaseModel):
    """素材属性响应模型"""
    id: str = Field(description="素材唯一标识符")
    name: str = Field(description="素材名称")
    material_type: str = Field(description="素材类型")
    file_size: Optional[int] = Field(default=None, description="文件大小(字节)")
    mime_type: Optional[str] = Field(default=None, description="MIME类型")
    # 分类属性
    scene_code: Optional[str] = Field(default=None, description="场景代码")
    technique_code: Optional[str] = Field(default=None, description="手法代码")
    properties_code: Optional[List[str]] = Field(default=None, description="属性代码列表")
    # 视频属性
    duration: Optional[int] = Field(default=None, description="视频时长（秒）")
    resolution: Optional[str] = Field(default=None, description="视频分辨率")
    # OSS信息
    oss_bucket: Optional[str] = Field(default=None, description="OSS Bucket")
    oss_key: Optional[str] = Field(default=None, description="OSS对象键")
    # 其他元数据
    material_metadata: Optional[dict] = Field(default=None, description="素材元数据")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")

@router.get("/{material_id}/properties", response_model=MaterialPropertiesResponse, summary="获取素材属性")
async def get_material_properties(
    material_id: str,
    user=Depends(get_verified_user)
):
    """
    获取指定素材的详细属性信息。
    
    Args:
        material_id (str): 素材ID
        user: 已认证的用户对象
        
    Returns:
        MaterialPropertiesResponse: 素材属性信息
    """
    try:
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        # 处理属性代码，将其转换为列表格式
        properties_list = None
        if material.properties_code:
            properties_list = material.properties_code.split("_")
        
        return MaterialPropertiesResponse(
            id=material.id,
            name=material.name,
            material_type=material.material_type,
            file_size=material.file_size,
            mime_type=material.mime_type,
            scene_code=material.scene_code,
            technique_code=material.technique_code,
            properties_code=properties_list,
            duration=material.duration,
            resolution=material.resolution,
            oss_bucket=material.oss_bucket,
            oss_key=material.oss_key,
            material_metadata=material.material_metadata,
            created_at=material.created_at,
            updated_at=material.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting material properties: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 素材分类管理
############################

@router.get("/categories", response_model=PaginatedHSAIMaterialCategoryResponse, summary="获取素材分类列表")
async def get_material_categories(
    category_type: Optional[str] = Query(None, description="分类类型过滤：scene(场景)、technique(手法)、property(属性)"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1)
):
    """
    获取素材分类列表（分页），可按分类类型过滤。
    
    Args:
        category_type (str, optional): 分类类型过滤
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        
    Returns:
        PaginatedHSAIMaterialCategoryResponse: 分页的分类列表
        - data: 分类列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        # 获取分类列表
        if category_type:
            categories = HSAIMaterialCategories.get_categories_by_type(category_type)
        else:
            categories = HSAIMaterialCategories.get_all_categories()
        
        # 应用分页（在内存中分页）
        total = len(categories)
        start_idx = offset
        end_idx = offset + ps
        paginated_categories = categories[start_idx:end_idx]
        
        # 转换为响应模型
        responses = []
        for category in paginated_categories:
            response = HSAIMaterialCategoryResponse(
                id=category.id,
                name=category.name,
                display_name=category.display_name,
                category_type=category.category_type,
                description=category.description,
                is_active=category.is_active,
                created_at=category.created_at,
                updated_at=category.updated_at
            )
            responses.append(response)
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIMaterialCategoryResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting material categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/categories", response_model=HSAIMaterialCategoryResponse, summary="创建素材分类")
async def create_material_category(
    form_data: HSAIMaterialCategoryForm
):
    """
    创建新的素材分类。
    
    Args:
        form_data (HSAIMaterialCategoryForm): 分类表单数据
        
    Returns:
        HSAIMaterialCategoryResponse: 创建的分类信息
    """
    try:
        # 验证分类类型
        valid_types = ["scene", "technique", "property"]
        if form_data.category_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category type. Must be one of: {', '.join(valid_types)}"
            )
        
        # 验证分类名称长度（控制在10个字符以内）
        if len(form_data.name) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name must be 10 characters or less"
            )
        
        category = HSAIMaterialCategories.insert_new_category(form_data)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create category"
            )
        
        # 转换为响应模型
        response = HSAIMaterialCategoryResponse(
            id=category.id,
            name=category.name,
            display_name=category.display_name,
            category_type=category.category_type,
            description=category.description,
            is_active=category.is_active,
            created_at=category.created_at,
            updated_at=category.updated_at
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating material category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.put("/categories/{category_id}", response_model=HSAIMaterialCategoryResponse, summary="更新素材分类")
async def update_material_category(
    category_id: str,
    form_data: HSAIMaterialCategoryForm
):
    """
    更新指定的素材分类。
    
    Args:
        category_id (str): 分类ID
        form_data (HSAIMaterialCategoryForm): 分类表单数据
        
    Returns:
        HSAIMaterialCategoryResponse: 更新的分类信息
    """
    try:
        # 验证分类名称长度（控制在10个字符以内）
        if form_data.name and len(form_data.name) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name must be 10 characters or less"
            )
        
        category = HSAIMaterialCategories.get_category_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        updated_category = HSAIMaterialCategories.update_category_by_id(category_id, form_data)
        if not updated_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update category"
            )
        
        # 转换为响应模型
        response = HSAIMaterialCategoryResponse(
            id=updated_category.id,
            name=updated_category.name,
            display_name=updated_category.display_name,
            category_type=updated_category.category_type,
            description=updated_category.description,
            is_active=updated_category.is_active,
            created_at=updated_category.created_at,
            updated_at=updated_category.updated_at
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating material category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.delete("/categories/{category_id}", response_model=bool, summary="删除素材分类")
async def delete_material_category(
    category_id: str
):
    """
    删除指定的素材分类（软删除）。
    
    Args:
        category_id (str): 分类ID
        
    Returns:
        bool: 删除成功返回True
    """
    try:
        category = HSAIMaterialCategories.get_category_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        result = HSAIMaterialCategories.delete_category_by_id(category_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error deleting material category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

# 添加新的Pydantic模型用于回收站操作
class MoveToRecoveryRequest(BaseModel):
    """移入回收站请求模型"""
    operator_id: str
    reason: Optional[str] = None

class RestoreRequest(BaseModel):
    """还原文件请求模型"""
    target_directory: str
    operator_id: str

class PermanentDeleteRequest(BaseModel):
    """永久删除请求模型"""
    operator_id: str
    reason: Optional[str] = None

class BatchOperationRequest(BaseModel):
    """批量操作请求模型"""
    operation: str  # "restore" 或 "delete"
    material_ids: List[str]
    target_directory: Optional[str] = None  # restore操作时必需
    operator_id: str

# 添加文件操作日志模型
class FileOperationLogModel(BaseModel):
    """文件操作日志模型"""
    id: str
    material_id: str
    operation_type: str
    source_path: str
    target_path: Optional[str] = None
    operator_id: str
    operation_time: int
    details: Optional[dict] = None
    created_at: int
    updated_at: int

class FileOperationLogForm(BaseModel):
    """文件操作日志表单模型"""
    material_id: str
    operation_type: str
    source_path: str
    target_path: Optional[str] = None
    operator_id: str
    operation_time: int
    details: Optional[dict] = None

class FileOperationLogResponse(BaseModel):
    """文件操作日志响应模型"""
    id: str = Field(description="日志唯一标识符")
    material_id: str = Field(description="素材唯一标识符")
    operation_type: str = Field(description="操作类型（upload/delete/restore/move/modify）")
    source_path: str = Field(description="源文件路径")
    target_path: Optional[str] = Field(default=None, description="目标文件路径")
    operator_id: str = Field(description="操作人ID")
    operation_time: int = Field(description="操作时间")
    details: Optional[dict] = Field(default=None, description="操作详情")
    created_at: int = Field(description="创建时间戳")
    updated_at: int = Field(description="更新时间戳")


class PaginatedHSAIFileOperationLogResponse(BaseModel):
    """分页的文件操作日志响应模型"""
    data: List[FileOperationLogResponse]
    pagination: PaginationData

# 添加文件操作日志的辅助函数
async def _log_file_operation(
    material_id: str,
    operation_type: str,
    source_path: str,
    operator_id: str,
    target_path: Optional[str] = None,
    details: Optional[dict] = None
):
    """
    记录文件操作日志
    
    Args:
        material_id: 素材ID
        operation_type: 操作类型
        source_path: 源路径
        operator_id: 操作人ID
        target_path: 目标路径（可选）
        details: 操作详情（可选）
    """
    # 这里应该将日志保存到数据库
    # 为简化实现，我们只记录到日志中
    log.info(f"File operation logged: material_id={material_id}, operation_type={operation_type}, "
             f"source_path={source_path}, target_path={target_path}, operator_id={operator_id}, details={details}")

############################
# 回收站管理接口
############################

@router.post("/{material_id}/move-to-recovery", response_model=HSAIMaterialResponse, summary="移入回收站（软删除）")
async def move_material_to_recovery(
    material_id: str,
    request: MoveToRecoveryRequest,
    user=Depends(get_verified_user)
):
    """
    将指定素材从原目录移动到回收站目录，在数据库中更新删除标志位和原目录信息，记录操作日志
    
    Args:
        material_id (str): 素材唯一标识符
        request (MoveToRecoveryRequest): 请求参数
        user: 已认证的用户对象
        
    Returns:
        HSAIMaterialResponse: 更新后的素材信息
    """
    try:
        # 获取素材信息
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        # 更新素材信息
        update_data = {
            "is_deleted": True,
            "original_directory": material.file_path,
            "deleted_at": int(time.time()),
            "deleted_by": request.operator_id
        }
        
        updated_material = HSAIMaterials.update_material_by_id(material_id, HSAIMaterialForm(**update_data))
        if not updated_material:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to move material to recovery"
            )
        
        # 记录操作日志
        await _log_file_operation(
            material_id=material_id,
            operation_type="delete",
            source_path=material.file_path,
            target_path=f"recovery/{material_id}",
            operator_id=request.operator_id,
            details={"reason": request.reason} if request.reason else None
        )
        
        # 返回更新后的素材信息
        return HSAIMaterialResponse(
            **updated_material.model_dump(),
            upload_url=updated_material.file_path,
            thumbnail_url=f"/hsai/materials/{material_id}/thumbnail" if updated_material.material_type in ["image", "video"] else None,
            download_url=updated_material.file_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error moving material to recovery: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/recovery/{material_id}/restore", response_model=HSAIMaterialResponse, summary="还原文件")
async def restore_material(
    material_id: str,
    request: RestoreRequest,
    user=Depends(get_verified_user)
):
    """
    将回收站中的文件还原到指定目录，更新数据库记录，记录操作日志
    
    Args:
        material_id (str): 素材唯一标识符
        request (RestoreRequest): 请求参数
        user: 已认证的用户对象
        
    Returns:
        HSAIMaterialResponse: 更新后的素材信息
    """
    try:
        # 获取素材信息
        material = HSAIMaterials.get_material_by_id(material_id)
        if not material or material.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        if not material.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Material is not in recovery"
            )
        
        # 更新素材信息
        update_data = {
            "is_deleted": False,
            "file_path": material.original_directory,  # 还原到原始目录
            "original_directory": None,
            "deleted_at": None,
            "deleted_by": None
        }
        
        updated_material = HSAIMaterials.update_material_by_id(material_id, HSAIMaterialForm(**update_data))
        if not updated_material:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to restore material"
            )
        
        # 记录操作日志
        await _log_file_operation(
            material_id=material_id,
            operation_type="restore",
            source_path=f"recovery/{material_id}",
            target_path=updated_material.file_path,
            operator_id=request.operator_id
        )
        
        # 返回更新后的素材信息
        return HSAIMaterialResponse(
            **updated_material.model_dump(),
            upload_url=updated_material.file_path,
            thumbnail_url=f"/hsai/materials/{material_id}/thumbnail" if updated_material.material_type in ["image", "video"] else None,
            download_url=updated_material.file_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error restoring material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.delete("/{material_id}/permanent-delete", response_model=bool, summary="永久删除文件")
async def permanent_delete_material(
    material_id: str,
    request: PermanentDeleteRequest,
    user=Depends(get_verified_user)
):
    """
    根据素材ID在素材表中找到对应的记录，通过素材文件的位置信息确定需要删除的OSS文件
    （企业目录或回收站目录中的文件），彻底删除OSS文件和数据库记录，记录操作日志。
    此接口统一处理所有永久删除操作，客户端无需关心文件具体位置。
    
    Args:
        material_id (str): 素材唯一标识符
        request (PermanentDeleteRequest): 请求参数
        user: 已认证的用户对象
        
    Returns:
        bool: 删除成功返回True
    """
    try:
        # 获取素材信息
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
        
        # 记录操作日志
        await _log_file_operation(
            material_id=material_id,
            operation_type="permanent_delete",
            source_path=material.file_path,
            operator_id=request.operator_id,
            details={"reason": request.reason} if request.reason else None
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error permanently deleting material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/recovery/list", response_model=PaginatedHSAIMaterialResponse, summary="获取回收站文件列表")
async def get_recovery_materials(
    enterprise_id: str,
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    sort_by: str = Query("delete_time", description="排序字段（delete_time/name/size）"),
    order: str = Query("desc", description="排序方式（asc/desc）"),
    user=Depends(get_verified_user)
):
    """
    获取指定企业回收站中的文件列表
    
    Args:
        enterprise_id (str): 企业ID
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        sort_by (str): 排序字段（delete_time/name/size），默认delete_time
        order (str): 排序方式（asc/desc），默认desc
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAIMaterialResponse: 分页的回收站文件列表
        - data: 回收站文件列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        # 获取企业已删除的素材
        materials = HSAIMaterials.get_deleted_materials_by_enterprise(
            enterprise_id, 
            limit=ps, 
            offset=offset
        )
        
        # 获取总数
        total = HSAIMaterials.count_deleted_materials_by_enterprise(enterprise_id)
        
        # 转换为响应模型
        responses = []
        for material in materials:
            response = HSAIMaterialResponse(
                **material.model_dump(),
                upload_url=material.file_path,
                thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
                download_url=material.file_path
            )
            responses.append(response)
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIMaterialResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting recovery materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/recovery/batch-operation", response_model=bool, summary="批量操作回收站文件")
async def batch_operation_recovery_materials(
    request: BatchOperationRequest,
    user=Depends(get_verified_user)
):
    """
    对回收站中的多个文件进行批量还原或删除操作
    
    Args:
        request (BatchOperationRequest): 请求参数
        user: 已认证的用户对象
        
    Returns:
        bool: 操作成功返回True
    """
    try:
        success_count = 0
        
        for material_id in request.material_ids:
            try:
                if request.operation == "restore":
                    if not request.target_directory:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Target directory is required for restore operation"
                        )
                    
                    # 还原操作
                    update_data = {
                        "is_deleted": False,
                        "original_directory": None,
                        "deleted_at": None,
                        "deleted_by": None
                    }
                    
                    result = HSAIMaterials.update_material_by_id(material_id, HSAIMaterialForm(**update_data))
                    if result:
                        success_count += 1
                        
                        # 记录操作日志
                        await _log_file_operation(
                            material_id=material_id,
                            operation_type="restore",
                            source_path=f"recovery/{material_id}",
                            target_path=request.target_directory,
                            operator_id=request.operator_id
                        )
                        
                elif request.operation == "delete":
                    # 永久删除操作
                    material = HSAIMaterials.get_material_by_id(material_id)
                    if material and material.user_id == user.id:
                        # 删除OSS文件
                        try:
                            Storage.delete_file(material.file_path)
                        except Exception as e:
                            log.warning(f"Failed to delete OSS file {material.file_path}: {e}")
                        
                        # 删除数据库记录
                        if HSAIMaterials.delete_material_by_id(material_id):
                            success_count += 1
                            
                            # 记录操作日志
                            await _log_file_operation(
                                material_id=material_id,
                                operation_type="permanent_delete",
                                source_path=material.file_path,
                                operator_id=request.operator_id
                            )
                
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid operation: {request.operation}"
                    )
                    
            except Exception as e:
                log.warning(f"Error processing material {material_id}: {e}")
                continue
        
        return success_count == len(request.material_ids)
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error in batch operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 文件操作日志接口
############################

@router.post("/logs", response_model=HSAIFileOperationLogResponse, summary="记录文件操作日志")
async def log_file_operation(
    form_data: FileOperationLogForm,
    user=Depends(get_verified_user)
):
    """
    记录文件操作日志
    
    Args:
        form_data (FileOperationLogForm): 日志表单数据
        user: 已认证的用户对象
        
    Returns:
        HSAIFileOperationLogResponse: 创建的日志信息
    """
    try:
        # 转换表单数据为数据库模型
        hsai_form_data = HSAIFileOperationLogForm(**form_data.model_dump())
        
        # 创建日志记录
        log_entry = HSAIFileOperationLogs.insert_new_log(hsai_form_data)
        if not log_entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create log entry"
            )
        
        return HSAIFileOperationLogResponse(**log_entry.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error logging file operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/logs", response_model=PaginatedHSAIFileOperationLogResponse, summary="查询文件操作日志")
async def get_file_operation_logs(
    material_id: Optional[str] = Query(None, description="素材唯一标识符"),
    enterprise_id: Optional[str] = Query(None, description="企业ID"),
    operation_type: Optional[str] = Query(None, description="操作类型"),
    operator_id: Optional[str] = Query(None, description="操作人ID"),
    start_time: Optional[int] = Query(None, description="查询起始时间"),
    end_time: Optional[int] = Query(None, description="查询结束时间"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    查询文件操作日志（分页）
    
    Args:
        material_id (str, optional): 素材唯一标识符
        enterprise_id (str, optional): 企业ID
        operation_type (str, optional): 操作类型
        operator_id (str, optional): 操作人ID
        start_time (int, optional): 查询起始时间
        end_time (int, optional): 查询结束时间
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAIFileOperationLogResponse: 分页的文件操作日志列表
        - data: 日志列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        # 获取日志列表
        logs = HSAIFileOperationLogs.get_logs(
            material_id=material_id,
            enterprise_id=enterprise_id,
            operation_type=operation_type,
            operator_id=operator_id,
            start_time=start_time,
            end_time=end_time,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = HSAIFileOperationLogs.get_logs_count(
            material_id=material_id,
            enterprise_id=enterprise_id,
            operation_type=operation_type,
            operator_id=operator_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # 转换为响应模型
        responses = [HSAIFileOperationLogResponse(**log.model_dump()) for log in logs]
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIFileOperationLogResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting file operation logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/{material_id}/history", response_model=PaginatedHSAIFileOperationLogResponse, summary="获取文件操作历史")
async def get_material_history(
    material_id: str,
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取指定文件的所有操作历史记录（分页）
    
    Args:
        material_id (str): 素材唯一标识符
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAIFileOperationLogResponse: 分页的文件操作历史记录列表
        - data: 历史记录列表
        - pagination: 分页信息
          - total: 总记录数
          - page: 当前页码
          - size: 每页大小
          - total_pages: 总页数
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        # 获取指定素材的日志列表
        logs = HSAIFileOperationLogs.get_logs(
            material_id=material_id,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = HSAIFileOperationLogs.get_logs_count(material_id=material_id)
        
        # 转换为响应模型
        responses = [HSAIFileOperationLogResponse(**log.model_dump()) for log in logs]
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIFileOperationLogResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting material history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )
