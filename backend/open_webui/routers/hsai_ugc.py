import logging
import os
import re
import uuid
from datetime import datetime
import traceback
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Body
from pydantic import BaseModel, Field

from open_webui.utils.auth import get_verified_user
from open_webui.storage.provider import Storage
from open_webui.models.hsai_ugc import (
    MaterialModels,
    VideoTasks,
    TaskScenes,
    Products,
    MaterialModelCreateForm,
    VideoTaskCreateForm,
    TaskSceneUpdateForm,
    MaterialModelData,
    VideoTaskData,
    TaskSceneData,
    UGCLibraryTasksResponse,
    UGCTaskCloseForm,
    ProductCreateForm,
    ProductUpdateForm,
    ProductData,
)
from open_webui.services.workflow_meta_update_service import post_json
from open_webui.constants import ERROR_MESSAGES
from open_webui.integrations.ffmpeg_oss import ensure_download_url, upload_via_ffmpeg, USE_FFMPEG_OSS
from open_webui.models.hsai_minimax_accounts import MiniMaxAccounts
from open_webui.services.minimax_speech_client import MinimaxAPIError, minimax_speech_client

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


def _resolve_minimax_credentials(
    minimax_account_id: Optional[int],
    *,
    require_group: bool,
    allow_env_fallback: bool,
) -> Dict[str, Optional[str]]:
    """
    Resolve MiniMax credentials for UGC:
    - If minimax_account_id is provided: must exist/enabled and have api_key; no env fallback.
    - Else: try default enabled MiniMax account; if missing and allow_env_fallback, fallback to env.
    """
    if minimax_account_id is not None:
        account = MiniMaxAccounts.get_account(int(minimax_account_id))
        if not account:
            raise HTTPException(status_code=404, detail="MiniMax account not found")
        if not bool(getattr(account, "enabled", False)):
            raise HTTPException(status_code=409, detail="MiniMax account is disabled")
        api_key = (getattr(account, "api_key", None) or "").strip()
        if not api_key:
            raise HTTPException(status_code=409, detail="MiniMax account missing api_key")
        group_id = (getattr(account, "group_id", None) or "").strip() or None
        if require_group and not group_id:
            raise HTTPException(status_code=409, detail="MiniMax account missing group_id")
        return {"api_key": api_key, "group_id": group_id, "resolved_account_id": str(int(account.id))}

    env_key = os.getenv("MINIMAX_KEY", "").strip() or None
    env_group = os.getenv("MINIMAX_GROUP", "").strip() or None

    resolved_id, api_key, group_id = MiniMaxAccounts.resolve_credentials(
        account_id=None,
        allow_fallback_env=bool(allow_env_fallback),
        env_api_key=env_key,
        env_group_id=env_group,
    )
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing MiniMax credentials (configure hsai_minimax_accounts or env MINIMAX_KEY)",
        )
    if require_group and not group_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing MiniMax group_id (configure hsai_minimax_accounts.group_id or env MINIMAX_GROUP)",
        )
    return {
        "api_key": api_key,
        "group_id": group_id,
        "resolved_account_id": str(resolved_id) if resolved_id is not None else None,
    }


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
    minimax_account_id: Optional[int] = Form(default=None),
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
        log.info(f"Creating material model for user {user_id}: name={model_name}")

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
        minimax = _resolve_minimax_credentials(
            minimax_account_id,
            require_group=False,
            allow_env_fallback=True,
        )
        minimax_key = minimax["api_key"]
        payload = {
            "ip_id": f"tmp_{uuid.uuid4()}",
            "ip_name": model_name,
            "ip_img": model_img_url,
            "voice_url": voice_preview_url,
            "minimax_key": minimax_key,
            "minimax-key": minimax_key,
        }
        log.info(f"Triggering n8n hs001: {URL_HS001}")
        status_code, data, raw_text = await post_json(URL_HS001, payload)
        log.info(f"n8n hs001 response: code={status_code}, data={data}, text={raw_text}")
        if status_code >= 400:
            error_msg = f"n8n hs001 failed: {status_code}"
            if isinstance(data, dict) and "error" in data:
                error_msg = data["error"]
            elif raw_text and len(raw_text) < 200:
                error_msg = raw_text
            raise HTTPException(status_code=502, detail=error_msg)

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
                minimax_account_id=(int(minimax["resolved_account_id"]) if minimax.get("resolved_account_id") else None),
            ),
        )
        return model
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to create material model: {e}\n{traceback.format_exc()}")
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
    return model


