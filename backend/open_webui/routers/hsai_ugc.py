import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import traceback
from typing import List, Dict, Any, Optional, Tuple, Set, Union

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Body
from pydantic import BaseModel, Field, AliasChoices, ConfigDict

from open_webui.config import CREDIT_DEFAULT_CREDIT, CREDIT_NO_CREDIT_MSG
from open_webui.internal.db import get_db
from open_webui.utils.auth import get_verified_user
from open_webui.storage.provider import Storage
from open_webui.models.billing_config import BillingConfigs
from open_webui.models.api_usage_log import APIUsageLogs, APIUsageLogForm
from open_webui.models.credits import Credit, CreditLog, CreditLogModel, Credits, SetCreditFormDetail
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
    ProductsListResponse,
    UGCTaskUpdateEvent,
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
URL_HS002_SHOT_IMG = f"{N8N_UGC_BASE_URL}/ugc_product_shot_img" # Generate Shot Image (Retry)
URL_HS003_SHOT_VIDEO = f"{N8N_UGC_BASE_URL}/ugc_video_shot" # Generate Shot Video (Retry)


def _utcnow() -> datetime:
    return datetime.utcnow()


def _epoch_now() -> int:
    return int(time.time())


def _get_billing_int(config_type: str, config_key: str, field: str, default: int) -> int:
    """
    Read an integer field from billing_config.config_value.
    Example:
      config_type=ugc, config_key=retry_cooldown_seconds, config_value={"seconds":"600"}
    """
    cfg = BillingConfigs.get_config_by_type_and_key(config_type, config_key)
    if not cfg or not isinstance(getattr(cfg, "config_value", None), dict):
        return int(default)
    raw = cfg.config_value.get(field, default)
    try:
        return int(raw)
    except Exception:
        return int(default)


def _ugc_full_video_cost() -> Decimal:
    # Option 2: rate comes from billing_config (resource/<key>). Missing config -> treat as 0.
    cost = BillingConfigs.get_billing_rate("resource", "ugc_video_full")
    try:
        return Decimal(cost)
    except Exception:
        return Decimal("0")


def _ugc_free_retry_window_days() -> int:
    days = _get_billing_int("ugc", "free_retry_window_days", "days", 3)
    return max(int(days), 1)


def _ugc_retry_cooldown_seconds() -> int:
    seconds = _get_billing_int("ugc", "retry_cooldown_seconds", "seconds", 600)
    return max(int(seconds), 600)


def _enforce_user_cooldown(*, user_id: str, now_dt: datetime) -> None:
    cooldown = _ugc_retry_cooldown_seconds()
    last_dt = VideoTasks.get_user_last_trigger_at(str(user_id))
    if not last_dt:
        return
    try:
        last_ts = int(last_dt.timestamp()) if isinstance(last_dt, datetime) else int(last_dt)
    except Exception:
        return
    now_ts = int(now_dt.timestamp())
    remaining = int(cooldown - (now_ts - last_ts))
    if remaining > 0:
        raise HTTPException(
            status_code=429,
            detail={"message": f"冷却时间未结束，请等待 {remaining} 秒后再发起生成", "remaining_seconds": remaining},
        )


def _record_ugc_usage_log(*, user_id: str, task_id: str, action: str, credits_consumed: Decimal) -> None:
    # Best-effort: do not block main flow.
    try:
        APIUsageLogs.insert_new_log(
            APIUsageLogForm(
                user_id=str(user_id),
                session_id=str(task_id),
                service_provider="ugc",
                model_name=str(action),
                credits_consumed=Decimal(str(credits_consumed or 0)),
            )
        )
    except Exception:
        pass


def _precharge_ugc_full_video(*, user_id: str, task_id: str, cost: Decimal) -> None:
    """
    Pre-charge credits at hs002 stage (script generation).
    - Must be atomic: lock credit row, check balance, then deduct.
    - Writes credit_log for traceability.
    """
    if cost is None or Decimal(str(cost)) <= 0:
        return
    cost = Decimal(str(cost))
    now_epoch = _epoch_now()

    with get_db() as db:
        dialect_name = db.get_bind().dialect.name.lower() if db.get_bind() else ""

        resolved_user_id, resolved_company_id = Credits._resolve_credit_owner(user_id=str(user_id), company_id=None)

        q = None
        if resolved_company_id:
            q = db.query(Credit).filter(Credit.company_id == resolved_company_id)
        else:
            q = db.query(Credit).filter(Credit.user_id == resolved_user_id)
        if dialect_name and dialect_name != "sqlite":
            q = q.with_for_update()
        credit_row = q.first()

        if not credit_row:
            credit_row = Credit(
                id=uuid.uuid4().hex,
                user_id=resolved_user_id,
                company_id=resolved_company_id,
                credit=Decimal(CREDIT_DEFAULT_CREDIT.value),
                created_at=now_epoch,
                updated_at=now_epoch,
            )
            db.add(credit_row)
            db.flush()

        current = Decimal(str(getattr(credit_row, "credit", 0) or 0))
        if current < cost:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": CREDIT_NO_CREDIT_MSG.value,
                    "required_credits": float(cost),
                    "current_credits": float(current),
                },
            )

        balance_after = current - cost

        log_entry = CreditLogModel(
            user_id=resolved_user_id,
            company_id=resolved_company_id,
            credit=balance_after,
            detail=SetCreditFormDetail(
                api_path="/api/v1/ugc/tasks",
                api_params={"task_id": str(task_id), "cost": float(cost)},
                desc="ugc full-video precharge",
            ).model_dump(),
            created_at=now_epoch,
        )
        db.add(CreditLog(**log_entry.model_dump()))

        db.query(Credit).filter(Credit.id == credit_row.id).update(
            {"credit": balance_after, "updated_at": now_epoch},
            synchronize_session=False,
        )
        db.commit()


