import logging
import json
import time
import os
from typing import Dict, Any, Optional

from open_webui.models.hsai_ugc import VideoTasks, TaskScenes, CallbackLogs
from open_webui.socket.main import sio
from open_webui.services.workflow_meta_update_service import post_json

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def _log_ws_ugc_update(payload: Dict[str, Any]) -> None:
    """
    Log a compact, non-sensitive summary for the UGC websocket event.

    Note: Avoid logging full payload (may include long strings / URLs).
    """
    try:
        scenes = payload.get("scenes")
        scenes_len = None
        scene_index_hint = None

        if scenes is None:
            scenes_len = None
        elif isinstance(scenes, list):
            scenes_len = len(scenes)
            if scenes_len == 1 and isinstance(scenes[0], dict):
                scene_index_hint = scenes[0].get("scene_index")
        else:
            # Unexpected shape; keep it simple.
            scenes_len = -1

        log.info(
            "UGC WS emit hsai_ugc_update: task_id=%s status=%s step=%s progress_percent=%s scenes_len=%s scene_index=%s error=%s",
            payload.get("task_id"),
            payload.get("status"),
            payload.get("step"),
            payload.get("progress_percent"),
            scenes_len,
            scene_index_hint,
            bool(payload.get("error_msg")),
        )
    except Exception as e:
        log.debug("UGC WS emit log failed: %s", e)