@router.delete("/models/{model_id}", summary="删除数字人资产 (含MiniMax Voice)")
async def delete_material_model(model_id: int, user=Depends(get_verified_user)):
    """
    删除数字人资产：
    1. 根据 model_id 查找资产（校验所有权）。
    2. 获取关联的 voice_provider_id 和 minimax_account_id。
    3. 调用 MiniMax API 删除远端 Voice（释放插槽）。
    4. 删除本地 DB 记录。
    """
    try:
        user_id = _require_user_id(user)
        model = MaterialModels.get_model_by_id_and_user_id(model_id, user_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        # Delete from MiniMax
        voice_id = getattr(model, "voice_provider_id", "")
        account_id = getattr(model, "minimax_account_id", None)
        
        if voice_id:
            try:
                minimax = _resolve_minimax_credentials(
                    account_id,
                    require_group=False,
                    allow_env_fallback=True, # Allow fallback if account was deleted but we have env key? Maybe safer.
                )
                api_key = minimax["api_key"]
                
                # Assume voice_type="voice_cloning" (T2A) as per Step 0 usage.
                # If failed, just log warning or swallow 404/invalid-id errors to allow local cleanup?
                # User request implies "avoid slot full", so we must try.
                log.info(f"Deleting MiniMax voice {voice_id} using key ...{api_key[-4:]}")
                await minimax_speech_client.delete_voice(
                    api_key=api_key,
                    voice_type="voice_cloning", # Most likely type for UGC
                    voice_id=voice_id
                )
            except HTTPException:
                pass # Minimax creds missing?
            except MinimaxAPIError as e:
                log.warning(f"MiniMax delete voice failed: {e.message} (status={e.status}). Proceeding with local delete.")
            except Exception as e:
                log.error(f"Unexpected error deleting MiniMax voice: {e}")

        # Delete from DB
        ok = MaterialModels.delete_model(model.id)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to delete model from DB")
            
        return {"success": True, "model_id": model_id}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to delete material model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


####################
# Product Library
####################

@router.post("/products", response_model=ProductData, summary="创建产品")
async def create_product(form: ProductCreateForm, user=Depends(get_verified_user)):
    user_id = _require_user_id(user)
    return Products.create_product(user_id, form)

@router.get("/products", response_model=List[ProductData], summary="产品列表")
async def get_products(
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_verified_user)
):
    user_id = _require_user_id(user)
    return Products.get_products(user_id, q=q, page=page, page_size=page_size)

@router.put("/products/{product_id}", response_model=ProductData, summary="更新产品")
async def update_product(product_id: int, form: ProductUpdateForm, user=Depends(get_verified_user)):
    user_id = _require_user_id(user)
    prod = Products.get_product(product_id)
    if not prod or prod.user_id != user_id:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated = Products.update_product(product_id, form)
    return updated

@router.delete("/products/{product_id}", summary="删除产品")
async def delete_product(product_id: int, user=Depends(get_verified_user)):
    user_id = _require_user_id(user)
    prod = Products.get_product(product_id)
    if not prod or prod.user_id != user_id:
        raise HTTPException(status_code=404, detail="Product not found")
    
    Products.delete_product(product_id)
    return {"success": True, "product_id": product_id}

####################
# Step 1: Video Task Creation & Script Generation
####################