def _enforce_free_retry_window_and_cooldown(*, user_id: str, task: VideoTaskData, now_dt: datetime) -> None:
    # Free retry window: after expiry, close task and deny retry entrance.
    if task.free_retry_until is not None:
        try:
            if int(task.free_retry_until) < int(now_dt.timestamp()):
                VideoTasks.close_task(str(task.id), closed_reason="free_retry_window_expired")
                raise HTTPException(status_code=400, detail="已超过免费重试窗口，请重新创建任务")
        except HTTPException:
            raise
        except Exception:
            # If parsing fails, do not block.
            pass

    # Cooldown: user-level, starts from each generate/retry request time (including scene retries).
    cooldown = _ugc_retry_cooldown_seconds()
    last_dt = VideoTasks.get_user_last_trigger_at(str(user_id))
    if not last_dt:
        return
    try:
        last_ts = int(last_dt.timestamp()) if isinstance(last_dt, datetime) else int(last_dt)
    except Exception:
        return
    now_ts = int(now_dt.timestamp())
    remaining = int(cooldown - (now_ts - last_ts))
    if remaining > 0:
        raise HTTPException(
            status_code=429,
            detail={"message": f"冷却时间未结束，请等待 {remaining} 秒后重试", "remaining_seconds": remaining},
        )


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

