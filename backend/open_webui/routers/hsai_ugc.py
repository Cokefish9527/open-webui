import logging
import os
import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
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
    TaskSceneData,
    UGCLibraryTasksResponse,
    UGCTaskCloseForm,
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


class UGCTaskStatusData(BaseModel):
    """
    轮询用：只返回任务状态相关字段，避免前端每次轮询拿到过多数据。
    """
    task_id: str
    status: int
    step: int
    result_video_url: Optional[str] = None
    updated_at: Optional[int] = None
    progress_percent: Optional[int] = None
    progress_stage: Optional[str] = None
    progress_message: Optional[str] = None
    closed_at: Optional[int] = None
    closed_reason: Optional[str] = None


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
    触发 n8n hs001 进行音色克隆，并将返回的 voice_id 写入 hsai_ugc_material_models.voice_provider_id。
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


@router.get("/models/{model_id}", response_model=MaterialModelData, summary="获取数字人资产详情")
async def get_material_model_detail(model_id: int, user=Depends(get_verified_user)):
    """
    兼容前端：按 id 获取单个数字人资产。
    权限边界：仅允许资产 owner 访问；否则返回 404（不泄漏存在性）。
    """
    user_id = _require_user_id(user)
    model = MaterialModels.get_model_by_id_and_user_id(model_id, user_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model

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
        
        # 触发 n8n 生成脚本（与当前联调 payload 约定保持一致；ffmpeg_api_key 已作废，不再注入）
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


@router.get("/tasks/{task_id}", response_model=VideoTaskData, summary="获取任务详情")
async def get_task_detail(task_id: str, user=Depends(get_verified_user)):
    """
    兼容前端：`GET /api/v1/ugc/tasks/{task_id}`（返回完整任务信息）。
    注意：与 /status、/scenes 一致，只有任务 owner 可访问；否则返回 404（不泄漏存在性）。
    """
    task = VideoTasks.get_task_by_id(task_id)
    user_id = _require_user_id(user)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get(
    "/library/tasks",
    response_model=UGCLibraryTasksResponse,
    summary="视频库：获取任务列表（支持筛选/排序/分页）",
)
async def get_library_tasks(
    q: Optional[str] = None,
    status: Optional[List[int]] = Query(default=None),
    model_id: Optional[int] = None,
    created_from: Optional[int] = None,
    created_to: Optional[int] = None,
    order_by: str = "updated_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_verified_user),
):
    user_id = _require_user_id(user)

    created_from_dt = datetime.utcfromtimestamp(created_from) if created_from else None
    created_to_dt = datetime.utcfromtimestamp(created_to) if created_to else None

    timeout_minutes = int(
        os.getenv("UGC_TASK_STALE_TIMEOUT_MINUTES", os.getenv("UGC_WATCHDOG_TIMEOUT_MINUTES", "60"))
    )

    return VideoTasks.get_library_tasks(
        user_id,
        q=q,
        status=status,
        model_id=model_id,
        created_from=created_from_dt,
        created_to=created_to_dt,
        order_by=order_by,
        order=order,
        page=page,
        page_size=page_size,
        stale_timeout_minutes=timeout_minutes,
    )

@router.post("/tasks/{task_id}/close", summary="关闭任务（手动）")
async def close_task(task_id: str, form: UGCTaskCloseForm, user=Depends(get_verified_user)):
    task = VideoTasks.get_task_by_id(task_id)
    user_id = _require_user_id(user)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    if int(task.status or 0) == -2:
        return {"success": True, "task_id": task_id, "status": -2}

    reason = (form.reason or "user_abort").strip()
    message = (form.message or "").strip()
    closed_reason = f"{reason}:{message}" if message else reason

    ok = VideoTasks.close_task(task_id, closed_reason=closed_reason)
    if not ok:
        raise HTTPException(status_code=409, detail="Task is already closed")
    return {"success": True, "task_id": task_id, "status": -2}

@router.get("/tasks/{task_id}/status", response_model=UGCTaskStatusData, summary="轮询任务状态（推荐）")
async def get_task_status(task_id: str, user=Depends(get_verified_user)):
    """
    轮询接口：用于前端高频查询任务状态。
    """
    task = VideoTasks.get_task_by_id(task_id)
    user_id = _require_user_id(user)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return UGCTaskStatusData(
        task_id=task.id,
        status=task.status,
        step=task.step,
        result_video_url=task.result_video_url,
        updated_at=getattr(task, "updated_at", None),
        progress_percent=getattr(task, "progress_percent", None),
        progress_stage=VideoTasks._status_to_stage(int(task.status or 0)),
        progress_message=VideoTasks._status_to_message(int(task.status or 0)),
        closed_at=getattr(task, "closed_at", None),
        closed_reason=getattr(task, "closed_reason", None),
    )

@router.get("/tasks/{task_id}/scenes", response_model=List[TaskSceneData], summary="获取任务分镜列表")
async def get_task_scenes(task_id: str, user=Depends(get_verified_user)):
    # 简单校验权限
    task = VideoTasks.get_task_by_id(task_id)
    user_id = _require_user_id(user)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskScenes.get_scenes_by_task_id(task_id)

####################
# Step 2/3: Confirm Script & Process To Final
####################

class TaskSceneEditItem(BaseModel):
    scene_index: int = Field(..., ge=0)
    subtitle: Optional[str] = None
    script_desc: Optional[str] = None
    reference_img_url: Optional[str] = None

@router.post("/tasks/{task_id}/process", summary="自动推进：生成分镜视频/合成最终视频（按任务状态判断）")
async def process_task_to_final(
    task_id: str,
    scenes: Optional[List[TaskSceneEditItem]] = None,
    user=Depends(get_verified_user),
):
    """
    合并 Step2 + Step3：前端只需调用一个接口，后续通过轮询/视频库等待最终成片。

    - status=2（待编辑）：可携带 scenes 更新分镜并触发 hs003；
    - status=4（待合成）：触发 hs004；
    - status∈{0,1,3,5}（进行中）：幂等返回，让前端继续轮询；
    - status=6：直接返回 result_video_url；
    - status=-2：返回 409（已关闭）。

    注：默认不自动触发合成；当任务进入 status=4（待合成）后，前端应展示分镜视频让用户确认，再调用本接口触发 hs004。
    """
    task = VideoTasks.get_task_by_id(task_id)
    user_id = _require_user_id(user)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    if int(task.status or 0) == -2:
        raise HTTPException(status_code=409, detail="Task is closed")

    current_status = int(task.status or 0)

    if current_status == 2:
        scenes = scenes or []
        if not scenes:
            raise HTTPException(status_code=400, detail="Missing scenes for pending-edit task")

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

        updated_scenes = TaskScenes.get_scenes_by_task_id(task_id)
        updated_scenes.sort(key=lambda s: s.scene_index)
        subtitle_list = [s.subtitle or "" for s in updated_scenes]
        shot_script_img_list = [s.reference_img_url or "" for s in updated_scenes]
        shot_script_list = [s.script_desc or "" for s in updated_scenes]

        VideoTasks.update_task_status(task_id, status=3, step=2)

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

        return {"success": True, "task_id": task_id, "status": 3, "message": "Scene video generation started"}

    if current_status == 4:
        scenes_rows = TaskScenes.get_scenes_by_task_id(task_id)
        scenes_rows.sort(key=lambda s: s.scene_index)
        video_urls = [s.fragment_video_url for s in scenes_rows]
        if not video_urls or any(not u for u in video_urls):
            raise HTTPException(status_code=400, detail="Not all scene videos are ready")

        VideoTasks.update_task_status(task_id, status=5, step=3)
        payload = {
            "task_id": task_id,
            "shot_video_list": video_urls,
            "jarvis_api_key": _require_env("JARVIS_API_KEY"),
        }
        status_code, _, _ = await post_json(URL_HS004, payload)
        if status_code >= 400:
            VideoTasks.update_task_status(task_id, status=-1)
            raise HTTPException(status_code=502, detail=f"n8n merge trigger failed: {status_code}")

        return {"success": True, "task_id": task_id, "status": 5, "message": "Merge process started"}

    if current_status == 6:
        return {
            "success": True,
            "task_id": task_id,
            "status": 6,
            "result_video_url": getattr(task, "result_video_url", None),
            "message": "Task already completed",
        }

    if current_status in (0, 1, 3, 5):
        return {"success": True, "task_id": task_id, "status": current_status, "message": "Task is in progress"}

    return {"success": False, "task_id": task_id, "status": current_status, "message": "Task is not actionable"}

####################
# Step 3: Final Merge
####################
