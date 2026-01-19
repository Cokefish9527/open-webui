import io
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import aiohttp
from fastapi import APIRouter, Body, Depends, File, HTTPException, Path, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.hsai_minimax_accounts import MiniMaxAccounts
from open_webui.services.minimax_speech_client import MinimaxAPIError, minimax_speech_client
from open_webui.storage.provider import Storage
from open_webui.utils.external_admin_auth import verify_external_request

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", "INFO"))

router = APIRouter(prefix="/external/admin/minimax", tags=["External Admin - MiniMax Speech"])


def _dt_to_epoch_seconds(value) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value.timestamp())
    except Exception:  # pragma: no cover
        return None


def _to_public_url(file_path: str) -> str:
    if not file_path:
        raise HTTPException(status_code=500, detail="storage returned empty file_path")
    if str(file_path).startswith(("http://", "https://")):
        return str(file_path)
    expires = int(os.getenv("MINIMAX_ASSET_URL_EXPIRES_SECONDS", "7200"))
    try:
        url = Storage.generate_download_url(str(file_path), expires=expires)
        if url:
            return url
    except Exception:
        pass
    return str(file_path)


async def _download_bytes(url: str, *, max_bytes: int = 100 * 1024 * 1024) -> bytes:
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
        async with session.get(url) as resp:
            if resp.status >= 400:
                raise HTTPException(status_code=502, detail=f"download failed: {resp.status}")
            buf = bytearray()
            async for chunk in resp.content.iter_chunked(64 * 1024):
                buf.extend(chunk)
                if len(buf) > max_bytes:
                    raise HTTPException(status_code=413, detail="download too large")
            return bytes(buf)


def _require_account_credentials(account_id: int) -> Dict[str, Any]:
    account = MiniMaxAccounts.get_account(int(account_id))
    if not account:
        raise HTTPException(status_code=404, detail="MiniMax account not found")
    if not bool(getattr(account, "enabled", False)):
        raise HTTPException(status_code=409, detail="MiniMax account is disabled")
    api_key = getattr(account, "api_key", None)
    if not api_key:
        raise HTTPException(status_code=409, detail="MiniMax account missing api_key")
    return {"account": account, "api_key": str(api_key), "group_id": getattr(account, "group_id", None)}


