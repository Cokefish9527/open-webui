import logging
import time
import uuid
import re
import zipfile
import tempfile
import os
import logging
from typing import Dict, List, Optional, Tuple
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
    # 添加分页相关的导入
    PaginationData,
    PaginatedHSAIMaterialResponse
)
from open_webui.internal.db import get_db
from open_webui.services.material_checklist_service import (
    ChecklistTreeNode,
    material_checklist_service,
)

from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.config import UPLOAD_DIR
from open_webui.config.oss import STORAGE_PROVIDER, S3_BUCKET_NAME

import aiofiles
import hashlib
import mimetypes
import json
try:
    from open_webui.storage.provider import Storage
    HAS_OSS = True
except ImportError:
    HAS_OSS = False

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/materials", tags=["HSAI 素材管理"])

# HSAI素材存储配置 - 使用OSS存储
HSAI_MATERIALS_PREFIX = "hsai/materials"  # OSS存储前缀

# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
LOCAL_STORAGE_PATH = os.path.join(UPLOAD_DIR, "materials")
os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True)

DEFAULT_COMPANY_SEGMENT = "default-company"
DEFAULT_USER_SEGMENT = "unknown-user"


def _normalize_segment_for_oss(value: Optional[str], fallback: str) -> str:
    """Allow中文, but strip characters that break object keys (newline, slash, etc.)."""
    if not value:
        return fallback
    segment = value.strip()
    if not segment:
        return fallback
    for ch in ("/", "\\", "\n", "\r", "\t"):
        segment = segment.replace(ch, "-")
    return segment or fallback


def _convert_checklist_node_to_response(
    node: ChecklistTreeNode,
    parent_id: Optional[str] = None,
    parent_name: Optional[str] = None,
) -> HSAIMaterialFolderResponse:
    timestamp = int(time.time())
    children = (
        [
            _convert_checklist_node_to_response(child, node.id, node.name)
            for child in (node.children or [])
        ]
        if node.children
        else []
    )

    return HSAIMaterialFolderResponse(
        id=node.id,
        name=node.name,
        label=node.name,
        description=node.description,
        parent_id=parent_id,
        parent_name=parent_name,
        sort_order=0,
        material_count=node.material_count,
        children=children,
        node_type=node.node_type,
        template_id=node.template_id,
        template_code=node.template_code,
        scene_id=node.scene_id,
        scene_code=node.scene_code,
        item_id=node.item_id,
        item_code=node.item_code,
        is_required=node.is_required,
        shot_sizes=node.shot_sizes,
        camera_movements=node.camera_movements,
        duration_min=node.duration_min,
        duration_max=node.duration_max,
        min_resolution=node.min_resolution,
        priority=node.priority,
        shooting_tips=node.shooting_tips,
        quality_standards=node.quality_standards,
        reference_video=node.reference_video,
        reference_image=node.reference_image,
        created_at=timestamp,
        updated_at=timestamp,
    )


def _filter_folder_responses(
    nodes: List[HSAIMaterialFolderResponse], query_lower: str
) -> List[HSAIMaterialFolderResponse]:
    filtered: List[HSAIMaterialFolderResponse] = []
    for node in nodes:
        children = _filter_folder_responses(node.children or [], query_lower)
        match = False
        if node.name and query_lower in node.name.lower():
            match = True
        elif node.description and query_lower in node.description.lower():
            match = True

        if match or children:
            node.children = children
            filtered.append(node)
    return filtered


def _collect_scene_codes(node: ChecklistTreeNode) -> List[str]:
    codes: List[str] = []
    if node.scene_code:
        codes.append(node.scene_code)
    for child in node.children or []:
        codes.extend(_collect_scene_codes(child))
    return list({code for code in codes if code})


def _resolve_folder_context(
    user,
    folder_id: Optional[str],
) -> Tuple[Optional[str], Optional[ChecklistTreeNode]]:
    if not folder_id or ":" not in folder_id:
        return folder_id, None
    node = material_checklist_service.get_node(user, folder_id)
    if not node:
        return folder_id, None
    return None, node


def _extract_codes_from_node(
    node: Optional[ChecklistTreeNode],
    scene_code: Optional[str],
    item_code: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[str]]:
    if not node:
        return scene_code, item_code, None, None

    if node.node_type == "item":
        return (
            scene_code or node.scene_code,
            item_code or node.item_code,
            None,
            node.scene_name or node.scene_code,
        )
    if node.node_type == "scene":
        return (
            scene_code or node.scene_code,
            item_code,
            None,
            node.name,
        )
    if node.node_type == "template":
        codes = _collect_scene_codes(node)
        return scene_code, item_code, codes or None, None
    return scene_code, item_code, None, None