async def handle_ugc_callback(message: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> None:
    """
    处理 UGC 视频生成回调消息
    """
    try:
        task_id = message.get("task_id")
        msg_type = message.get("type")
        data = message.get("data", {})

        # 1. Persistent Logging (Step 15: Debugging)
        log_entry = None
        try:
             log_entry = CallbackLogs.insert_log(message, task_id=task_id, msg_type=msg_type)
        except Exception as e:
            log.error(f"Failed to persist UGC callback log: {e}")

        # 2. Type Inference (Fix for missing type in n8n payload)
        if not msg_type and data:
            if "shot_list" in data and msg_type not in ["SCRIPT_RESULT", "VIDEO_RESULT", "SCRIPT_SHOT_IMG_RESULT", "SHOT_VIDEO_RESULT"]:
                 # Ambiguous: could be SCRIPT or VIDEO result if type is missing.
                 # Heuristic: check inner fields
                 first_shot = data["shot_list"][0] if len(data["shot_list"]) > 0 else {}
                 if "shot_video_url" in first_shot:
                     msg_type = "VIDEO_RESULT"
                 else:
                     msg_type = "SCRIPT_RESULT"
                 log.warning(f"Inferred msg_type='{msg_type}' for task_id={task_id}")
            elif "video_url" in data:
                msg_type = "MERGE_RESULT"
                log.warning(f"Inferred msg_type='MERGE_RESULT' for task_id={task_id}")

        if not task_id or not msg_type:
            error_msg = f"UGC Callback message missing task_id or type: {message}"
            log.error(error_msg)
            # Optionally update log_entry with error
            return

        task = VideoTasks.get_task_by_id(task_id)
        if not task:
            log.error(f"UGC Callback task not found: task_id={task_id}")
            return
        if int(task.status or 0) == -2:
            log.info(f"UGC Callback ignored (task closed): task_id={task_id}, type={msg_type}")
            return

        log.info(f"Processing UGC Callback: task_id={task_id}, type={msg_type}")

        if msg_type == "SCRIPT_RESULT":
            # 脚本生成结果 (Step 1 -> 2)
            shot_list = data.get("shot_list", [])
            if not isinstance(shot_list, list):
                # Backwards compatibility for old payload
                subtitle_list = data.get("subtitle_list", [])
                shot_script_img_list = data.get("shot_script_img_list", [])
                shot_script_list = data.get("shot_script_list", [])
                if subtitle_list:
                     shot_list = []
                     for i in range(len(subtitle_list)):
                         shot_list.append({
                             "shot_id": i,
                             "subtitle": subtitle_list[i],
                             "shot_script": shot_script_list[i] if i < len(shot_script_list) else "",
                             "shot_script_img": shot_script_img_list[i] if i < len(shot_script_img_list) else ""
                         })
                else:
                    log.error(f"Invalid SCRIPT_RESULT payload type: {data}")
                    VideoTasks.update_task_status(task_id, status=-1)
                    return

            scenes_to_insert = []
            for item in shot_list:
                # shot_id from n8n might be mapped to scene_index or just an index
                # Here we assume it corresponds to scene_index
                try:
                    idx = int(item.get("shot_id") if item.get("shot_id") is not None else item.get("scene_index", 0))
                except:
                    idx = len(scenes_to_insert)

                scenes_to_insert.append({
                    "scene_index": idx,
                    "subtitle": item.get("subtitle"),
                    "script_desc": item.get("shot_script") or item.get("script_desc"),
                    "script_desc": item.get("shot_script") or item.get("script_desc"),
                    "reference_img_url": item.get("shot_script_img") or item.get("reference_img_url") or item.get("image_url"),
                    "image_prompt": item.get("image_prompt") or item.get("prompt")
                })
            
            # 入库分镜
            TaskScenes.batch_insert_scenes(task_id, scenes_to_insert)
            # 更新任务状态为 2 (待编辑)
            VideoTasks.update_task_status(task_id, status=2, step=1)
            # 更新任务状态为 2 (待编辑)
            VideoTasks.update_task_status(task_id, status=2, step=1)
            log.info(f"Task {task_id} status updated to 2 (Pending Edit)")
            
            # Fetch updated scenes for full structure
            updated_scenes = TaskScenes.get_scenes_by_task_id(task_id)
            if sio is not None:
                payload = {
                    "task_id": task_id, 
                    "status": 2, 
                    "step": 1,
                    "progress_percent": 35,
                    "result_video_url": None,
                    "scenes": [s.model_dump() for s in (updated_scenes or [])],
                    "error_msg": None
                }
                _log_ws_ugc_update(payload)
                await sio.emit("hsai_ugc_update", payload)

        elif msg_type == "VIDEO_RESULT":
            # 分镜视频生成结果 (Step 2 -> 3)
            shot_list = data.get("shot_list") or []
            
            # Backwards compatibility check
            if not shot_list and "shot_video_list" in data:
                 shot_video_list_legacy = data.get("shot_video_list", []) or []
                 log.warning("Received legacy VIDEO_RESULT payload (shot_video_list), attempting to map...")
                 # Legacy format: list aligned by scene_index.
                 shot_list = [
                     {"shot_id": idx, "shot_video_url": url}
                     for idx, url in enumerate(shot_video_list_legacy)
                     if url
                 ]

            submitted_indices = set()
            if isinstance(shot_list, list) and shot_list:
                for item in shot_list:
                    try:
                        idx = int(
                            item.get("shot_id")
                            if item.get("shot_id") is not None
                            else item.get("scene_index", -1)
                        )
                        if idx < 0:
                            continue
                        submitted_indices.add(idx)

                        video_url = item.get("shot_video_url") or item.get("video_url")
                        candidates = []

                        raw_candidates = item.get("candidates") or item.get("videos")
                        if isinstance(raw_candidates, list):
                            candidates = [str(v) for v in raw_candidates if v]

                        if not candidates and video_url:
                            candidates = [video_url]

                        if candidates:
                            TaskScenes.update_fragment_video_candidates(
                                task_id, idx, candidates, selected_url=candidates[0]
                            )
                    except Exception as e:
                        log.error(f"Error processing video shot item: {e}")

            # Auto-Retry Partial Failure Logic (Phase 3)
            # Detect missing scenes and trigger retry instead of failing or partial merging if retry_count allows.
            existing_map = {}
            try:
                for s in TaskScenes.get_scenes_by_task_id(task_id) or []:
                    si = getattr(s, "scene_index", None)
                    if si is not None:
                        existing_map[int(si)] = s
            except Exception:
                existing_map = {}

            missing_indices = set(existing_map.keys()) - set(submitted_indices)
            
            # Also check for empty video URLs in the returned list
            # If payload has entry but URL is empty, treating as "failed" generation for that shot?
            # Current logic: selected_video_list contains candidates. If candidates was empty, we errored out above.
            # But let's say we have 3 scenes, returned 2. 'missing_indices' covers it.
            
            retry_triggered = False
            
            if missing_indices:
                log.warning(f"VIDEO_RESULT missing scenes: {missing_indices} for task {task_id}")
                
                # Check retry counts and trigger retries
                from open_webui.routers.hsai_ugc import URL_HS003_SHOT_VIDEO, _get_sharded_api_key, _require_env, _resolve_minimax_credentials
                from open_webui.models.hsai_ugc import MaterialModels
                
                # We need context to trigger retry (model, creds)
                # Load context once optimization
                task_ctx = VideoTasks.get_task_by_id(task_id)
                model_ctx = MaterialModels.get_model_by_id_and_user_id(int(task_ctx.model_id), task_ctx.user_id) if task_ctx else None
                
                if task_ctx and model_ctx:
                    try:
                        # Shared credentials resolution
                        minimax_creds = _resolve_minimax_credentials(
                            getattr(model_ctx, "minimax_account_id", None),
                            require_group=True,
                            allow_env_fallback=True,
                        )
                        run_hub_key = _require_env("RUNNINGHUB_API_KEY")
                        run_hub_wid = _require_env("RUNNINGHUB_WORKFLOW_ID")
                        jarvis_key = _get_sharded_api_key(1) # Key #2 for video
                        
                        for missing_idx in missing_indices:
                            scene_row = existing_map[missing_idx]
                            retry_count = int(TaskScenes.increment_retry_count(task_id, missing_idx, error_msg="Partial failure auto-retry") or 0)

                            if 0 < retry_count <= 3:
                                log.info(f"Triggering auto-retry for scene {missing_idx} (attempt {retry_count}/3)")
                                
                                # Trigger hs003_shot_video
                                payload = {
                                    "task_id": task_id,
                                    "shot_id": missing_idx,
                                    "shot_script": getattr(scene_row, "script_desc", "") or "",
                                    "shot_script_img": getattr(scene_row, "reference_img_url", "") or "",
                                    "subtitle": getattr(scene_row, "subtitle", "") or "",
                                    "jarvis_api_key": jarvis_key,
                                    "minimax_key": minimax_creds["api_key"],
                                    "minimax_group": minimax_creds["group_id"],
                                    "runninghub_api_key": run_hub_key,
                                    "runninghub_workflow_id": run_hub_wid,
                                }
                                # Fire and forget (async check)
                                await post_json(URL_HS003_SHOT_VIDEO, payload)
                                retry_triggered = True
                            else:
                                log.error(f"Scene {missing_idx} exceeded max retries ({retry_count}). Giving up on auto-retry.")
                                TaskScenes.increment_retry_count(task_id, missing_idx, error_msg="Max retries exceeded")

                    except Exception as exc:
                        log.error(f"Failed to prepare auto-retry context: {exc}")
            
            # If we triggered retries, DO NOT advance status to 4 yet.
            # We stay in status 3 (Rendering). Wait for SHOT_VIDEO_RESULT to fill the gaps.
            if retry_triggered:
                log.info(f"Task {task_id} staying in status 3 (RENDERING) waiting for auto-retries.")
                return

            # If no retries triggered (all good OR max retries exceeded), proceed to status 4.
            # 更新任务状态为 4 (待合成)
            VideoTasks.update_task_status(task_id, status=4, step=2)
            log.info(f"Task {task_id} status updated to 4 (Pending Merge)")
            
            # Fetch all scenes for full structure (like SCRIPT_RESULT)
            all_scenes = TaskScenes.get_scenes_by_task_id(task_id)
            if sio is not None:
                payload = {
                    "task_id": task_id, 
                    "status": 4, 
                    "step": 2,
                    "progress_percent": 85,
                    "result_video_url": None,
                    "scenes": [s.model_dump() for s in (all_scenes or [])],
                    "error_msg": None
                }
                _log_ws_ugc_update(payload)
                await sio.emit("hsai_ugc_update", payload)

            # Auto-Merge Logic (Same as before)
            auto_merge_enabled = os.getenv("UGC_AUTO_MERGE_ENABLED", "false").lower() in ("1", "true", "yes", "on")
            if auto_merge_enabled:
                 # Construct hs004 payload from callback data (prefer this over DB reads).
                 shot_list_payload = []
                 if isinstance(shot_list, list):
                     for item in shot_list:
                         try:
                             idx = int(
                                 item.get("shot_id")
                                 if item.get("shot_id") is not None
                                 else item.get("scene_index", -1)
                             )
                         except Exception:
                             continue
                         if idx < 0:
                             continue
                         url = item.get("shot_video_url") or item.get("video_url")
                         if url:
                             shot_list_payload.append({"shot_id": idx, "shot_video_url": url})

                 if shot_list_payload:
                     
                     base_url = os.getenv("N8N_UGC_BASE_URL", "https://webhook-n8n.hsai.cc/webhook").strip().rstrip("/")
                     url_hs004 = f"{base_url}/ugc_result"
                     jarvis_key = os.getenv("JARVIS_API_KEY", "").strip()
                     
                     VideoTasks.update_task_status(task_id, status=5, step=3)
                     payload = {
                        "task_id": task_id,
                        "shot_list": shot_list_payload,
                        "jarvis_api_key": jarvis_key,
                     }
                     try:
                        await post_json(url_hs004, payload)
                     except:
                        pass

        elif msg_type == "SCRIPT_SHOT_IMG_RESULT":
            # 单分镜图片重绘结果
            shot_list = data.get("shot_list", [])
            if not shot_list:
                log.warning(f"SCRIPT_SHOT_IMG_RESULT missing shot_list for task {task_id}")
                return

            item = shot_list[0] # Should only be one
            scene_index = int(item.get("shot_id") if item.get("shot_id") is not None else -1)
            if scene_index < 0:
                log.error(f"Invalid shot_id in SCRIPT_SHOT_IMG_RESULT: {item}")
                return
            
            # Update specific scene
            from open_webui.models.hsai_ugc import TaskSceneUpdateForm
            
            img_url = item.get("shot_script_img") or item.get("image_url") or item.get("reference_img_url")
            prompt = item.get("image_prompt")
            
            update_data = {}
            if img_url: update_data["reference_img_url"] = img_url
            if img_url: update_data["reference_img_url"] = img_url
            if prompt: update_data["image_prompt"] = prompt
            
            # If we want to save the prompt, we need schema support (not yet adding column, just logging or ignoring)
            # But we update the image url
            if update_data:
                TaskScenes.update_scene_by_index(task_id, scene_index, TaskSceneUpdateForm(**update_data))
                log.info(f"Updated scene {scene_index} image for task {task_id}")

            # Notify frontend with single scene update
            updated_scene = TaskScenes.get_scene_by_index(task_id, scene_index)
            task_curr = VideoTasks.get_task_by_id(task_id)
            if sio is not None and updated_scene and task_curr:
                payload = {
                    "task_id": task_id, 
                    "status": int(task_curr.status or 0),
                    "step": int(task_curr.step or 0),
                    "progress_percent": int(task_curr.progress_percent or 0),
                    "result_video_url": task_curr.result_video_url,
                    "scenes": [updated_scene.model_dump()],
                    "error_msg": None
                }
                _log_ws_ugc_update(payload)
                await sio.emit("hsai_ugc_update", payload)

        elif msg_type == "SHOT_VIDEO_RESULT":
            # 单分镜视频重生成结果
            shot_list = data.get("shot_list", [])
            if not shot_list:
                log.warning(f"SHOT_VIDEO_RESULT missing shot_list for task {task_id}")
                return

            item = shot_list[0]
            scene_index = int(item.get("shot_id") if item.get("shot_id") is not None else -1)
            if scene_index < 0: return

            video_url = item.get("shot_video_url") or item.get("video_url")
            if video_url:
                 # Update candidates (replace or append? Logic implies this is the "new" result)
                 # Simple approach: set as selected
                 TaskScenes.update_fragment_video_candidates(task_id, scene_index, [video_url], selected_url=video_url)
                 log.info(f"Updated scene {scene_index} video for task {task_id}")
                 
                 # Logic for Phase 3 Auto-Retry Completion Check
                 # If task is in status 3 (RENDERING), check if this was the last missing piece.
                 task_curr = VideoTasks.get_task_by_id(task_id)
                 if task_curr and int(task_curr.status or 0) == 3:
                     all_scenes = TaskScenes.get_scenes_by_task_id(task_id)
                     # Check if ALL scenes have a fragment_video_url now
                     if all(s.fragment_video_url for s in all_scenes):
                         log.info(f"All scenes completed via retry for task {task_id}. Advancing to status 4.")
                         VideoTasks.update_task_status(task_id, status=4, step=2)
            
            # Notify frontend with single scene update
            updated_scene = TaskScenes.get_scene_by_index(task_id, scene_index)
            task_curr_ws = VideoTasks.get_task_by_id(task_id)
            if sio is not None and updated_scene and task_curr_ws:
                payload = {
                    "task_id": task_id, 
                    "status": int(task_curr_ws.status or 0),
                    "step": int(task_curr_ws.step or 0),
                    "progress_percent": int(task_curr_ws.progress_percent or 0),
                    "result_video_url": task_curr_ws.result_video_url,
                    "scenes": [updated_scene.model_dump()],
                    "error_msg": None
                }
                _log_ws_ugc_update(payload)
                await sio.emit("hsai_ugc_update", payload)

        elif msg_type == "MERGE_RESULT":
            # 最终合成结果 (Step 3 -> Finish)
            video_url = data.get("video_url")
            if not video_url:
                log.error(f"MERGE_RESULT missing video_url: {data}")
                VideoTasks.update_task_status(task_id, status=-1)
                return
            # 更新任务状态为 6 (成功) 并保存最终视频 URL
            VideoTasks.update_task_status(task_id, status=6, step=3, result_url=video_url)
            VideoTasks.update_task_status(task_id, status=6, step=3, result_url=video_url)
            log.info(f"Task {task_id} completed successfully. Result: {video_url}")
            
            if sio is not None:
                payload = {
                    "task_id": task_id, 
                    "status": 6, 
                    "step": 3,
                    "progress_percent": 100,
                    "result_video_url": video_url,
                    "scenes": None,
                    "error_msg": None
                }
                _log_ws_ugc_update(payload)
                await sio.emit("hsai_ugc_update", payload)

        elif msg_type == "ERROR":
            # 错误回调
            error_msg = data.get("msg", "Unknown error from n8n")
            log.error(f"UGC Task {task_id} failed: {error_msg}")
            VideoTasks.update_task_status(task_id, status=-1)
            
            # Push error event to frontend
            task_curr_err = VideoTasks.get_task_by_id(task_id)
            if sio is not None and task_curr_err:
                payload = {
                    "task_id": task_id,
                    "status": -1,
                    "step": int(task_curr_err.step or 0),
                    "progress_percent": 0,
                    "result_video_url": None,
                    "scenes": None,
                    "error_msg": error_msg
                }
                _log_ws_ugc_update(payload)
                await sio.emit("hsai_ugc_update", payload)

        else:
            log.warning(f"Unknown UGC Callback type: {msg_type}")

        # 通知前端 (可选，hsai_response 事件) - 已在各分支处理，此处不再通用发送
        # if sio is not None:
        #      await sio.emit("hsai_ugc_update", {"task_id": task_id, "type": msg_type, "status": "updated"})

    except Exception as e:
        log.error(f"Error handling UGC callback: {e}", exc_info=True)

def register_ugc_handler(redis_signal_handler) -> None:
    """
    注册 UGC 消息队列处理器
    """
    redis_signal_handler.register_handler(
        "ugc_callback_queue",
        handle_ugc_callback,
        {
            "timeout": 60,
            "max_retry": 3
        }
    )
    log.info("Registered UGC Callback handler for queue: ugc_callback_queue")