class MiniMaxAccountCreateForm(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    api_key: Optional[str] = Field(default=None, description="MiniMax API Key（仅写入，不回传）")
    group_id: Optional[str] = Field(default=None, description="可选：MINIMAX_GROUP")
    enabled: bool = True
    is_default: bool = False
    meta_json: Optional[str] = Field(default=None, description="备注/元信息（JSON字符串或文本）")


class MiniMaxAccountUpdateForm(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    api_key: Optional[str] = Field(default=None, description="更新 API Key（仅写入）")
    clear_api_key: bool = Field(default=False, description="清空已保存的 API Key")
    group_id: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    meta_json: Optional[str] = None


class MiniMaxAccountData(BaseModel):
    id: int
    name: str
    enabled: bool
    is_default: bool
    group_id: Optional[str] = None
    has_api_key: bool
    api_key_masked: Optional[str] = None
    meta_json: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


@router.get("/accounts", response_model=List[MiniMaxAccountData], summary="列出 MiniMax 账号")
async def list_accounts(_: dict = Depends(verify_external_request)):
    items = []
    for a in MiniMaxAccounts.list_accounts():
        d = MiniMaxAccounts.to_safe_dict(a)
        items.append(
            MiniMaxAccountData(
                id=int(d["id"]),
                name=str(d.get("name") or ""),
                enabled=bool(d.get("enabled")),
                is_default=bool(d.get("is_default")),
                group_id=d.get("group_id"),
                has_api_key=bool(d.get("has_api_key")),
                api_key_masked=d.get("api_key_masked"),
                meta_json=d.get("meta_json"),
                created_at=_dt_to_epoch_seconds(d.get("created_at")),
                updated_at=_dt_to_epoch_seconds(d.get("updated_at")),
            )
        )
    return items


@router.post("/accounts", response_model=MiniMaxAccountData, summary="创建 MiniMax 账号")
async def create_account(form: MiniMaxAccountCreateForm, _: dict = Depends(verify_external_request)):
    account = MiniMaxAccounts.create_account(
        name=form.name,
        api_key=form.api_key,
        group_id=form.group_id,
        enabled=form.enabled,
        is_default=form.is_default,
        meta_json=form.meta_json,
    )
    d = MiniMaxAccounts.to_safe_dict(account)
    return MiniMaxAccountData(
        id=int(d["id"]),
        name=str(d.get("name") or ""),
        enabled=bool(d.get("enabled")),
        is_default=bool(d.get("is_default")),
        group_id=d.get("group_id"),
        has_api_key=bool(d.get("has_api_key")),
        api_key_masked=d.get("api_key_masked"),
        meta_json=d.get("meta_json"),
        created_at=_dt_to_epoch_seconds(d.get("created_at")),
        updated_at=_dt_to_epoch_seconds(d.get("updated_at")),
    )


@router.get("/accounts/{account_id}", response_model=MiniMaxAccountData, summary="获取 MiniMax 账号详情")
async def get_account(
    account_id: int = Path(..., ge=1),
    _: dict = Depends(verify_external_request),
):
    account = MiniMaxAccounts.get_account(int(account_id))
    if not account:
        raise HTTPException(status_code=404, detail="MiniMax account not found")
    d = MiniMaxAccounts.to_safe_dict(account)
    return MiniMaxAccountData(
        id=int(d["id"]),
        name=str(d.get("name") or ""),
        enabled=bool(d.get("enabled")),
        is_default=bool(d.get("is_default")),
        group_id=d.get("group_id"),
        has_api_key=bool(d.get("has_api_key")),
        api_key_masked=d.get("api_key_masked"),
        meta_json=d.get("meta_json"),
        created_at=_dt_to_epoch_seconds(d.get("created_at")),
        updated_at=_dt_to_epoch_seconds(d.get("updated_at")),
    )


@router.put("/accounts/{account_id}", response_model=MiniMaxAccountData, summary="更新 MiniMax 账号")
async def update_account(
    account_id: int = Path(..., ge=1),
    form: MiniMaxAccountUpdateForm = Body(...),
    _: dict = Depends(verify_external_request),
):
    updated = MiniMaxAccounts.update_account(
        int(account_id),
        name=form.name,
        api_key=form.api_key,
        group_id=form.group_id,
        enabled=form.enabled,
        is_default=form.is_default,
        meta_json=form.meta_json,
        clear_api_key=bool(form.clear_api_key),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="MiniMax account not found")
    d = MiniMaxAccounts.to_safe_dict(updated)
    return MiniMaxAccountData(
        id=int(d["id"]),
        name=str(d.get("name") or ""),
        enabled=bool(d.get("enabled")),
        is_default=bool(d.get("is_default")),
        group_id=d.get("group_id"),
        has_api_key=bool(d.get("has_api_key")),
        api_key_masked=d.get("api_key_masked"),
        meta_json=d.get("meta_json"),
        created_at=_dt_to_epoch_seconds(d.get("created_at")),
        updated_at=_dt_to_epoch_seconds(d.get("updated_at")),
    )


@router.delete("/accounts/{account_id}", summary="删除 MiniMax 账号")
async def delete_account(
    account_id: int = Path(..., ge=1),
    _: dict = Depends(verify_external_request),
):
    ok = MiniMaxAccounts.delete_account(int(account_id))
    if not ok:
        raise HTTPException(status_code=404, detail="MiniMax account not found")
    return {"success": True}


class VoiceGetRequest(BaseModel):
    voice_type: str = Field(description="system/voice_cloning/voice_generation/all")


@router.post("/accounts/{account_id}/test", summary="测试 MiniMax 账号可用性")
async def test_account(
    account_id: int = Path(..., ge=1),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    try:
        data = await minimax_speech_client.get_voice(api_key=creds["api_key"], voice_type="system")
        return {"success": True, "account_id": int(account_id), "sample": data.get("data")}
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")


@router.post("/accounts/{account_id}/voices", summary="获取 voices 列表（MiniMax get_voice）")
async def get_voices(
    account_id: int = Path(..., ge=1),
    req: VoiceGetRequest = Body(...),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    try:
        return await minimax_speech_client.get_voice(api_key=creds["api_key"], voice_type=req.voice_type)
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")


@router.delete("/accounts/{account_id}/voices/{voice_id}", summary="删除 voice（MiniMax delete_voice）")
async def delete_voice(
    account_id: int = Path(..., ge=1),
    voice_id: str = Path(..., min_length=1),
    voice_type: str = Query("voice_cloning", description="system/voice_cloning/voice_generation"),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    try:
        return await minimax_speech_client.delete_voice(
            api_key=creds["api_key"],
            voice_type=voice_type,
            voice_id=str(voice_id),
        )
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")


@router.post("/accounts/{account_id}/files/upload", summary="上传文件（MiniMax files/upload）")
async def upload_file(
    account_id: int = Path(..., ge=1),
    purpose: str = Query("voice_clone", description="voice_clone/voice_prompt等，按 MiniMax 文档"),
    file: UploadFile = File(...),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    content = await file.read()
    try:
        return await minimax_speech_client.upload_file(
            api_key=creds["api_key"],
            purpose=purpose,
            filename=file.filename or "upload.bin",
            content=content,
            content_type=file.content_type,
        )
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")


@router.get("/accounts/{account_id}/files/list", summary="列出文件（MiniMax files/list）")
async def list_files(
    account_id: int = Path(..., ge=1),
    purpose: str = Query(..., description="voice_clone/voice_prompt等"),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    try:
        return await minimax_speech_client.list_files(api_key=creds["api_key"], purpose=purpose)
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")


@router.get("/accounts/{account_id}/files/{file_id}", summary="获取文件信息（MiniMax files/retrieve）")
async def retrieve_file(
    account_id: int = Path(..., ge=1),
    file_id: int = Path(..., ge=1),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    try:
        return await minimax_speech_client.retrieve_file(api_key=creds["api_key"], file_id=int(file_id))
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")


@router.get("/accounts/{account_id}/files/{file_id}/content", summary="下载文件内容（MiniMax files/retrieve_content）")
async def retrieve_file_content(
    account_id: int = Path(..., ge=1),
    file_id: int = Path(..., ge=1),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    try:
        _, body, headers = await minimax_speech_client.retrieve_file_content(
            api_key=creds["api_key"],
            file_id=int(file_id),
        )
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")

    content_type = headers.get("Content-Type") or "application/octet-stream"
    return StreamingResponse(io.BytesIO(body), media_type=content_type)


class DeleteFileRequest(BaseModel):
    file_id: int
    purpose: str


@router.post("/accounts/{account_id}/files/delete", summary="删除文件（MiniMax files/delete）")
async def delete_file(
    account_id: int = Path(..., ge=1),
    req: DeleteFileRequest = Body(...),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    try:
        return await minimax_speech_client.delete_file(
            api_key=creds["api_key"],
            file_id=int(req.file_id),
            purpose=req.purpose,
        )
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")


@router.post("/accounts/{account_id}/voice/clone", summary="Voice Clone（MiniMax voice_clone）")
async def voice_clone(
    account_id: int = Path(..., ge=1),
    payload: Dict[str, Any] = Body(..., description="透传 MiniMax voice_clone 请求体"),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    try:
        return await minimax_speech_client.voice_clone(api_key=creds["api_key"], payload=payload)
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")


@router.post("/accounts/{account_id}/voice/design", summary="Voice Design（MiniMax voice_design）")
async def voice_design(
    account_id: int = Path(..., ge=1),
    payload: Dict[str, Any] = Body(..., description="透传 MiniMax voice_design 请求体；支持 persist=true"),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    persist = bool(payload.pop("persist", True))

    try:
        resp = await minimax_speech_client.voice_design(api_key=creds["api_key"], payload=payload)
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")

    data = resp.get("data") if isinstance(resp, dict) else None
    if not isinstance(data, dict) or not persist:
        return resp

    trial_audio = data.get("trial_audio")
    voice_id = data.get("voice_id")

    if not trial_audio:
        return resp

    try:
        audio_bytes = bytes.fromhex(str(trial_audio))
    except Exception:
        audio_bytes = None

    if not audio_bytes:
        return resp

    filename = f"minimax_voice_design_{voice_id or 'preview'}.wav"
    _, file_path = Storage.upload_file(
        io.BytesIO(audio_bytes),
        filename,
        {"OpenWebUI-Source": "minimax-voice-design"},
    )
    data["preview_audio_url"] = _to_public_url(file_path)
    data.pop("trial_audio", None)
    return resp


@router.post("/accounts/{account_id}/speech/t2a", summary="T2A（MiniMax t2a_v2，默认 persist=true）")
async def speech_t2a(
    account_id: int = Path(..., ge=1),
    payload: Dict[str, Any] = Body(..., description="透传 MiniMax t2a_v2 请求体；支持 persist=true"),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    persist = bool(payload.pop("persist", True))
    if persist:
        payload["output_format"] = "hex"
    payload.setdefault("stream", False)

    try:
        resp = await minimax_speech_client.t2a_v2(api_key=creds["api_key"], payload=payload)
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")

    data = resp.get("data") if isinstance(resp, dict) else None
    if not isinstance(data, dict) or not persist:
        return resp

    audio = data.get("audio")
    if not audio:
        return resp

    audio_bytes: Optional[bytes] = None
    audio_str = str(audio)
    if audio_str.startswith(("http://", "https://")):
        audio_bytes = await _download_bytes(audio_str)
    else:
        try:
            audio_bytes = bytes.fromhex(audio_str)
        except Exception:
            audio_bytes = None

    if not audio_bytes:
        return resp

    filename = f"minimax_t2a_{int(account_id)}_{uuid.uuid4().hex}.wav"
    _, file_path = Storage.upload_file(
        io.BytesIO(audio_bytes),
        filename,
        {"OpenWebUI-Source": "minimax-t2a"},
    )
    data["audio_url"] = _to_public_url(file_path)
    data.pop("audio", None)
    return resp


@router.post("/accounts/{account_id}/speech/t2a_async", summary="提交异步 T2A（MiniMax t2a_async_v2）")
async def speech_t2a_async_create(
    account_id: int = Path(..., ge=1),
    payload: Dict[str, Any] = Body(..., description="透传 MiniMax t2a_async_v2 请求体"),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    try:
        return await minimax_speech_client.t2a_async_v2_create(api_key=creds["api_key"], payload=payload)
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")


@router.get("/accounts/{account_id}/speech/t2a_async/tasks/{task_id}", summary="查询异步 T2A 任务（可选拉取下载链接并持久化）")
async def speech_t2a_async_query(
    account_id: int = Path(..., ge=1),
    task_id: int = Path(..., ge=1),
    with_download_url: bool = Query(True, description="当任务完成时，是否额外查询 files/retrieve 获取 download_url"),
    persist: bool = Query(False, description="将 download_url 下载并上传到 Storage，返回 audio_url（建议配合 with_download_url）"),
    _: dict = Depends(verify_external_request),
):
    creds = _require_account_credentials(int(account_id))
    try:
        resp = await minimax_speech_client.t2a_async_v2_query(api_key=creds["api_key"], task_id=int(task_id))
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")

    if not with_download_url and not persist:
        return resp

    data = resp.get("data") if isinstance(resp, dict) else None
    if not isinstance(data, dict):
        return resp

    status_val = str(data.get("status") or "")
    file_id = data.get("file_id")

    if status_val != "Success" or not file_id:
        return resp

    try:
        file_info = await minimax_speech_client.retrieve_file(api_key=creds["api_key"], file_id=int(file_id))
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=502, detail=f"minimax error: {exc.message}")

    file_data = file_info.get("data") if isinstance(file_info, dict) else None
    if isinstance(file_data, dict):
        data["download_url"] = file_data.get("download_url")

    if persist and isinstance(file_data, dict) and file_data.get("download_url"):
        audio_bytes = await _download_bytes(str(file_data["download_url"]))
        filename = f"minimax_t2a_async_{int(task_id)}_{uuid.uuid4().hex}.wav"
        _, file_path = Storage.upload_file(
            io.BytesIO(audio_bytes),
            filename,
            {"OpenWebUI-Source": "minimax-t2a-async"},
        )
        data["audio_url"] = _to_public_url(file_path)

    return resp