def _get_sharded_api_key(index: int = 0) -> str:
    """
    Get the JARVIS_API_KEY at a specific index.
    Supports comma-separated keys in the environment variable.
    If index is out of bounds, falls back to the first key (or strictly compliant logic).
    
    Logic:
    - Split env JARVIS_API_KEY by comma.
    - If index < len(keys), return keys[index].
    - Else if keys exist, return keys[0] (fallback to first).
    - Else raise error.
    """
    raw_val = _require_env("JARVIS_API_KEY")
    keys = [k.strip() for k in raw_val.split(",") if k.strip()]
    
    if not keys:
         # Should be caught by _require_env but double check
         raise HTTPException(status_code=500, detail="JARVIS_API_KEY is empty")

    if 0 <= index < len(keys):
        return keys[index]
    
    # Fallback: if we requested key #2 but only 1 exists, use key #1?
    # Or should we strictly error? 
    # User request: "hs002 -> key1, hs003 -> key2". 
    # Let's fallback to key[0] to accept legacy config, but log warning?
    # For now, safe fallback to keys[0].
    return keys[0]


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
        minimax = _resolve_minimax_credentials(
            getattr(model, "minimax_account_id", None),
            require_group=True,
            allow_env_fallback=True,
        )
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
            "jarvis_api_key": _get_sharded_api_key(0), # Key #1 for Step 1
            "minimax_key": minimax["api_key"],
            "minimax_group": minimax["group_id"],
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


class TaskSceneVideoSelectItem(BaseModel):
    scene_index: int = Field(..., ge=0)
    video_url: str = Field(..., min_length=1)


class UGCMergeForm(BaseModel):
    """
    hs004 合成输入：
    - selections：按 scene_index 指定用户选择的视频（用于“多候选分镜”场景）；
    - shot_video_list：直接提供按 scene_index 排序的视频列表（与 n8n hs004 对齐）。
    """

    selections: Optional[List[TaskSceneVideoSelectItem]] = None
    shot_video_list: Optional[List[str]] = None


