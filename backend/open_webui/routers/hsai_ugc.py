import logging
import os
import re
import uuid
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field

from open_webui.utils.auth import get_verified_user
from open_webui.storage.provider import Storage
from open_webui.models.hsai_ugc import (
    MaterialModels,
    VideoTasks,
    TaskScenes,
    MaterialModelCreateForm,
    VideoTaskCreateForm,
    TaskSceneUpdateForm,
    MaterialModelData,
    VideoTaskData,
    TaskSceneData
)
from open_webui.services.workflow_meta_update_service import post_json
from open_webui.constants import ERROR_MESSAGES
from open_webui.integrations.ffmpeg_oss import ensure_download_url, upload_via_ffmpeg, USE_FFMPEG_OSS

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ugc", tags=["UGC Video Generation"])

# n8n Webhook URLs
N8N_UGC_BASE_URL = os.getenv("N8N_UGC_BASE_URL", "https://webhook-n8n.hsai.cc/webhook")
URL_HS001 = f"{N8N_UGC_BASE_URL}/ugc_voice_id"  # Clone Voice
URL_HS002 = f"{N8N_UGC_BASE_URL}/ugc_product"  # Generate Script
URL_HS003 = f"{N8N_UGC_BASE_URL}/ugc_video"  # Generate Video
URL_HS004 = f"{N8N_UGC_BASE_URL}/ugc_result"  # Merge Video


def _require_user_id(user) -> str:
    """
    UGC 使用 OpenWebUI 的 user.id 作为 user_id（字符串），不要求纯数字。
    """
    return str(user.id)


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Missing required env var: {name}",
        )
    return value


def _ugc_asset_url(file_path: str) -> str:
    """
    生成可供 n8n 访问的资源 URL。

    - 若 Storage 支持签名链接：优先使用 presigned URL（默认 2 小时）。
    - 否则若 file_path 已是 http(s)：直接使用。
    - 否则报错（例如 local 存储下仅有本地路径）。
    """
    expires = int(os.getenv("UGC_ASSET_URL_EXPIRES_SECONDS", "7200"))
    try:
        url = Storage.generate_download_url(file_path, expires=expires)
        if url:
            return url
    except Exception:
        pass

    if isinstance(file_path, str) and file_path.startswith(("http://", "https://")):
        return file_path

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="无法为 UGC 资产生成可访问 URL，请启用支持外部访问的存储（如 S3/OSS/Azure）或实现签名链接。",
    )


def _sanitize_oss_path_segment(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return "unknown"
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", normalized)


def _ugc_upload_and_get_url(
    upload: UploadFile,
    storage_filename: str,
    *,
    user_id: str,
    kind: str,
) -> str:
    """
    上传 UGC 资产并返回 n8n 可访问的 URL。
    - 优先走 StorageProvider（如 s3/gcs/azure 可生成 presigned URL）。
    - 若 StorageProvider 无法生成可访问 URL 且启用了 FFmpeg OSS，则回退到 `/oss/upload` 上传并使用返回 URL（必要时再签名）。
    """
    contents, file_path = Storage.upload_file(
        upload.file,
        storage_filename,
        {"OpenWebUI-User-Id": str(user_id)},
    )
    try:
        return _ugc_asset_url(file_path)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR:
            raise

        if not USE_FFMPEG_OSS:
            raise

        prefix = os.getenv("UGC_ASSET_OSS_PATH_PREFIX", "ugc/assets").strip()
        prefix = prefix.replace("\\", "/").strip("/")
        if not prefix or ".." in prefix:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid UGC_ASSET_OSS_PATH_PREFIX",
            )

        safe_user_id = _sanitize_oss_path_segment(user_id)
        safe_kind = _sanitize_oss_path_segment(kind)
        target_path = f"{prefix}/{safe_user_id}/{safe_kind}".strip("/")

        original_name = os.path.basename(upload.filename or storage_filename or "upload.bin")
        resp = upload_via_ffmpeg(
            contents,
            target_path,
            content_type=upload.content_type,
            filename=original_name,
        )
        if not isinstance(resp, dict):
            raise
        url = resp.get("url")
        if not url:
            raise

        expires = int(os.getenv("UGC_ASSET_URL_EXPIRES_SECONDS", "7200"))
        signed = ensure_download_url(url, expires=expires, fallback_url=url)
        return signed or url

####################
# Step 0: Digital Human Asset Management
####################

