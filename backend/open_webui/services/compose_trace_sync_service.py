from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from open_webui.internal.db_n8n import get_n8n_db
from open_webui.models.hsai_compose_traces import HSAIComposeTraces

log = logging.getLogger(__name__)


DEFAULT_ENABLED = os.environ.get("HSAI_COMPOSE_TRACE_SYNC_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DEFAULT_INTERVAL_SECONDS = int(os.environ.get("HSAI_COMPOSE_TRACE_SYNC_INTERVAL_SECONDS", "5"))
DEFAULT_BATCH_SIZE = int(os.environ.get("HSAI_COMPOSE_TRACE_SYNC_BATCH_SIZE", "50"))


STAGE_PUBLISH_CONFIRMATION = "STATE_WAITING_PUBLISH_CONFIRMATION"
STAGE_SCRIPT_SELECTION = "STATE_WAITING_SCRIPT_SELECTION"


_URL_HINT_RE = re.compile(r"https?://[^\\s\\\"']+", re.IGNORECASE)


def _to_epoch_seconds(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp())
    try:
        return int(value)
    except Exception:
        return None


def _deep_find_stage_payloads(root: Any, stage_key: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    if isinstance(root, dict):
        for key, value in root.items():
            if key == stage_key and isinstance(value, dict):
                results.append(value)
            results.extend(_deep_find_stage_payloads(value, stage_key))
    elif isinstance(root, list):
        for item in root:
            results.extend(_deep_find_stage_payloads(item, stage_key))
    return results


def _choose_best_payload(stage_key: str, payloads: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not payloads:
        return None

    def score(payload: Dict[str, Any]) -> int:
        if stage_key == STAGE_PUBLISH_CONFIRMATION:
            return 100 if payload.get("oss_video_link") else 10
        if stage_key == STAGE_SCRIPT_SELECTION:
            points = 0
            if payload.get("视频脚本"):
                points += 50
            if payload.get("视频编号") is not None:
                points += 20
            if payload.get("视频链接"):
                points += 10
            return points
        return 1

    best = max(payloads, key=score)
    return best


def _extract_publish_confirmation(payload: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
    oss_url = payload.get("oss_video_link")
    extracted = {"final_video_url": oss_url} if oss_url else {}
    return (str(oss_url) if oss_url else None, extracted)


def _extract_script_selection(payload: Dict[str, Any]) -> Dict[str, Any]:
    extracted: Dict[str, Any] = {}
    if "视频编号" in payload:
        extracted["source_video_id"] = payload.get("视频编号")
    if "视频链接" in payload:
        extracted["source_video_url"] = payload.get("视频链接")
    shots = payload.get("视频脚本")
    if isinstance(shots, list):
        normalized = []
        for item in shots:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "category": item.get("category"),
                    "shot_type": item.get("shot_type"),
                    "scene_name": item.get("scene_name"),
                    "camera_move": item.get("camera_move"),
                    "camera_angle": item.get("camera_angle"),
                    "description": item.get("description"),
                    "dialogue_cn": item.get("chinese_dialogue"),
                    "dialogue_en": item.get("english_dialogue"),
                }
            )
        extracted["script_shots"] = normalized
    return extracted


def _find_any_oss_url(payload: Any) -> Optional[str]:
    """Fallback: scan payload strings for an OSS mp4-like url."""
    if payload is None:
        return None
    if isinstance(payload, str):
        if "oss-cn-" in payload and (".mp4" in payload.lower() or ".m3u8" in payload.lower()):
            return payload
        for m in _URL_HINT_RE.finditer(payload):
            url = m.group(0)
            if "oss-cn-" in url and (".mp4" in url.lower() or ".m3u8" in url.lower()):
                return url
        return None
    if isinstance(payload, dict):
        for v in payload.values():
            found = _find_any_oss_url(v)
            if found:
                return found
        return None
    if isinstance(payload, list):
        for v in payload:
            found = _find_any_oss_url(v)
            if found:
                return found
        return None
    return None


def _fetch_session_snapshot(session_id: str) -> Optional[Dict[str, Any]]:
    stmt = text(
        """
        SELECT
            session_id::text AS session_id,
            current_stage::text AS current_stage,
            status::text AS status,
            stages,
            updated_at
        FROM staff_main_flow_session_storage
        WHERE session_id = :sid
        LIMIT 1
        """
    )
    with get_n8n_db() as db:
        row = db.execute(stmt, {"sid": session_id}).mappings().first()
        return dict(row) if row else None


def _map_trace_status(n8n_status: Optional[str], has_final_video: bool) -> str:
    status = (n8n_status or "").upper()
    if has_final_video:
        return "ready_to_publish"
    if status in {"COMPLETED"}:
        return "completed"
    if status in {"FAILED"}:
        return "failed"
    if status in {"CANCELLED"}:
        return "cancelled"
    return "running"


def sync_trace_once(trace_id: str) -> bool:
    trace = HSAIComposeTraces.get_trace(trace_id)
    if not trace or not trace.n8n_session_id:
        return False

    snapshot = _fetch_session_snapshot(trace.n8n_session_id)
    if not snapshot:
        return False

    updated_at_epoch = _to_epoch_seconds(snapshot.get("updated_at"))
    if updated_at_epoch and trace.last_n8n_updated_at and updated_at_epoch <= trace.last_n8n_updated_at:
        return True

    stages = snapshot.get("stages")
    if not isinstance(stages, (dict, list)):
        stages = {}

    # 1) Script selection stage
    script_payloads = _deep_find_stage_payloads(stages, STAGE_SCRIPT_SELECTION)
    script_payload = _choose_best_payload(STAGE_SCRIPT_SELECTION, script_payloads)
    if script_payload:
        extracted = _extract_script_selection(script_payload)
        HSAIComposeTraces.upsert_step(
            trace_id,
            step_key="script_selection",
            stage_name=STAGE_SCRIPT_SELECTION,
            status="captured",
            raw_stage_json=script_payload,
            extracted_json=extracted,
            updated_at=updated_at_epoch or int(time.time()),
        )

    # 2) Publish confirmation stage -> final OSS link
    pub_payloads = _deep_find_stage_payloads(stages, STAGE_PUBLISH_CONFIRMATION)
    pub_payload = _choose_best_payload(STAGE_PUBLISH_CONFIRMATION, pub_payloads)
    final_url = None
    pub_extracted: Dict[str, Any] = {}
    if pub_payload:
        final_url, pub_extracted = _extract_publish_confirmation(pub_payload)
        if not final_url:
            final_url = _find_any_oss_url(pub_payload)
            if final_url:
                pub_extracted = {"final_video_url": final_url}

        step = HSAIComposeTraces.upsert_step(
            trace_id,
            step_key="publish_confirmation",
            stage_name=STAGE_PUBLISH_CONFIRMATION,
            status="captured",
            raw_stage_json=pub_payload,
            extracted_json=pub_extracted,
            updated_at=updated_at_epoch or int(time.time()),
        )
        if final_url:
            existing_final = HSAIComposeTraces.get_final_video_url(trace_id)
            if not existing_final or existing_final != final_url:
                HSAIComposeTraces.insert_artifact(
                    trace_id,
                    step_id=step.id,
                    artifact_type="final_video",
                    oss_url=final_url,
                    metadata_json=None,
                )

    has_final = bool(HSAIComposeTraces.get_final_video_url(trace_id))
    new_status = _map_trace_status(snapshot.get("status"), has_final)
    HSAIComposeTraces.set_trace_sync_state(
        trace_id,
        status=new_status,
        last_n8n_updated_at=updated_at_epoch,
    )
    return True


_TASK: Optional[asyncio.Task] = None
_STOP: Optional[asyncio.Event] = None


async def _runner_loop(interval_seconds: int, batch_size: int) -> None:
    global _STOP
    assert _STOP is not None
    while not _STOP.is_set():
        try:
            traces = HSAIComposeTraces.list_traces(status="running", limit=batch_size, offset=0)
            for trace in traces:
                try:
                    sync_trace_once(trace.trace_id)
                except Exception as exc:  # pylint: disable=broad-except
                    log.warning("ComposeTrace sync failed trace_id=%s err=%s", trace.trace_id, exc, exc_info=True)
        except Exception as exc:  # pylint: disable=broad-except
            log.warning("ComposeTrace sync loop error: %s", exc, exc_info=True)
        try:
            await asyncio.wait_for(_STOP.wait(), timeout=max(1, interval_seconds))
        except asyncio.TimeoutError:
            continue


async def start_compose_trace_sync() -> None:
    global _TASK, _STOP
    if not DEFAULT_ENABLED:
        log.info("ComposeTrace sync disabled via HSAI_COMPOSE_TRACE_SYNC_ENABLED.")
        return
    if _TASK and not _TASK.done():
        return
    _STOP = asyncio.Event()
    _TASK = asyncio.create_task(
        _runner_loop(DEFAULT_INTERVAL_SECONDS, DEFAULT_BATCH_SIZE),
        name="compose-trace-sync",
    )
    log.info(
        "ComposeTrace sync started interval=%ss batch=%s",
        DEFAULT_INTERVAL_SECONDS,
        DEFAULT_BATCH_SIZE,
    )


async def stop_compose_trace_sync() -> None:
    global _TASK, _STOP
    if _STOP:
        _STOP.set()
    if _TASK:
        try:
            await asyncio.wait_for(_TASK, timeout=5)
        except Exception:  # pragma: no cover
            pass
    _TASK = None
    _STOP = None
    log.info("ComposeTrace sync stopped.")