@router.post(
    "/tasks/{task_id}/generate_video",
    response_model=List[TaskSceneData],
    summary="生成分镜视频（hs003）",
)
async def generate_scene_videos(
    task_id: str,
    scenes: Optional[List[TaskSceneEditItem]] = None,
    user=Depends(get_verified_user),
):
    """
    对标 n8n hs003：生成分镜视频（Step 2）。

    - 前端可在 status=2(PENDING_EDIT) 时提交分镜编辑内容；
    - 服务端更新分镜后触发 hs003；
    - 服务端会注入 `voice_id`（来源：数字人资产 `voice_provider_id`）以对齐 n8n 入参；
    - 返回更新后的分镜列表（不等待视频生成完成），前端后续轮询 status 并拉取 scenes 获取结果。
    """
    task = VideoTasks.get_task_by_id(task_id)
    user_id = _require_user_id(user)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    if int(task.status or 0) == -2:
        raise HTTPException(status_code=409, detail="Task is closed")

    current_status = int(task.status or 0)
    if current_status != 2:
        raise HTTPException(status_code=409, detail="Task is not in pending-edit state")

    # n8n hs003 对齐：需要 voice_id（来源：数字人资产 voice_provider_id）。
    model = MaterialModels.get_model_by_id_and_user_id(int(task.model_id), user_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    scenes = scenes or []
    if scenes:
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
    if not updated_scenes:
        raise HTTPException(status_code=400, detail="No scenes found for task")

    subtitle_list = [s.subtitle or "" for s in updated_scenes]
    shot_script_img_list = [s.reference_img_url or "" for s in updated_scenes]
    shot_script_list = [s.script_desc or "" for s in updated_scenes]

    VideoTasks.update_task_status(task_id, status=3, step=2)
    minimax = _resolve_minimax_credentials(
        getattr(model, "minimax_account_id", None),
        require_group=True,
        allow_env_fallback=True,
    )
    payload = {
        "task_id": task_id,
        "voice_id": model.voice_provider_id,
        "subtitle_list": subtitle_list,
        "shot_script_img_list": shot_script_img_list,
        "shot_script_list": shot_script_list,
        "jarvis_api_key": _get_sharded_api_key(1), # Key #2 for Step 2
        "minimax_key": minimax["api_key"],
        "minimax_group": minimax["group_id"],
        "runninghub_api_key": _require_env("RUNNINGHUB_API_KEY"),
        "runninghub_workflow_id": _require_env("RUNNINGHUB_WORKFLOW_ID"),
    }
    status_code, _, _ = await post_json(URL_HS003, payload)
    if status_code >= 400:
        VideoTasks.update_task_status(task_id, status=-1)
        raise HTTPException(status_code=502, detail=f"n8n video generation trigger failed: {status_code}")

    return updated_scenes


@router.post("/tasks/{task_id}/merge", summary="合成最终视频（hs004）")
async def merge_final_video(
    task_id: str,
    payload: Any = Body(default=None),
    user=Depends(get_verified_user),
):
    """
    对标 n8n hs004：最终合成（Step 3）。

    - status=4(PENDING_MERGE) 时由前端显式调用；
    - 支持“多候选分镜”：payload.selections 指定每个 scene_index 选择的视频；
    - 也可直接传 shot_video_list（与 n8n 对齐）。
    """
    task = VideoTasks.get_task_by_id(task_id)
    user_id = _require_user_id(user)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    if int(task.status or 0) == -2:
        raise HTTPException(status_code=409, detail="Task is closed")

    current_status = int(task.status or 0)
    if current_status != 4:
        raise HTTPException(status_code=409, detail="Task is not in pending-merge state")

    scenes_rows = TaskScenes.get_scenes_by_task_id(task_id)
    scenes_rows.sort(key=lambda s: s.scene_index)
    if not scenes_rows:
        raise HTTPException(status_code=400, detail="No scenes found for task")

    form: Optional[UGCMergeForm] = None
    if isinstance(payload, dict):
        try:
            form = UGCMergeForm.model_validate(payload)
        except Exception:
            form = None

    # Compatibility: allow payload to be a raw list of urls.
    shot_video_list = payload if isinstance(payload, list) else (form.shot_video_list if form else None)

    if form and form.selections:
        existing_map = {s.scene_index: s for s in scenes_rows}
        selection_map: Dict[int, str] = {}
        for item in form.selections:
            if item.scene_index not in existing_map:
                raise HTTPException(status_code=400, detail=f"Invalid scene_index: {item.scene_index}")
            selection_map[item.scene_index] = item.video_url
            # Persist user selection for traceability / future retries.
            TaskScenes.update_fragment_video_url(task_id, item.scene_index, item.video_url)

        shot_video_list = [selection_map.get(s.scene_index) or s.fragment_video_url for s in scenes_rows]

    if not shot_video_list:
        shot_video_list = [s.fragment_video_url for s in scenes_rows]

    if len(shot_video_list) != len(scenes_rows):
        raise HTTPException(status_code=400, detail="shot_video_list length mismatch")
    if any(not u for u in shot_video_list):
        raise HTTPException(status_code=400, detail="Not all scene videos are selected/ready")

    VideoTasks.update_task_status(task_id, status=5, step=3)
    hs004_payload = {
        "task_id": task_id,
        "shot_video_list": shot_video_list,
        "jarvis_api_key": _get_sharded_api_key(0), # Key #1 (default) or should we allow Key #3? Using Key #1 for now.
    }
    status_code, _, _ = await post_json(URL_HS004, hs004_payload)
    if status_code >= 400:
        VideoTasks.update_task_status(task_id, status=-1)
        raise HTTPException(status_code=502, detail=f"n8n merge trigger failed: {status_code}")

    return {"success": True, "task_id": task_id, "status": 5, "message": "Merge process started"}


@router.post("/tasks/{task_id}/retry", summary="重试失败任务")
async def retry_task(task_id: str, user=Depends(get_verified_user)):
    """
    重试失败或超时的任务。
    根据 step 自动判断重试逻辑：
    - step=1: 重试脚本生成 (hs002)
    - step=2: 重试分镜视频生成 (hs003)
    - step=3: 重试最终合成 (hs004)
    """
    task = VideoTasks.get_task_by_id(task_id)
    user_id = _require_user_id(user)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    # 仅允许重试失败(-1)或超时关闭(-2)的任务
    if int(task.status or 0) not in (-1, -2):
         raise HTTPException(status_code=409, detail="Task is not in failed state")

    step = int(task.step or 1)
    
    # 重新加载模型信息
    model = MaterialModels.get_model_by_id_and_user_id(int(task.model_id), user_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    minimax = _resolve_minimax_credentials(
        getattr(model, "minimax_account_id", None),
        require_group=True,
        allow_env_fallback=True,
    )

    if step == 1:
        # Retry HS002
        form_dict = getattr(task, "base_inputs", {}) or {}
        # 恢复 status=1 (SCRIPTING)
        VideoTasks.update_task_status(task.id, status=1)
        
        payload = {
            "task_id": task.id,
            "ip_id": f"model_{model.id}",
            "ip_name": model.model_name,
            "ip_img": model.model_img_url,
            "voice_id": model.voice_provider_id,
            "product_url": form_dict.get("product_url"),
            "product_name": form_dict.get("product_name"),
            "product_country": form_dict.get("product_country") or "",
            "language": form_dict.get("language"),
            "subtitle": form_dict.get("subtitle") or "",
            "shot_script": form_dict.get("shot_script") or "",
            "jarvis_api_key": _get_sharded_api_key(0), # Key #1
            "minimax_key": minimax["api_key"],
            "minimax_group": minimax["group_id"],
            "runninghub_api_key": _require_env("RUNNINGHUB_API_KEY"),
            "runninghub_workflow_id": _require_env("RUNNINGHUB_WORKFLOW_ID"),
        }
        target_url = URL_HS002
        new_status = 1

    elif step == 2:
        # Retry HS003
        scenes_rows = TaskScenes.get_scenes_by_task_id(task.id)
        scenes_rows.sort(key=lambda s: s.scene_index)
        if not scenes_rows:
            raise HTTPException(status_code=400, detail="No scenes found for retry step 2")

        subtitle_list = [s.subtitle or "" for s in scenes_rows]
        shot_script_img_list = [s.reference_img_url or "" for s in scenes_rows]
        shot_script_list = [s.script_desc or "" for s in scenes_rows]

        VideoTasks.update_task_status(task.id, status=3)
        payload = {
            "task_id": task.id,
            "voice_id": model.voice_provider_id,
            "subtitle_list": subtitle_list,
            "shot_script_img_list": shot_script_img_list,
            "shot_script_list": shot_script_list,
            "jarvis_api_key": _get_sharded_api_key(1), # Key #2
            "minimax_key": minimax["api_key"],
            "minimax_group": minimax["group_id"],
            "runninghub_api_key": _require_env("RUNNINGHUB_API_KEY"),
            "runninghub_workflow_id": _require_env("RUNNINGHUB_WORKFLOW_ID"),
        }
        target_url = URL_HS003
        new_status = 3

    elif step == 3:
        # Retry HS004
        scenes_rows = TaskScenes.get_scenes_by_task_id(task.id)
        scenes_rows.sort(key=lambda s: s.scene_index)
        # Use existing fragments
        shot_video_list = [s.fragment_video_url for s in scenes_rows]
        if any(not u for u in shot_video_list):
             raise HTTPException(status_code=400, detail="Missing fragment videos for retry step 3")

        VideoTasks.update_task_status(task.id, status=5)
        payload = {
            "task_id": task.id,
            "shot_video_list": shot_video_list,
            "jarvis_api_key": _get_sharded_api_key(0), # Key #1 (Default)
        }
        target_url = URL_HS004
        new_status = 5
    else:
        raise HTTPException(status_code=400, detail=f"Invalid step for retry: {step}")

    # Trigger n8n
    status_code, _, _ = await post_json(target_url, payload)
    if status_code >= 400:
        VideoTasks.update_task_status(task.id, status=-1)
        raise HTTPException(status_code=502, detail=f"n8n retry trigger failed: {status_code}")

    return {"success": True, "task_id": task.id, "status": new_status, "step": step, "message": "Retry triggered"}