@router.post("/models", response_model=MaterialModelData, summary="创建数字人资产 (Step 0)")
async def create_material_model(
    model_name: str = Form(...),
    model_img: UploadFile = File(...),
    voice_audio: UploadFile = File(...),
    user=Depends(get_verified_user),
):
    """
    创建数字人基础资产，绑定图片和音色。
    触发 n8n hs001 进行音色克隆，并将返回的 voice_id 写入 Material_Models.voice_provider_id。
    """
    try:
        user_id = _require_user_id(user)

        # 1) 上传资源到存储
        img_filename = f"ugc_model_img_{uuid.uuid4()}_{os.path.basename(model_img.filename or 'model.jpg')}"
        model_img_url = _ugc_upload_and_get_url(
            model_img,
            img_filename,
            user_id=user_id,
            kind="model-image",
        )

        audio_filename = f"ugc_voice_audio_{uuid.uuid4()}_{os.path.basename(voice_audio.filename or 'voice.wav')}"
        voice_preview_url = _ugc_upload_and_get_url(
            voice_audio,
            audio_filename,
            user_id=user_id,
            kind="voice-audio",
        )

        # 2) 调用 n8n hs001 获取 voice_id
        # 设计文档未固定 hs001 入参字段，这里按现有 n8n 文档的最小集合传递并注入 minimax_key。
        minimax_key = _require_env("MINIMAX_KEY")
        payload = {
            "ip_id": f"tmp_{uuid.uuid4()}",
            "ip_name": model_name,
            "ip_img": model_img_url,
            "voice_url": voice_preview_url,
            "minimax_key": minimax_key,
            "minimax-key": minimax_key,
        }
        status_code, data, raw_text = await post_json(URL_HS001, payload)
        if status_code >= 400:
            raise HTTPException(status_code=502, detail=f"n8n hs001 failed: {status_code}")

        voice_id = None
        if isinstance(data, dict):
            voice_id = data.get("voice_id") or data.get("voice_provider_id")
        if not voice_id and raw_text:
            # 容错：部分工作流可能返回纯文本
            voice_id = raw_text.strip()
        if not voice_id:
            raise HTTPException(status_code=502, detail="n8n hs001 did not return voice_id")

        # 3) 入库
        model = MaterialModels.insert_new_model(
            user_id,
            MaterialModelCreateForm(
                model_name=model_name,
                model_img_url=model_img_url,
                voice_provider_id=str(voice_id),
                voice_preview_url=voice_preview_url,
            ),
        )
        return model
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to create material model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models", response_model=List[MaterialModelData], summary="获取数字人资产列表")
async def get_material_models(user=Depends(get_verified_user)):
    user_id = _require_user_id(user)
    return MaterialModels.get_models_by_user_id(user_id)

####################
# Step 1: Video Task Creation & Script Generation
####################

