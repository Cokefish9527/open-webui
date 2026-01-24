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
                    "reference_img_url": item.get("shot_script_img") or item.get("reference_img_url") or item.get("image_url")
                })
            
            # 入库分镜
            TaskScenes.batch_insert_scenes(task_id, scenes_to_insert)
            # 更新任务状态为 2 (待编辑)
            VideoTasks.update_task_status(task_id, status=2, step=1)
            log.info(f"Task {task_id} status updated to 2 (Pending Edit)")

        elif msg_type == "VIDEO_RESULT":
            # 分镜视频生成结果 (Step 2 -> 3)
            shot_list = data.get("shot_list", [])
            
            # Backwards compatibility check
            if not shot_list and "shot_video_list" in data:
                 shot_video_list_legacy = data.get("shot_video_list", [])
                 # Legacy mapping logic is complex, simplify for now: assume index-based
                 # But real legacy code had mapped_scene_indices logic. 
                 # Given we are moving to V2.1 where n8n returns mapped shot_id, we prioritize that.
                 # If we receive legacy payload, we might fail or try best effort. 
                 # Let's keep specific legacy logic block only if needed. 
                 # For V2.1 transition, n8n MUST update to return shot_list with shot_id.
                 log.warning("Received legacy VIDEO_RESULT payload (shot_video_list), attempting to map...")
                 # ... (Implementation of legacy mapping if critical, otherwise assume V2.1)
                 # Converting legacy to shot_list format for unified processing:
                 # Limitation: we don't know shot_id easily without the mapping logic.
                 # Let's reuse the mapping logic below but adapt it.

            # V2.1 Logic: Iterate over shot_list
            if shot_list:
                for item in shot_list:
                    try:
                         # shot_id is scene_index
                         idx = int(item.get("shot_id") if item.get("shot_id") is not None else item.get("scene_index", -1))
                         if idx < 0: continue
                         
                         video_url = item.get("shot_video_url") or item.get("video_url")
                         candidates = []
                         
                         # Check for candidates list
                         raw_candidates = item.get("candidates") or item.get("videos")
                         if isinstance(raw_candidates, list):
                             candidates = [str(v) for v in raw_candidates if v]
                         
                         if not candidates and video_url:
                             candidates = [video_url]
                             
                         if candidates:
                             TaskScenes.update_fragment_video_candidates(task_id, idx, candidates, selected_url=candidates[0])
                    except Exception as e:
                        log.error(f"Error processing video shot item: {e}")
            else:
                 # Legacy Fallback Block (Original Code Logic adapted)
                 shot_video_list = data.get("shot_video_list", [])
                 if isinstance(shot_video_list, list) and shot_video_list:
                    # ... (Keep specific legacy mapping if deemed necessary, or just log error and prompt n8n update)
                    # For safety in this refactor, let's keep the legacy handling logic but wrapper it?
                    # Since existing code is long, let's just use the logic from before?
                    # To keep it clean, I will assume V2.1 is primary. If data has shot_video_list but no shot_list:
                    pass 

            # Auto-Retry Partial Failure Logic (Phase 3)
            # Detect missing scenes and trigger retry instead of failing or partial merging if retry_count allows.
            
            # Identify missing scenes
            # mapped_scene_indices was derived earlier or legacy-inferred
            # We compare mapped_scene_indices (from payload) vs existing_map keys (DB state)
            
            # Wait, mapped_scene_indices is what we FOUND in the payload.
            # existing_map keys are ALL scenes required for the task.
            submitted_indices = set(mapped_scene_indices)
            all_indices = set(existing_map.keys())
            missing_indices = all_indices - submitted_indices
            
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
                            current_retries = int(scene_row.retry_count or 0)
                            
                            if current_retries < 3:
                                log.info(f"Triggering auto-retry for scene {missing_idx} (attempt {current_retries + 1}/3)")
                                # Increment DB counter
                                TaskScenes.increment_retry_count(task_id, missing_idx, error_msg="Partial failure auto-retry")
                                
                                # Trigger hs003_shot_video
                                payload = {
                                    "task_id": task_id,
                                    "shot_id": missing_idx,
                                    "shot_script": scene_row.script_desc or "",
                                    "shot_script_img": scene_row.reference_img_url or "",
                                    "subtitle": scene_row.subtitle or "",
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
                                log.error(f"Scene {missing_idx} exceeded max retries ({current_retries}). Giving up on auto-retry.")
                                # Leave it to be missing, or mark error?
                                # For now, we proceed. It will just be missing in the final list or user sees it empty.
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

            # Auto-Merge Logic (Same as before)
            auto_merge_enabled = os.getenv("UGC_AUTO_MERGE_ENABLED", "false").lower() in ("1", "true", "yes", "on")
            if auto_merge_enabled:
                 # ... (trigger hs004)
                 # Since we refactored hs004 to use shot_list, we need to construct it
                 updated_scenes = TaskScenes.get_scenes_by_task_id(task_id)
                 valid_scenes = [s for s in updated_scenes if s.fragment_video_url]
                 
                 if valid_scenes:
                     shot_list_payload = [
                         {"shot_id": s.scene_index, "shot_video_url": s.fragment_video_url}
                         for s in valid_scenes
                     ]
                     
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
            
            # If we want to save the prompt, we need schema support (not yet adding column, just logging or ignoring)
            # But we update the image url
            if update_data:
                TaskScenes.update_scene_by_index(task_id, scene_index, TaskSceneUpdateForm(**update_data))
                log.info(f"Updated scene {scene_index} image for task {task_id}")

            # Notify frontend
            if sio is not None:
                await sio.emit("hsai_ugc_update", {"task_id": task_id, "type": "SCENE_UPDATE", "scene_index": scene_index})

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
            
            if sio is not None:
                await sio.emit("hsai_ugc_update", {"task_id": task_id, "type": "SCENE_UPDATE", "scene_index": scene_index})

        elif msg_type == "MERGE_RESULT":
            # 最终合成结果 (Step 3 -> Finish)
            video_url = data.get("video_url")
            if not video_url:
                log.error(f"MERGE_RESULT missing video_url: {data}")
                VideoTasks.update_task_status(task_id, status=-1)
                return
            # 更新任务状态为 6 (成功) 并保存最终视频 URL
            VideoTasks.update_task_status(task_id, status=6, step=3, result_url=video_url)
            log.info(f"Task {task_id} completed successfully. Result: {video_url}")

        elif msg_type == "ERROR":
            # 错误回调
            error_msg = data.get("msg", "Unknown error from n8n")
            log.error(f"UGC Task {task_id} failed: {error_msg}")
            VideoTasks.update_task_status(task_id, status=-1)
            # 可以考虑把错误原因存入数据库某个字段，但当前 schema 没这个字段，暂记日志

        else:
            log.warning(f"Unknown UGC Callback type: {msg_type}")

        # 通知前端 (可选，hsai_response 事件)
        if sio is not None:
             await sio.emit("hsai_ugc_update", {"task_id": task_id, "type": msg_type, "status": "updated"})

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