@router.post(
    "/models", 
    response_model=MaterialModelData, 
    summary="创建数字人资产 (Step 0)",
    description="""
    创建数字人基础资产：
    1. 上传数字人形象图片和音色音频到存储。
    2. 调用 n8n hs001 克隆音色。
    3. 保存资产记录到数据库。
    """,
    responses={
        502: {"description": "音色克隆服务(n8n)调用失败或超时"},
        504: {"description": "音色克隆服务超时"}
    }
)
async def create_material_model(
    model_name: str = Form(..., description="数字人名称"),
    minimax_account_id: Optional[int] = Form(None, description="指定MiniMax账号ID (可选)"),
    model_img: UploadFile = File(..., description="数字人形象图片 (建议512x512)"),
    voice_audio: UploadFile = File(..., description="音色克隆源音频 (WAV/MP3)"),
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
        
        # hs001 音色克隆需要较长时间,设置 60 秒超时
        hs001_timeout = int(os.getenv("N8N_UGC_HS001_TIMEOUT", "60"))
        try:
            status_code, data, raw_text = await post_json(
                URL_HS001, 
                payload, 
                timeout_seconds=hs001_timeout
            )
            log.info(f"n8n hs001 response: code={status_code}, data={data}, text={raw_text[:200] if raw_text else ''}")
        except Exception as e:
            error_type = type(e).__name__
            log.error(f"n8n hs001 request failed ({error_type}): {e}")
            if "TimeoutError" in error_type:
                raise HTTPException(
                    status_code=504,
                    detail=f"音色克隆服务超时(>{hs001_timeout}秒),请稍后重试或联系管理员"
                )
            raise HTTPException(
                status_code=502,
                detail=f"音色克隆服务异常: {str(e)[:100]}"
            )
        
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


@router.delete(
    "/models/{model_id}", 
    summary="删除数字人资产 (含MiniMax Voice)",
    description="""
    删除数字人资产(软删除)：
    1. 调用 MiniMax API 删除远端 Voice 插槽。
    2. 标记本地数据库记录为已删除 (保留历史任务引用)。
    注意：此操作不可逆。
    """,
    responses={
        404: {"description": "资产未找到"},
        502: {"description": "MiniMax API 调用失败"}
    }
)
async def delete_material_model(model_id: int, user=Depends(get_verified_user)):
    """
    删除数字人资产(软删除):
    1. 根据 model_id 查找资产(校验所有权)。
    2. 获取关联的 voice_provider_id 和 minimax_account_id。
    3. 调用 MiniMax API 删除远端 Voice(释放插槽) - 必须成功。
    4. 标记本地 DB 记录为已删除(软删除,保留历史任务引用)。
    
    流程一致性保证:
    - MiniMax API 调用失败 → 抛出异常,不执行软删除
    - MiniMax API 调用成功 → 执行软删除
    - 软删除失败 → 抛出异常(此时插槽已释放,需人工介入)
    """
    try:
        user_id = _require_user_id(user)
        model = MaterialModels.get_model_by_id_and_user_id(model_id, user_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        voice_id = getattr(model, "voice_provider_id", "")
        account_id = getattr(model, "minimax_account_id", None)
        
        # Step 1: 释放 MiniMax 插槽(关键步骤,必须成功)
        minimax_deleted = False
        if voice_id:
            try:
                minimax = _resolve_minimax_credentials(
                    account_id,
                    require_group=False,
                    allow_env_fallback=True,
                )
                api_key = minimax["api_key"]
                
                log.info(f"Deleting MiniMax voice {voice_id} for model {model_id}")
                await minimax_speech_client.delete_voice(
                    api_key=api_key,
                    voice_type="voice_cloning",
                    voice_id=voice_id
                )
                minimax_deleted = True
                log.info(f"MiniMax voice {voice_id} deleted successfully")
                
            except HTTPException as e:
                # 凭证问题
                log.error(f"MiniMax credentials error: {e.detail}")
                raise HTTPException(
                    status_code=500,
                    detail=f"无法获取 MiniMax 凭证以释放插槽: {e.detail}"
                )
            except MinimaxAPIError as e:
                # MiniMax API 错误
                # 404 可能表示插槽已被释放,可以容忍
                if e.status == 404:
                    log.warning(f"MiniMax voice {voice_id} not found (already deleted?), proceeding")
                    minimax_deleted = True
                else:
                    log.error(f"MiniMax API error: {e.message} (status={e.status})")
                    raise HTTPException(
                        status_code=502,
                        detail=f"MiniMax 插槽释放失败: {e.message}"
                    )
            except Exception as e:
                log.error(f"Unexpected error deleting MiniMax voice: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"释放 MiniMax 插槽时发生未知错误: {str(e)}"
                )
        else:
            # 没有 voice_id,跳过 MiniMax 删除
            log.warning(f"Model {model_id} has no voice_provider_id, skipping MiniMax deletion")
            minimax_deleted = True

        # Step 2: 软删除本地记录(仅在 MiniMax 成功后执行)
        if minimax_deleted:
            ok = MaterialModels.delete_model(model.id)
            if not ok:
                # 严重错误:插槽已释放但本地标记失败
                log.error(f"CRITICAL: MiniMax voice deleted but local soft-delete failed for model {model_id}")
                raise HTTPException(
                    status_code=500,
                    detail="MiniMax 插槽已释放,但本地删除标记失败,请联系管理员"
                )
            
            log.info(f"Model {model_id} soft-deleted successfully")
            return {"success": True, "model_id": model_id, "minimax_deleted": True}
        else:
            # 理论上不会到这里
            raise HTTPException(status_code=500, detail="删除流程异常")

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

@router.get("/products", response_model=ProductsListResponse, summary="产品列表")
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


def _get_spare_jarvis_key() -> Optional[str]:
    """
    Optional spare Jarvis key for downstream LLM fallback in n8n workflows.

    Priority:
    1) Explicit env `JARVIS_API_KEY_SPARE`
    2) The 3rd entry of `JARVIS_API_KEY` if configured as comma-separated list
    """
    spare = (os.getenv("JARVIS_API_KEY_SPARE") or "").strip()
    if spare:
        return spare

    try:
        raw_val = os.getenv("JARVIS_API_KEY") or ""
        keys = [k.strip() for k in raw_val.split(",") if k.strip()]
        if len(keys) >= 3:
            return keys[2]
    except Exception:
        pass

    return None


@router.post(
    "/tasks", 
    response_model=VideoTaskData, 
    summary="创建视频生成任务 (Step 1)",
    description="""
    创建视频生成任务并触发脚本生成 (Step 1 -> hs002)：
    - 支持按 `product_id` (推荐) 或直接传参 (兼容模式)。
    - 成功创建后任务状态为 1 (脚本生成中)。
    """,
    responses={
        404: {"description": "模型或产品未找到"},
        502: {"description": "脚本生成服务(n8n)调用失败"}
    }
)
async def create_video_task(form: VideoTaskCreateForm, user=Depends(get_verified_user)):
    """
    创建视频生成任务,并触发 n8n hs002 生成脚本。
    
    支持两种模式:
    1. 产品库模式(推荐): 提交 product_id,从产品库获取产品信息
    2. 兼容模式: 直接提交 product_name 和 product_url (已废弃,但保持兼容)
    """
    try:
        user_id = _require_user_id(user)
        model = MaterialModels.get_model_by_id_and_user_id(form.model_id, user_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        # User-level cooldown (including scene retries) to avoid bursty load.
        _enforce_user_cooldown(user_id=user_id, now_dt=_utcnow())

        # 产品信息解析:优先使用产品库
        # 约定：
        # - product_url: 产品图 URL（n8n hs002 仍可能按旧字段读取）
        # - product_img: 产品图 URL（新字段，逐步迁移）
        product_name = None
        product_desc = ""
        product_img = ""
        product_url = ""
        payload_product_name = None
        
        if form.product_id is not None:
            # 模式1: 从产品库获取
            product = Products.get_product(form.product_id)
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            if product.user_id != user_id:
                raise HTTPException(status_code=403, detail="Product access denied")
            
            product_name = product.name
            product_desc = (product.description or "").strip()
            product_img = product.cover_img or ""
            # 兼容：n8n 侧仍可能读取 product_url（旧字段）
            product_url = (form.product_url or "").strip() or product_img
            if not product_url:
                raise HTTPException(status_code=400, detail="Product cover image is required")
            log.info(f"Using product from library: id={form.product_id}, name={product_name}")
            # n8n hs002 兼容：当使用产品库 product_id 时，将“名称+描述”合并到 product_name 字段中。
            # 约定格式："产品名称,产品描述"（字符串）
            payload_product_name = f"{product_name},{product_desc}"
            
        elif form.product_name:
            # 模式2: 兼容旧接口(直接使用提交的参数)
            product_name = form.product_name
            product_url = (form.product_url or "").strip()
            if not product_url:
                # 旧接口历史上允许缺省，但 n8n hs002 已在多数流程中强依赖产品图；
                # 提前返回 400 让前端可明确提示用户补齐输入，而不是让任务卡住/报 500。
                raise HTTPException(status_code=400, detail="product_url is required in legacy mode")
            # 兼容：补齐新字段 product_img，便于 n8n 新旧版本都可消费
            product_img = product_url
            log.warning(f"Using legacy product parameters: name={product_name}")
            payload_product_name = product_name
            
        else:
            # 两者都没提供
            raise HTTPException(
                status_code=400,
                detail="Either product_id or product_name must be provided"
            )

        # 确保任务可追溯：将解析后的 product_name/product_url 写入 base_inputs（而不是保留 None）
        form_for_task = form.model_copy(update={"product_name": product_name, "product_url": product_url})

        # Billing: pre-charge full-video credits at script generation (hs002).
        now_dt = _utcnow()
        task_uuid = str(uuid.uuid4())
        cost = _ugc_full_video_cost()
        _precharge_ugc_full_video(user_id=user_id, task_id=task_uuid, cost=cost)

        # Free retry window + cooldown anchor.
        free_days = _ugc_free_retry_window_days()
        free_until = now_dt + timedelta(days=free_days)

        task = VideoTasks.create_task(
            user_id,
            form_for_task,
            task_id=task_uuid,
            billed_credits=cost,
            billed_at=now_dt,
            free_retry_until=free_until,
            last_trigger_at=now_dt,
        )

        # Usage record: created when the generation request is issued.
        _record_ugc_usage_log(user_id=user_id, task_id=task.id, action="ugc_video_full", credits_consumed=cost)
        # 保存产品库上下文，便于 hs002 重试/审计（legacy 模式下 product_id 为空，不写入也不影响）
        try:
            VideoTasks.patch_base_inputs(
                task.id,
                {
                    "product_id": form.product_id,
                    "product_desc": product_desc,
                },
            )
        except Exception:
            # best-effort: 不影响主流程
            pass
        
        # 触发 n8n 生成脚本
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
            # product_url/product_img 同时发送：兼容 n8n 旧流程与新流程
            "product_url": product_url,
            "product_name": payload_product_name,
            "product_img": product_img,
            "product_country": form.product_country or "",
            "language": form.language,
            "subtitle": form.subtitle or "",
            "shot_script": form.shot_script or "",
            "creative_bias": form.creative_bias or "",
            "jarvis_api_key": _get_sharded_api_key(0),
            "minimax_key": minimax["api_key"],
            "minimax_group": minimax["group_id"],
            "runninghub_api_key": _require_env("RUNNINGHUB_API_KEY"),
            "runninghub_workflow_id": _require_env("RUNNINGHUB_WORKFLOW_ID"),
        }
        try:
            status_code, _, _ = await post_json(URL_HS002, payload)
        except Exception as e:
            # post_json 对 5xx 会重试后抛异常；此处将任务标记为 FAILED，且对外返回 502（上游错误）
            VideoTasks.update_task_status(task.id, status=-1)
            raise HTTPException(status_code=502, detail=f"n8n script generation trigger failed: {e}")
        
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
    # input-only aliases:
    # - shot_script -> script_desc
    # - shot_script_img -> reference_img_url
    script_desc: Optional[str] = Field(default=None, validation_alias=AliasChoices("script_desc", "shot_script"))
    reference_img_url: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("reference_img_url", "shot_script_img")
    )


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


class UGCGenerateVideoForm(BaseModel):
    """
    Body wrapper for /tasks/{task_id}/generate_video.
    NOTE: extra fields are ignored for forward/backward compatibility.
    """

    model_config = ConfigDict(extra="ignore")

# ---------------------------------------------------------
# Documentation Endpoints
# ---------------------------------------------------------

@router.get("/docs/events", response_model=UGCTaskUpdateEvent, summary="WebSocket 事件结构")
async def get_websocket_event_schema():
    """
    仅用于文档展示 WebSocket `hsai_ugc_update` 事件的 Payload 结构。
    实际不返回数据。
    """
    return UGCTaskUpdateEvent(
        task_id="demo_id", 
        type="usage_info"
    )


UGCGenerateVideoPayload = Union[List[TaskSceneEditItem], UGCGenerateVideoForm]


def _parse_generate_video_scenes(payload: Any) -> List[TaskSceneEditItem]:
    """
    Body parser for /tasks/{task_id}/generate_video.

    Supported formats:
    - Legacy/Recommended: List[TaskSceneEditItem]  (the list itself is the selected scenes, in order)
    - Wrapper: {"scenes": [...]}  (extra keys are ignored)
    """
    if payload is None:
        return []
    if isinstance(payload, list):
        scenes: List[TaskSceneEditItem] = []
        for item in payload:
            if isinstance(item, TaskSceneEditItem):
                scenes.append(item)
                continue
            if not isinstance(item, dict):
                raise HTTPException(status_code=400, detail="Each scene must be an object")
            scenes.append(TaskSceneEditItem.model_validate(item))
        return scenes
    if isinstance(payload, UGCGenerateVideoForm):
        return payload.scenes or []
    if isinstance(payload, dict):
        try:
            return UGCGenerateVideoForm.model_validate(payload).scenes or []
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request body")
    raise HTTPException(status_code=400, detail="Invalid request body")


@router.post(
    "/tasks/{task_id}/generate_video",
    response_model=List[TaskSceneData],
    summary="生成分镜视频（hs003）",
)
async def generate_scene_videos(
    task_id: str,
    payload: Optional[UGCGenerateVideoPayload] = Body(default=None),
    user=Depends(get_verified_user),
):
    """
    对标 n8n hs003：生成分镜视频（Step 2）。

    - 前端可在 status=2(PENDING_EDIT) 时提交分镜编辑内容；
    - 以本次提交的 scenes 列表作为“选中分镜集合”（服务端会删除未提交分镜；scene_index 可不连续）；
    - 入参字段别名兼容（仅入参）：shot_script -> script_desc，shot_script_img -> reference_img_url；
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

    scenes = _parse_generate_video_scenes(payload)
    if not scenes:
        raise HTTPException(status_code=400, detail="scenes is required")

    ordered_indices: List[int] = []
    seen_indices: Set[int] = set()
    for item in scenes:
        try:
            idx = int(item.scene_index)
        except Exception:
            raise HTTPException(status_code=400, detail="scene_index must be an integer")
        if idx < 0:
            raise HTTPException(status_code=400, detail="scene_index must be >= 0")
        if idx in seen_indices:
            raise HTTPException(status_code=400, detail=f"Duplicate scene_index: {idx}")
        ordered_indices.append(idx)
        seen_indices.add(idx)

    existing = TaskScenes.get_scenes_by_task_id(task_id)
    existing_map = {s.scene_index: s for s in existing}

    # 1) Validate indices exist, then apply user edits (patch semantics).
    missing = [i for i in ordered_indices if i not in existing_map]
    if missing:
        raise HTTPException(status_code=400, detail=f"Invalid scene_index: {missing}")

    for item in scenes:
        patch = item.model_dump(exclude_unset=True)
        patch.pop("scene_index", None)
        if not patch:
            continue
        TaskScenes.update_scene(existing_map[item.scene_index].id, TaskSceneUpdateForm(**patch))

    # 2) Treat submitted scenes as the selected set: delete unsubmitted scenes.
    TaskScenes.delete_scenes_except_indices(task_id, ordered_indices)

    updated_all = TaskScenes.get_scenes_by_task_id(task_id)
    updated_map = {s.scene_index: s for s in updated_all}
    updated_scenes_in_order = [updated_map[i] for i in ordered_indices]

    # Persist mapping for VIDEO_RESULT callback handling.
    # The list order is the canonical "scene order" from the frontend submission.
    VideoTasks.patch_base_inputs(task_id, {"hs003_scene_index_list": ordered_indices})

    subtitle_list = [s.subtitle or "" for s in updated_scenes_in_order]
    shot_script_img_list = [s.reference_img_url or "" for s in updated_scenes_in_order]
    shot_script_list = [s.script_desc or "" for s in updated_scenes_in_order]

    VideoTasks.update_task_status(task_id, status=3, step=2)
    minimax = _resolve_minimax_credentials(
        getattr(model, "minimax_account_id", None),
        require_group=True,
        allow_env_fallback=True,
    )
    payload = {
        "task_id": task_id,
        "voice_id": model.voice_provider_id,
        "shot_list": [
            {
                "shot_id": s.scene_index, # Align with n8n terminology
                "subtitle": s.subtitle or "",
                "shot_script_img": s.reference_img_url or "",
                "shot_script": s.script_desc or "",
            }
            for s in updated_scenes_in_order
        ],
        "jarvis_api_key": _get_sharded_api_key(1), # Key #2 for Step 2
        "minimax_key": minimax["api_key"],
        "minimax_group": minimax["group_id"],
        "runninghub_api_key": _require_env("RUNNINGHUB_API_KEY"),
        "runninghub_workflow_id": _require_env("RUNNINGHUB_WORKFLOW_ID"),
    }
    sparekey = _get_spare_jarvis_key()
    if sparekey:
        payload["sparekey"] = sparekey
    status_code, _, _ = await post_json(URL_HS003, payload)
    if status_code >= 400:
        VideoTasks.update_task_status(task_id, status=-1)
        raise HTTPException(status_code=502, detail=f"n8n video generation trigger failed: {status_code}")

    return updated_scenes_in_order


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
    if not scenes_rows:
        raise HTTPException(status_code=400, detail="No scenes found for task")

    # Respect frontend-selected order when available (persisted in base_inputs during hs003 trigger).
    scenes_map = {s.scene_index: s for s in scenes_rows}
    ordered_scene_indices: List[int]
    base_inputs = getattr(task, "base_inputs", {}) or {}
    raw_order = base_inputs.get("hs003_scene_index_list") if isinstance(base_inputs, dict) else None
    if isinstance(raw_order, list):
        try:
            candidate = [int(v) for v in raw_order]
        except Exception:
            candidate = []
        if candidate and len(candidate) == len(scenes_rows) and set(candidate) == set(scenes_map.keys()):
            ordered_scene_indices = candidate
        else:
            ordered_scene_indices = sorted(scenes_map.keys())
    else:
        ordered_scene_indices = sorted(scenes_map.keys())

    ordered_scenes_rows = [scenes_map[i] for i in ordered_scene_indices]

    form: Optional[UGCMergeForm] = None
    if isinstance(payload, dict):
        try:
            form = UGCMergeForm.model_validate(payload)
        except Exception:
            form = None

    # Compatibility: allow payload to be a raw list of urls.
    shot_video_list = payload if isinstance(payload, list) else (form.shot_video_list if form else None)

    if form and form.selections:
        selection_map: Dict[int, str] = {}
        for item in form.selections:
            if item.scene_index not in scenes_map:
                raise HTTPException(status_code=400, detail=f"Invalid scene_index: {item.scene_index}")
            selection_map[item.scene_index] = item.video_url
            # Persist user selection for traceability / future retries.
            TaskScenes.update_fragment_video_url(task_id, item.scene_index, item.video_url)

        shot_video_list = [selection_map.get(s.scene_index) or s.fragment_video_url for s in ordered_scenes_rows]

    if not shot_video_list:
        shot_video_list = [s.fragment_video_url for s in ordered_scenes_rows]

    if len(shot_video_list) != len(ordered_scenes_rows):
        raise HTTPException(status_code=400, detail="shot_video_list length mismatch")
    if any(not u for u in shot_video_list):
        raise HTTPException(status_code=400, detail="Not all scene videos are selected/ready")

    VideoTasks.update_task_status(task_id, status=5, step=3)
    hs004_payload = {
        "task_id": task_id,
        "shot_list": [
            {"shot_id": row.scene_index, "shot_video_url": url}
            for row, url in zip(ordered_scenes_rows, shot_video_list)
        ],
        "jarvis_api_key": _get_sharded_api_key(0), # Key #1 (default)
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

    now_dt = _utcnow()
    _enforce_free_retry_window_and_cooldown(user_id=user_id, task=task, now_dt=now_dt)

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
        VideoTasks.update_task_status(task.id, status=1, step=1)

        # 产品库模式：按约定将“名称+描述”合并到 hs002 product_name 字段（字符串）。
        retry_product_name = form_dict.get("product_name")
        if isinstance(form_dict, dict) and form_dict.get("product_id") is not None:
            name = str(form_dict.get("product_name") or "")
            desc = str(form_dict.get("product_desc") or "")
            retry_product_name = f"{name},{desc}"

        # n8n hs002 兼容：同时发送 product_url + product_img（新旧字段并存）。
        retry_product_url = (form_dict.get("product_url") or "").strip() if isinstance(form_dict, dict) else ""
        retry_product_img = (form_dict.get("product_img") or "").strip() if isinstance(form_dict, dict) else ""
        if not retry_product_url:
            retry_product_url = retry_product_img
        if not retry_product_img:
            retry_product_img = retry_product_url
         
        payload = {
            "task_id": task.id,
            "ip_id": f"model_{model.id}",
            "ip_name": model.model_name,
            "ip_img": model.model_img_url,
            "voice_id": model.voice_provider_id,
            "product_url": retry_product_url,
            "product_name": retry_product_name,
            "product_img": retry_product_img,
            "product_country": form_dict.get("product_country") or "",
            "language": form_dict.get("language"),
            "subtitle": form_dict.get("subtitle") or "",
            "shot_script": form_dict.get("shot_script") or "",
            "creative_bias": form_dict.get("creative_bias") or "",
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
        if not scenes_rows:
            raise HTTPException(status_code=400, detail="No scenes found for retry step 2")

        scenes_map = {s.scene_index: s for s in scenes_rows}
        base_inputs = getattr(task, "base_inputs", {}) or {}
        raw_order = base_inputs.get("hs003_scene_index_list") if isinstance(base_inputs, dict) else None
        if isinstance(raw_order, list):
            try:
                candidate = [int(v) for v in raw_order]
            except Exception:
                candidate = []
            if candidate and len(candidate) == len(scenes_rows) and set(candidate) == set(scenes_map.keys()):
                ordered_scene_indices = candidate
            else:
                ordered_scene_indices = sorted(scenes_map.keys())
        else:
            ordered_scene_indices = sorted(scenes_map.keys())

        ordered_scenes_rows = [scenes_map[i] for i in ordered_scene_indices]

        # Persist mapping for VIDEO_RESULT callback handling (scene_index can be non-contiguous and ordered by frontend).
        VideoTasks.patch_base_inputs(task.id, {"hs003_scene_index_list": ordered_scene_indices})

        subtitle_list = [s.subtitle or "" for s in ordered_scenes_rows]
        shot_script_img_list = [s.reference_img_url or "" for s in ordered_scenes_rows]
        shot_script_list = [s.script_desc or "" for s in ordered_scenes_rows]

        VideoTasks.update_task_status(task.id, status=3, step=2)
        payload = {
            "task_id": task.id,
            "voice_id": model.voice_provider_id,
            # n8n V2+ expects shot_list; keep legacy *_list fields for backward compatibility.
            "shot_list": [
                {
                    "shot_id": s.scene_index,
                    "subtitle": s.subtitle or "",
                    "shot_script_img": s.reference_img_url or "",
                    "shot_script": s.script_desc or "",
                }
                for s in ordered_scenes_rows
            ],
            "subtitle_list": subtitle_list,
            "shot_script_img_list": shot_script_img_list,
            "shot_script_list": shot_script_list,
            "jarvis_api_key": _get_sharded_api_key(1), # Key #2
            "minimax_key": minimax["api_key"],
            "minimax_group": minimax["group_id"],
            "runninghub_api_key": _require_env("RUNNINGHUB_API_KEY"),
            "runninghub_workflow_id": _require_env("RUNNINGHUB_WORKFLOW_ID"),
        }
        sparekey = _get_spare_jarvis_key()
        if sparekey:
            payload["sparekey"] = sparekey
        target_url = URL_HS003
        new_status = 3

    elif step == 3:
        # Retry HS004
        scenes_rows = TaskScenes.get_scenes_by_task_id(task.id)
        scenes_rows.sort(key=lambda s: s.scene_index)
        # Use existing fragments (hs004 expects shot_list)
        shot_list = [
            {"shot_id": s.scene_index, "shot_video_url": s.fragment_video_url}
            for s in scenes_rows
        ]
        if not shot_list or any(not item.get("shot_video_url") for item in shot_list):
            raise HTTPException(status_code=400, detail="Missing fragment videos for retry step 3")

        VideoTasks.update_task_status(task.id, status=5)
        payload = {
            "task_id": task.id,
            "shot_list": shot_list,
            "jarvis_api_key": _get_sharded_api_key(0), # Key #1 (Default)
        }
        target_url = URL_HS004
        new_status = 5
    else:
        raise HTTPException(status_code=400, detail=f"Invalid step for retry: {step}")

    # Trigger n8n
    VideoTasks.touch_last_trigger_at(task.id, when=now_dt)
    _record_ugc_usage_log(
        user_id=user_id,
        task_id=task.id,
        action=f"ugc_retry_task_step_{step}",
        credits_consumed=Decimal("0"),
    )
    try:
        status_code, _, _ = await post_json(target_url, payload)
    except Exception as e:
        # post_json raises after retrying on 5xx/timeout; convert to 502 to avoid leaking 500 to clients.
        VideoTasks.update_task_status(task.id, status=-1)
        raise HTTPException(status_code=502, detail=f"n8n retry trigger failed: {e}")
    if status_code >= 400:
        VideoTasks.update_task_status(task.id, status=-1)
        raise HTTPException(status_code=502, detail=f"n8n retry trigger failed: {status_code}")

    return {"success": True, "task_id": task.id, "status": new_status, "step": step, "message": "Retry triggered"}


@router.post("/tasks/{task_id}/scenes/{scene_index}/regenerate_image", summary="分镜重绘图片 (hs002_shot_img)")
async def regenerate_scene_image(
    task_id: str,
    scene_index: int,
    payload: Dict[str, Any] = Body(default=None),
    user=Depends(get_verified_user),
):
    """
    重绘单个分镜图片 (Step 1 -> 2 单点重试)。
    """
    user_id = _require_user_id(user)
    task = VideoTasks.get_task_by_id(task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    now_dt = _utcnow()
    _enforce_free_retry_window_and_cooldown(user_id=user_id, task=task, now_dt=now_dt)

    now_dt = _utcnow()
    _enforce_free_retry_window_and_cooldown(user_id=user_id, task=task, now_dt=now_dt)

    scenes = TaskScenes.get_scenes_by_task_id(task_id)
    target_scene = next((s for s in scenes if s.scene_index == scene_index), None)
    if not target_scene:
        raise HTTPException(status_code=404, detail=f"Scene {scene_index} not found")

    # Construct Payload
    base_inputs = getattr(task, "base_inputs", {}) or {}
    product_url = base_inputs.get("product_url")
    
    # Optional overrides from request body
    user_prompt = payload.get("image_prompt") if payload else None
    
    # Fallback: user input > scene script > scene subtitle > empty
    final_prompt = user_prompt or target_scene.script_desc or target_scene.subtitle or ""

    if not final_prompt:
        raise HTTPException(status_code=400, detail="Image prompt (or script description) is required")
    
    json_payload = {
        "task_id": task_id,
        "shot_id": scene_index,
        "image_prompt": final_prompt, 
        "ip_img": None, # Will be filled by n8n if empty
        # Actually spec says: ip_img from DB, product_url from DB
        "product_url": product_url,
        "jarvis_api_key": _get_sharded_api_key(0)
    }
    
    # We need model info for ip_img
    model = MaterialModels.get_model_by_id_and_user_id(int(task.model_id), user_id)
    if model:
        json_payload["ip_img"] = model.model_img_url

    VideoTasks.touch_last_trigger_at(task.id, when=now_dt)
    _record_ugc_usage_log(
        user_id=user_id,
        task_id=task.id,
        action="ugc_retry_scene_image",
        credits_consumed=Decimal("0"),
    )

    status_code, _, _ = await post_json(URL_HS002_SHOT_IMG, json_payload)
    if status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Trigger failed: {status_code}")

    return {"success": True, "task_id": task_id, "scene_index": scene_index, "message": "Regenerating image"}


@router.post("/tasks/{task_id}/scenes/{scene_index}/regenerate_video", summary="分镜重生成视频 (hs003_shot_video)")
async def regenerate_scene_video(
    task_id: str,
    scene_index: int,
    payload: Dict[str, Any] = Body(default=None),
    user=Depends(get_verified_user),
):
    """
    重生成单个分镜视频 (Step 2 -> 3 单点重试)。
    """
    user_id = _require_user_id(user)
    task = VideoTasks.get_task_by_id(task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    scenes = TaskScenes.get_scenes_by_task_id(task_id)
    target_scene = next((s for s in scenes if s.scene_index == scene_index), None)
    if not target_scene:
        raise HTTPException(status_code=404, detail=f"Scene {scene_index} not found")

    model = MaterialModels.get_model_by_id_and_user_id(int(task.model_id), user_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    minimax = _resolve_minimax_credentials(
        getattr(model, "minimax_account_id", None),
        require_group=True,
        allow_env_fallback=True,
    )

    # Optional overrides
    req_body = payload or {}
    
    json_payload = {
        "task_id": task_id,
        "shot_id": scene_index,
        "shot_script": req_body.get("shot_script") or target_scene.script_desc or "",
        "shot_script_img": req_body.get("shot_script_img") or target_scene.reference_img_url or "",
        "subtitle": req_body.get("subtitle") or target_scene.subtitle or "",
        # Credentials
        "jarvis_api_key": _get_sharded_api_key(1),
        "minimax_key": minimax["api_key"],
        "minimax_group": minimax["group_id"],
        "runninghub_api_key": _require_env("RUNNINGHUB_API_KEY"),
        "runninghub_workflow_id": _require_env("RUNNINGHUB_WORKFLOW_ID"),
    }

    VideoTasks.touch_last_trigger_at(task.id, when=now_dt)
    _record_ugc_usage_log(
        user_id=user_id,
        task_id=task.id,
        action="ugc_retry_scene_video",
        credits_consumed=Decimal("0"),
    )

    status_code, _, _ = await post_json(URL_HS003_SHOT_VIDEO, json_payload)
    if status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Trigger failed: {status_code}")

    return {"success": True, "task_id": task_id, "scene_index": scene_index, "message": "Regenerating video"}