def _count_tree_nodes(nodes: List[ChecklistTreeNode]) -> int:
    total = 0
    for node in nodes:
        total += 1
        if node.children:
            total += _count_tree_nodes(node.children)
    return total


def _is_oss_mode() -> bool:
    """当前是否运行在 OSS 存储模式"""
    return HAS_OSS and STORAGE_PROVIDER.lower() in {"s3", "oss"}


def _sanitize_path_segment(value: Optional[str], fallback: str) -> str:
    """
    将任意字符串转换为路径安全的片段，仅保留字母、数字、下划线和中划线。
    """
    if not value:
        return fallback
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", value.strip())
    sanitized = sanitized.strip("-_")
    return (sanitized or fallback).lower()


def _resolve_business_name(user) -> str:
    """
    从用户对象中解析公司名称，若不存在则返回默认值。
    """
    name = getattr(user, "business_name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    info = getattr(user, "info", None)
    if isinstance(info, dict):
        info_name = info.get("business_name")
        if isinstance(info_name, str) and info_name.strip():
            return info_name.strip()
    return DEFAULT_COMPANY_SEGMENT


def _resolve_company_display(user) -> str:
    return _normalize_segment_for_oss(_resolve_business_name(user), DEFAULT_COMPANY_SEGMENT)


def _get_storage_segments(user) -> Tuple[str, str]:
    """
    计算存储路径使用的公司与用户目录片段。
    """
    business_segment = _sanitize_path_segment(
        _resolve_business_name(user), DEFAULT_COMPANY_SEGMENT
    )
    user_segment = _sanitize_path_segment(getattr(user, "id", None), DEFAULT_USER_SEGMENT)
    return business_segment, user_segment


def _build_storage_key(storage_filename: str, business_segment: str, user_segment: str) -> str:
    """根据公司与用户目录生成对象键"""
    return f"{business_segment}/{user_segment}/{storage_filename}"


def _build_storage_filename(base_filename: str, content_hash: str) -> str:
    """
    为素材生成带哈希的唯一文件名，保留原扩展名。
    """
    path = Path(base_filename)
    safe_stem = path.stem or "material"
    return f"{safe_stem}_{content_hash}{path.suffix}"


def _build_project_filename(project_name: Optional[str], original_filename: str) -> str:
    original_suffix = Path(original_filename).suffix or ""
    base = _normalize_segment_for_oss(project_name or Path(original_filename).stem, "material")
    return f"{base}{original_suffix}"


def _build_oss_relative_path(
    company_segment: str,
    scene_segment: str,
    filename: str,
) -> str:
    cleaned_filename = filename.lstrip("/")
    return f"{company_segment}/{scene_segment}/{cleaned_filename}"


def _store_material_file(
    content: bytes,
    storage_filename: str,
    user,
    material_type: str,
    original_filename: str,
    *,
    oss_object_path: Optional[str] = None,
) -> dict:
    """
    将素材文件保存到本地或 OSS，返回存储元数据。
    """
    business_segment, user_segment = _get_storage_segments(user)
    storage_key = oss_object_path or _build_storage_key(
        storage_filename, business_segment, user_segment
    )

    storage_provider = "local"
    file_url = ""
    file_path = ""
    oss_bucket = None
    oss_key = None

    if _is_oss_mode():
        try:
            from io import BytesIO

            file_like = BytesIO(content)
            _, storage_path = Storage.upload_file(
                file=file_like,
                filename=storage_key,
                tags={
                    "user_id": str(getattr(user, "id", "")),
                    "material_type": material_type,
                    "hsai_module": "materials",
                    "original_filename": original_filename,
                    "business_segment": business_segment,
                },
            )
            storage_provider = "oss"
            file_path = str(storage_path)
            file_url = str(storage_path)
            oss_bucket = S3_BUCKET_NAME or (
                storage_path.split("//", 1)[1].split("/", 1)[0]
                if isinstance(storage_path, str)
                and storage_path.startswith(("s3://", "https://"))
                else None
            )
            oss_key = storage_key
        except Exception as upload_error:
            log.warning(
                "OSS upload failed, fallback to local storage; error=%s", upload_error
            )

    if storage_provider != "oss":
        file_url, file_path = _save_file_local(
            content,
            storage_filename,
            business_segment,
            user_segment,
        )

    return {
        "storage_provider": storage_provider,
        "file_url": file_url,
        "file_path": file_path,
        "oss_bucket": oss_bucket,
        "oss_key": oss_key,
        "storage_key": storage_key,
        "business_segment": business_segment,
        "user_segment": user_segment,
        "oss_object_path": storage_key if storage_provider == "oss" else None,
    }

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

async def _schedule_ai_analysis(material_id: str, file_url: str, material_type: str, user_id: str):
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

def _save_file_local(
    content: bytes,
    storage_filename: str,
    business_segment: str,
    user_segment: str,
) -> tuple:
    """
    将文件保存到本地存储
    
    Args:
        content: 文件内容
        storage_filename: 已生成的存储文件名（需保证唯一）
        business_segment: 公司路径片段
        user_segment: 用户路径片段
    
    Returns:
        tuple: (文件访问URL, 文件存储路径)
    """
    # 创建公司 / 用户特定的存储目录
    user_storage_path = os.path.join(LOCAL_STORAGE_PATH, business_segment, user_segment)
    os.makedirs(user_storage_path, exist_ok=True)
    
    # 完整文件路径
    file_path = os.path.join(user_storage_path, storage_filename)
    
    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 生成访问URL
    file_url = (
        f"http://localhost:8080/uploads/materials/"
        f"{business_segment}/{user_segment}/{storage_filename}"
    )
    
    return file_url, file_path




############################
# 文件夹管理
############################

@router.get("/folders", response_model=List[HSAIMaterialFolderResponse], summary="获取素材文件夹")
async def get_material_folders(
    query: Optional[str] = Query(None, description="搜索关键词，用于按文件夹名称进行模糊搜索"),
    user=Depends(get_verified_user)
):
    """
    获取用户的素材清单树（模板 → 场景 → 拍摄项目）。
    可通过 query 关键词对名称/描述进行过滤。
    """
    try:
        checklist_tree = material_checklist_service.get_tree_for_user(user)
        responses = [
            _convert_checklist_node_to_response(node)
            for node in checklist_tree
        ]

        if query:
            responses = _filter_folder_responses(responses, query.lower())

        return responses

    except HTTPException:
        raise
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
        # 验证输入数据
        if not form_data.name or not form_data.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Folder name cannot be empty"
            )
        
        # 验证父目录是否存在（如果提供了的话）
        if form_data.parent_id:
            parent_folder = HSAIMaterialFolders.get_folder_by_id(form_data.parent_id)
            if not parent_folder or parent_folder.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid parent folder ID or insufficient permissions"
                )
        
        folder = HSAIMaterialFolders.insert_new_folder(user.id, form_data)
        if not folder:
            # 检查具体原因
            existing_folder_check = None
            with get_db() as db:
                existing_folder_check = db.query(HSAIMaterialFolder).filter_by(
                    name=form_data.name,
                    parent_id=form_data.parent_id,
                    user_id=user.id
                ).first()
            
            if existing_folder_check:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A folder with the same name already exists in this location"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create folder"
                )
        
        return HSAIMaterialFolderResponse(
            **folder.model_dump(),
            label=folder.name,  # 为 label 字段赋与 name 字段相同的值
            children=[],
            material_count=0
        )
        
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        log.exception(f"Error creating material folder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/folders/{folder_id}/rename", response_model=HSAIMaterialFolderResponse, summary="重命名素材文件夹")
async def rename_material_folder(
    folder_id: str,
    form_data: HSAIMaterialFolderForm,
    user=Depends(get_verified_user)
):
    """
    重命名素材文件夹。
    
    Args:
        folder_id (str): 文件夹唯一标识符
        form_data (HSAIMaterialFolderForm): 包含新文件夹名称的表单数据
        user: 已认证的用户对象
        
    Returns:
        HSAIMaterialFolderResponse: 更新后的文件夹信息
        
    Raises:
        HTTPException: 404 - 文件夹不存在或无权限访问
        HTTPException: 400 - 文件夹名称已存在
        HTTPException: 500 - 更新失败
    """
    try:
        # 首先验证文件夹所有权
        folder = HSAIMaterialFolders.get_folder_by_id(folder_id)
        if not folder or folder.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found or insufficient permissions"
            )
        
        # 验证文件夹所有权并更新名称
        updated_folder = HSAIMaterialFolders.update_folder_name_by_id(folder_id, form_data.name)
        if not updated_folder:
            # 检查具体原因
            existing_folder_check = None
            with get_db() as db:
                existing_folder_check = db.query(HSAIMaterialFolder).filter_by(
                    id=folder_id,
                    user_id=user.id
                ).first()
            
            if not existing_folder_check:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Folder not found or insufficient permissions"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A folder with the same name already exists in this location"
                )
        
        return HSAIMaterialFolderResponse(
            **updated_folder.model_dump(),
            label=updated_folder.name,  # 为 label 字段赋与 name 字段相同的值
            children=[],
            material_count=0
        )
        
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        log.exception(f"Error renaming material folder: {e}")
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
    删除指定的素材文件夹。
    
    Args:
        folder_id (str): 文件夹唯一标识符
        user: 已认证的用户对象
        
    Returns:
        bool: 删除成功返回true
        
    Raises:
        HTTPException: 404 - 文件夹不存在或无权限访问
        HTTPException: 400 - 文件夹不为空，无法删除
        HTTPException: 500 - 删除失败
    """
    try:
        # 验证文件夹所有权
        folder = HSAIMaterialFolders.get_folder_by_id(folder_id)
        if not folder or folder.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found or insufficient permissions"
            )
        
        # 检查文件夹是否为空（没有子文件夹和素材）
        with get_db() as db:
            # 检查子文件夹
            child_folders = db.query(HSAIMaterialFolder).filter_by(
                parent_id=folder_id,
                user_id=user.id
            ).all()
            
            if child_folders:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete folder: contains {len(child_folders)} subfolder(s). Please delete or move subfolders first."
                )
            
            # 检查文件夹中的素材
            materials = db.query(HSAIMaterial).filter_by(
                folder_id=folder_id,
                user_id=user.id,
                is_deleted=False  # 只检查未被软删除的素材
            ).all()
            
            if materials:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete folder: contains {len(materials)} material(s). Please delete or move materials first."
                )
        
        # 执行删除
        result = HSAIMaterialFolders.delete_folder_by_id(folder_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete folder"
            )
        
        log.info(f"Folder deleted successfully: {folder.name} (ID: {folder_id}) by user {user.id}")
        return True
        
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        log.exception(f"Error deleting material folder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

############################
# 素材上传 - 支持本地存储和OSS存储
############################

@router.post("/upload", response_model=List[HSAIMaterialResponse], summary="上传素材")
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
    上传素材文件，支持本地存储和OSS存储。
    
    支持多种文件格式的上传，包括图片、视频、音频、文档等。
    支持压缩包上传，系统会自动解析压缩包内的文件并按规则重命名。
    文件将存储在本地或上传到阿里云OSS存储，上传后可选择进行AI自动分析。
    
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
        - file_path: 存储路径
        - file_size: 文件大小
        - mime_type: 文件MIME类型
        - material_type: 素材类型
        - upload_url: 文件访问URL
        
    Raises:
        HTTPException: 400 - 文件格式不支持或文件过大
        HTTPException: 500 - 上传失败或服务器错误
    """
    log.info(f"Upload material request received. User ID: {user.id}")
    log.info(f"File name: {file.filename}")
    log.info(f"Form data: name={name}, folder_id={folder_id}, scene_code={scene_code}, technique_code={technique_code}, properties_code={properties_code}")

    # 清单目录映射：如 folder_id 形如 item:xxx，自动填充对应的场景/项目编码
    folder_id, checklist_node = _resolve_folder_context(user, folder_id)
    scene_code, technique_code, _, scene_display_name = _extract_codes_from_node(
        checklist_node,
        scene_code,
        technique_code,
    )

    if checklist_node and checklist_node.node_type == "template":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择具体的场景或拍摄项目后再上传素材",
        )
    
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
            log.info("Processing ZIP file")
            # 处理压缩包
            processed_files = _process_zip_file(file, user.id, scene_code, technique_code, properties_code)
            responses = []
            
            # 逐个上传处理后的文件
            for file_info in processed_files:
                log.info(f"Processing file from ZIP: {file_info['new_filename']}")

                file_hash = hashlib.md5(file_info["content"]).hexdigest()
                mime_type = mimetypes.guess_type(file_info["new_filename"])[0] or "application/octet-stream"
                material_type = _determine_material_type(mime_type)
                storage_filename = _build_storage_filename(file_info["new_filename"], file_hash)

                storage_result = _store_material_file(
                    content=file_info["content"],
                    storage_filename=storage_filename,
                    user=user,
                    material_type=material_type,
                    original_filename=file_info["original_filename"],
                )

                file_path = storage_result["file_path"]
                file_url = storage_result["file_url"]
                storage_provider = storage_result["storage_provider"]
                oss_bucket = storage_result["oss_bucket"]
                oss_key = storage_result["oss_key"]

                material_metadata = {
                    "original_filename": file_info["original_filename"],
                    "upload_time": int(time.time()),
                    "file_url": file_url,
                    "storage_provider": storage_provider,
                    "storage_key": storage_result["storage_key"],
                    "business_directory": storage_result["business_segment"],
                    "user_directory": storage_result["user_segment"],
                }

                if oss_bucket:
                    material_metadata["oss_bucket"] = oss_bucket
                if oss_key:
                    material_metadata["oss_key"] = oss_key

                duration = None
                resolution = None

                if material_type == "video":
                    try:
                        import tempfile

                        with tempfile.NamedTemporaryFile(
                            suffix=Path(file_info["new_filename"]).suffix, delete=False
                        ) as tmp_file:
                            tmp_file.write(file_info["content"])
                            tmp_file_path = Path(tmp_file.name)

                        try:
                            from open_webui.utils.hsai_file_processor import HSAIFileProcessor

                            processor = HSAIFileProcessor(str(tmp_file_path.parent))
                            metadata = processor.extract_metadata(tmp_file_path, material_type)
                            material_metadata.update(metadata)

                            if "duration" in metadata:
                                duration = int(metadata["duration"])
                            if "width" in metadata and "height" in metadata:
                                resolution = f"{metadata['width']}x{metadata['height']}"
                        finally:
                            tmp_file_path.unlink(missing_ok=True)
                    except Exception as meta_error:
                        log.warning(f"Failed to extract video metadata: {meta_error}")

                properties_list = None
                if file_info["properties_code"]:
                    if isinstance(file_info["properties_code"], str):
                        try:
                            properties_list = json.loads(file_info["properties_code"])
                            if isinstance(properties_list, str):
                                properties_list = [properties_list]
                            elif not isinstance(properties_list, list):
                                properties_list = [file_info["properties_code"]]
                        except json.JSONDecodeError:
                            properties_list = [file_info["properties_code"]]
                    elif isinstance(file_info["properties_code"], list):
                        properties_list = file_info["properties_code"]
                    else:
                        properties_list = [str(file_info["properties_code"])]

                material_data = HSAIMaterialForm(
                    name=Path(file_info["new_filename"]).stem,
                    description=description,
                    material_type=material_type,
                    folder_id=folder_id,
                    file_path=file_path,  # 存储文件路径
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
                    material_metadata=material_metadata,
                    oss_bucket=oss_bucket,
                    oss_key=oss_key,
                )
                
                log.info(f"Creating material record with data: {material_data}")
                log.info(f"Material data dict: {material_data.model_dump()}")
                
                material = HSAIMaterials.insert_new_material(user.id, material_data)
                if not material:
                    log.error("Failed to create material record in database")
                    log.error(f"Material data that failed: {material_data}")
                    log.error(f"Material data dict: {material_data.model_dump()}")
                    # 如果是OSS存储且数据库记录创建失败，尝试删除OSS文件
                    if storage_provider == "oss":
                        try:
                            Storage.delete_file(file_path)
                        except:
                            log.warning(f"Failed to cleanup OSS file after database error: {file_path}")
                    
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to create material record"
                    )
                
                log.info(f"Successfully created material record with ID: {material.id}")
                
                # 如果启用自动分析，异步执行AI分析
                if auto_analyze:
                    try:
                        await _schedule_ai_analysis(material.id, file_url, material_type, user.id)
                    except Exception as ai_error:
                        log.warning(f"Failed to schedule AI analysis: {ai_error}")
                
                # 处理可能的字节类型数据
                safe_file_url = file_url
                if isinstance(safe_file_url, bytes):
                    try:
                        safe_file_url = safe_file_url.decode('utf-8')
                    except UnicodeDecodeError:
                        import base64
                        safe_file_url = base64.b64encode(safe_file_url).decode('utf-8')
                
                # 创建响应对象时排除properties_code字段，使用处理后的值
                response = HSAIMaterialResponse(
                    **{k: v for k, v in material.model_dump().items() if k != 'properties_code'},
                    thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material_type in ["image", "video"] else None,
                    download_url=safe_file_url,  # 直接使用文件URL进行下载
                    properties_code=material.properties_code.split("_") if material.properties_code else None  # 将字符串转换为列表
                )
                
                responses.append(response)
            
            return responses
        else:
            log.info("Processing single file")
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
            mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
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
            
            # 生成存储文件名
            file_extension = Path(file.filename).suffix
            storage_filename = _build_storage_filename(
                f"{filename_base}{file_extension}", file_hash
            )

            storage_result = _store_material_file(
                content=content,
                storage_filename=storage_filename,
                user=user,
                material_type=material_type,
                original_filename=file.filename,
            )

            file_url = storage_result["file_url"]
            file_path = storage_result["file_path"]
            storage_provider = storage_result["storage_provider"]
            oss_bucket = storage_result["oss_bucket"]
            oss_key = storage_result["oss_key"]
            
            # 提取文件元数据
            material_metadata = {
                "original_filename": file.filename,
                "upload_time": int(time.time()),
                "file_url": file_url,
                "storage_provider": storage_provider,
                "storage_key": storage_result["storage_key"],
                "business_directory": storage_result["business_segment"],
                "user_directory": storage_result["user_segment"],
            }

            if oss_bucket:
                material_metadata["oss_bucket"] = oss_bucket
            if oss_key:
                material_metadata["oss_key"] = oss_key
            
            # 如果file_url是bytes类型，则进行解码
            if isinstance(material_metadata.get("file_url"), bytes):
                try:
                    material_metadata["file_url"] = material_metadata["file_url"].decode('utf-8')
                except UnicodeDecodeError:
                    # 如果UTF-8解码失败，则使用base64编码
                    import base64
                    material_metadata["file_url"] = base64.b64encode(material_metadata["file_url"]).decode('utf-8')

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
                file_path=file_path,  # 存储文件路径
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
                    material_metadata=material_metadata,
                    oss_bucket=storage_result["oss_bucket"],
                    oss_key=storage_result["oss_key"],
                )
            
            log.info(f"Creating material record with data: {material_data}")
            log.info(f"Material data dict: {material_data.model_dump()}")
            
            # 添加额外的验证
            try:
                # 验证数据是否符合模型要求
                validated_data = HSAIMaterialForm(**material_data.model_dump())
                log.info(f"Material data validated successfully: {validated_data}")
            except Exception as validation_error:
                log.error(f"Material data validation failed: {validation_error}")
                log.error(f"Material data that failed validation: {material_data}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid material data: {str(validation_error)}"
                )
            
            # 这里是关键部分 - 添加更多日志
            log.info(f"About to call HSAIMaterials.insert_new_material with user_id: {user.id}")
            log.info(f"Material data being passed: {material_data}")
            
            material = HSAIMaterials.insert_new_material(user.id, material_data)
            
            log.info(f"Result from insert_new_material: {material}")
            
            if not material:
                log.error("Failed to create material record in database")
                log.error(f"User ID: {user.id}")
                log.error(f"Material data that failed: {material_data}")
                log.error(f"Material data dict: {material_data.model_dump()}")
                # 如果是OSS存储且数据库记录创建失败，尝试删除OSS文件
                if storage_provider == "oss":
                    try:
                        Storage.delete_file(file_path)
                    except:
                        log.warning(f"Failed to cleanup OSS file after database error: {file_path}")
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create material record"
                )
            
            log.info(f"Successfully created material record with ID: {material.id}")
            
            # 如果启用自动分析，异步执行AI分析
            if auto_analyze:
                try:
                    await _schedule_ai_analysis(material.id, file_url, material_type, user.id)
                except Exception as ai_error:
                    log.warning(f"Failed to schedule AI analysis: {ai_error}")
            
            # 处理可能的字节类型数据
            safe_file_url = file_url
            if isinstance(safe_file_url, bytes):
                try:
                    safe_file_url = safe_file_url.decode('utf-8')
                except UnicodeDecodeError:
                    import base64
                    safe_file_url = base64.b64encode(safe_file_url).decode('utf-8')
            
            return [HSAIMaterialResponse(
                **{k: v for k, v in material.model_dump().items() if k != 'properties_code'},
                thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material_type in ["image", "video"] else None,
                download_url=safe_file_url,  # 直接使用文件URL进行下载
                properties_code=material.properties_code.split("_") if material.properties_code else None  # 将字符串转换为列表
            )]
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error uploading material: {e}")
        # 添加更详细的错误信息
        error_detail = f"Error uploading material: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
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
        if material.file_path and material.file_path.startswith(('http://', 'https://', 's3://', 'gs://')):
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
    query: Optional[str] = Query(None, description="搜索关键词，用于按名称、描述、标签进行模糊搜索"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取用户的素材列表（分页）。
    
    支持按文件夹、类型过滤和关键词搜索，支持分页查询。
    
    Args:
        folder_id (str, optional): 文件夹ID，为空则获取根目录素材
        material_type (str, optional): 素材类型过滤：image(图片)、video(视频)、audio(音频)、text(文本)、document(文档)
        query (str, optional): 搜索关键词，用于按名称、描述、标签进行模糊搜索
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAIMaterialResponse: 分页的素材列表
        - data: 素材列表
        - pagination: 分页信息
    """
    try:
        # 解析清单节点上下文
        folder_filter, checklist_node = _resolve_folder_context(user, folder_id)
        scene_code_filter, item_code_filter, scene_codes_filter, _ = _extract_codes_from_node(
            checklist_node,
            None,
            None,
        )

        # 计算offset
        offset = (pi - 1) * ps
        
        # 根据是否有搜索关键词决定使用哪种查询方式
        if query:
            # 使用搜索接口
            materials = HSAIMaterials.search_materials(
                user.id,
                query=query,
                material_type=material_type,
                scene_code=scene_code_filter,
                item_code=item_code_filter,
                scene_codes=scene_codes_filter,
                limit=ps,
                offset=offset,
            )
            
            # 获取搜索结果总数
            total = HSAIMaterials.count_search_materials(
                user.id,
                query=query,
                material_type=material_type,
                scene_code=scene_code_filter,
                item_code=item_code_filter,
                scene_codes=scene_codes_filter,
            )
        else:
            # 使用常规列表查询
            materials = HSAIMaterials.get_materials_by_user_id(
                user.id,
                folder_id=folder_filter,
                material_type=material_type,
                scene_code=scene_code_filter,
                item_code=item_code_filter,
                scene_codes=scene_codes_filter,
                limit=ps,
                offset=offset
            )
            
            # 获取常规列表总数
            total = HSAIMaterials.get_materials_count(
                user.id,
                folder_id=folder_filter,
                material_type=material_type,
                scene_code=scene_code_filter,
                item_code=item_code_filter,
                scene_codes=scene_codes_filter,
            )
        
        responses = []
        for material in materials:
            # 确保返回OSS URL
            download_url = material.file_path or ""
            if not download_url.startswith(('http://', 'https://')):
                download_url = f"/hsai/materials/{material.id}/download"
            
            # 处理可能的字节类型数据
            safe_download_url = download_url
            if isinstance(safe_download_url, bytes):
                try:
                    safe_download_url = safe_download_url.decode('utf-8')
                except UnicodeDecodeError:
                    import base64
                    safe_download_url = base64.b64encode(safe_download_url).decode('utf-8')
            
            # 处理属性代码，将其转换为列表格式
            properties_list = None
            if material.properties_code:
                if isinstance(material.properties_code, str):
                    properties_list = material.properties_code.split("_")
                elif isinstance(material.properties_code, list):
                    properties_list = material.properties_code
            
            response = HSAIMaterialResponse(
                **{k: v for k, v in material.model_dump().items() if k not in ['properties_code']},
                thumbnail_url=f"/hsai/materials/{material.id}/thumbnail" if material.material_type in ["image", "video"] else None,
                download_url=safe_download_url,
                properties_code=properties_list  # 返回列表格式
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
        download_url = material.file_path or ""
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
        checklist_tree = material_checklist_service.get_tree_for_user(user)
        
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
            folders_count=_count_tree_nodes(checklist_tree),
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


# 初始化全局实例
from open_webui.models.hsai_materials import (
    HSAIMaterialFolders,
    HSAIMaterials,
    HSAIMaterialCategories,
    HSAIFileOperationLogs
)