@router.post("/tasks", response_model=VideoTaskData, summary="创建视频生成任务 (Step 1)")
async def create_video_task(form: VideoTaskCreateForm, user=Depends(get_verified_user)):
    """
    创建视频生成任务，并触发 n8n hs002 生成脚本。
    """
    try:
        user_id = _require_user_id(user)
        model = MaterialModels.get_model_by_id_and_user_id(form.model_id, user_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        task = VideoTasks.create_task(user_id, form)
        
        # 触发 n8n 生成脚本（严格按设计文档 V3.2 payload）
        payload = {
            "task_id": task.id,
            "ip_id": f"model_{model.id}",
            "ip_name": model.model_name,
            "ip_img": model.model_img_url,
            "voice_id": model.voice_provider_id,
            "product_url": form.product_url,
            "product_name": form.product_name,
            "product_country": form.product_country or "",
            "language": form.language,
            "subtitle": form.subtitle or "",
            "shot_script": form.shot_script or "",
            "jarvis_api_key": _require_env("JARVIS_API_KEY"),
            "minimax_key": _require_env("MINIMAX_KEY"),
            "minimax_group": _require_env("MINIMAX_GROUP"),
            "runninghub_api_key": _require_env("RUNNINGHUB_API_KEY"),
            "runninghub_workflow_id": _require_env("RUNNINGHUB_WORKFLOW_ID"),
        }
        status_code, _, _ = await post_json(URL_HS002, payload)
        
        if status_code >= 400:
            VideoTasks.update_task_status(task.id, status=-1)
            raise HTTPException(status_code=502, detail=f"n8n script generation trigger failed: {status_code}")
            
        return task
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to create video task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks", response_model=List[VideoTaskData], summary="获取任务列表")
async def get_video_tasks(user=Depends(get_verified_user)):
    user_id = _require_user_id(user)
    return VideoTasks.get_tasks_by_user_id(user_id)

@router.get("/tasks/{task_id}", response_model=VideoTaskData, summary="获取任务详情")
async def get_task_details(task_id: str, user=Depends(get_verified_user)):
    task = VideoTasks.get_task_by_id(task_id)
    user_id = _require_user_id(user)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/tasks/{task_id}/scenes", response_model=List[TaskSceneData], summary="获取任务分镜列表")
async def get_task_scenes(task_id: str, user=Depends(get_verified_user)):
    # 简单校验权限
    task = VideoTasks.get_task_by_id(task_id)
    user_id = _require_user_id(user)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskScenes.get_scenes_by_task_id(task_id)

####################
# Step 2: Update Script & Generate Scene Videos
####################

class TaskSceneEditItem(BaseModel):
    scene_index: int = Field(..., ge=0)
    subtitle: Optional[str] = None
    script_desc: Optional[str] = None
    reference_img_url: Optional[str] = None

@router.post("/tasks/{task_id}/generate_video", summary="提交编辑并生成分镜视频 (Step 2)")
async def generate_scene_videos(task_id: str, scenes: List[TaskSceneEditItem], user=Depends(get_verified_user)):
    """
    用户完成脚本编辑后，提交此接口。
    1. 更新本地分镜脚本。
    2. 触发 n8n hs003 生成所有分镜视频。
    """
    try:
        task = VideoTasks.get_task_by_id(task_id)
        user_id = _require_user_id(user)
        if not task or task.user_id != user_id:
            raise HTTPException(status_code=404, detail="Task not found")

        # 1) 更新数据库（逐条更新，避免覆盖 fragment_video_url）
        existing = TaskScenes.get_scenes_by_task_id(task_id)
        existing_map = {s.scene_index: s for s in existing}
        for item in scenes:
            if item.scene_index not in existing_map:
                raise HTTPException(status_code=400, detail=f"Invalid scene_index: {item.scene_index}")
            TaskScenes.update_scene(
                existing_map[item.scene_index].id,
                TaskSceneUpdateForm(
                    subtitle=item.subtitle,
                    script_desc=item.script_desc,
                    reference_img_url=item.reference_img_url,
                ),
            )
        
        # 2) 读取最新分镜并组装 hs003 payload（按设计文档）
        updated_scenes = TaskScenes.get_scenes_by_task_id(task_id)
        updated_scenes.sort(key=lambda s: s.scene_index)
        subtitle_list = [s.subtitle or "" for s in updated_scenes]
        shot_script_img_list = [s.reference_img_url or "" for s in updated_scenes]
        shot_script_list = [s.script_desc or "" for s in updated_scenes]

        # 3) 切换状态为 3 (视频生成中)
        VideoTasks.update_task_status(task_id, status=3, step=2)

        # 4) 触发 n8n 生成视频
        payload = {
            "task_id": task_id,
            "subtitle_list": subtitle_list,
            "shot_script_img_list": shot_script_img_list,
            "shot_script_list": shot_script_list,
            "jarvis_api_key": _require_env("JARVIS_API_KEY"),
            "minimax_key": _require_env("MINIMAX_KEY"),
            "minimax_group": _require_env("MINIMAX_GROUP"),
            "runninghub_api_key": _require_env("RUNNINGHUB_API_KEY"),
            "runninghub_workflow_id": _require_env("RUNNINGHUB_WORKFLOW_ID"),
        }
        status_code, _, _ = await post_json(URL_HS003, payload)
        
        if status_code >= 400:
             VideoTasks.update_task_status(task_id, status=-1)
             raise HTTPException(status_code=502, detail=f"n8n video generation trigger failed: {status_code}")

        return {"success": True, "message": "Video generation started"}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to trigger video generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

####################
# Step 3: Final Merge
####################

@router.post("/tasks/{task_id}/merge", summary="合成最终视频 (Step 3)")
async def merge_video(task_id: str, user=Depends(get_verified_user)):
    """
    分镜视频生成完毕后，用户点击合成。
    触发 n8n hs004 完成视频拼接。
    """
    try:
        task = VideoTasks.get_task_by_id(task_id)
        user_id = _require_user_id(user)
        if not task or task.user_id != user_id:
            raise HTTPException(status_code=404, detail="Task not found")

        # 1) 获取分镜视频列表（必须全部就绪）
        scenes = TaskScenes.get_scenes_by_task_id(task_id)
        scenes.sort(key=lambda s: s.scene_index)
        video_urls = [s.fragment_video_url for s in scenes]
        if not video_urls or any(not u for u in video_urls):
            raise HTTPException(status_code=400, detail="Not all scene videos are ready")

        # 2) 切换状态为 5 (合成中)
        VideoTasks.update_task_status(task_id, status=5, step=3)

        # 3) 触发 n8n 合成（按设计文档：shot_video_list）
        payload = {
            "task_id": task_id,
            "shot_video_list": video_urls,
            "jarvis_api_key": _require_env("JARVIS_API_KEY"),
        }
        status_code, _, _ = await post_json(URL_HS004, payload)

        if status_code >= 400:
             VideoTasks.update_task_status(task_id, status=-1)
             raise HTTPException(status_code=502, detail=f"n8n merge trigger failed: {status_code}")

        return {"success": True, "message": "Merge process started"}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to trigger merge: {e}")
        raise HTTPException(status_code=500, detail=str(e))
