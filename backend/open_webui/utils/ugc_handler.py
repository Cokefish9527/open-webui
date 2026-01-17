import logging
import json
import time
import os
from typing import Dict, Any, Optional

from open_webui.models.hsai_ugc import VideoTasks, TaskScenes
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

        if not task_id or not msg_type:
            log.error(f"UGC Callback message missing task_id or type: {message}")
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
            subtitle_list = data.get("subtitle_list", [])
            shot_script_img_list = data.get("shot_script_img_list", [])
            shot_script_list = data.get("shot_script_list", []) # optional shot descriptions

            if not isinstance(subtitle_list, list) or not isinstance(shot_script_img_list, list) or not isinstance(shot_script_list, list):
                log.error(f"Invalid SCRIPT_RESULT payload types: {data}")
                VideoTasks.update_task_status(task_id, status=-1)
                return

            # 设计要求：长度一致性校验
            if len(shot_script_img_list) not in (0, len(subtitle_list)) or len(shot_script_list) not in (0, len(subtitle_list)):
                log.error(
                    f"SCRIPT_RESULT length mismatch: subtitle={len(subtitle_list)}, "
                    f"img={len(shot_script_img_list)}, script={len(shot_script_list)}"
                )
                VideoTasks.update_task_status(task_id, status=-1)
                return

            scenes_to_insert = []
            for i in range(len(subtitle_list)):
                scenes_to_insert.append({
                    "scene_index": i,
                    "subtitle": subtitle_list[i],
                    "script_desc": shot_script_list[i] if i < len(shot_script_list) else "",
                    "reference_img_url": shot_script_img_list[i] if i < len(shot_script_img_list) else ""
                })
            
            # 入库分镜
            TaskScenes.batch_insert_scenes(task_id, scenes_to_insert)
            # 更新任务状态为 2 (待编辑)
            VideoTasks.update_task_status(task_id, status=2, step=1)
            log.info(f"Task {task_id} status updated to 2 (Pending Edit)")

        elif msg_type == "VIDEO_RESULT":
            # 分镜视频生成结果 (Step 2 -> 3)
            shot_video_list = data.get("shot_video_list", [])
            if not isinstance(shot_video_list, list):
                log.error(f"Invalid VIDEO_RESULT payload type: {data}")
                VideoTasks.update_task_status(task_id, status=-1)
                return

            existing_scenes = TaskScenes.get_scenes_by_task_id(task_id)
            if len(existing_scenes) != len(shot_video_list):
                log.error(
                    f"VIDEO_RESULT length mismatch: existing={len(existing_scenes)}, returned={len(shot_video_list)}"
                )
                VideoTasks.update_task_status(task_id, status=-1)
                return

            # 支持每个分镜返回多个备选视频：
            # - 旧格式：shot_video_list = ["u1","u2",...]
            # - 新格式：shot_video_list = [["u1a","u1b"], ["u2a","u2b"], ...]
            selected_video_list = []
            for i, item in enumerate(shot_video_list):
                candidates = None
                if isinstance(item, list):
                    candidates = [str(v) for v in item if v]
                elif isinstance(item, str):
                    candidates = [item]
                elif isinstance(item, dict):
                    raw = item.get("candidates") or item.get("videos") or item.get("shot_video_candidates")
                    if isinstance(raw, list):
                        candidates = [str(v) for v in raw if v]
                    else:
                        url = item.get("video_url") or item.get("url")
                        candidates = [str(url)] if url else []
                else:
                    candidates = []

                if not candidates:
                    log.error(f"VIDEO_RESULT missing candidates for scene_index={i}: {item}")
                    VideoTasks.update_task_status(task_id, status=-1)
                    return

                selected_video_list.append(candidates[0])
                TaskScenes.update_fragment_video_candidates(task_id, i, candidates, selected_url=candidates[0])
            
            # 更新任务状态为 4 (待合成)
            VideoTasks.update_task_status(task_id, status=4, step=2)
            log.info(f"Task {task_id} status updated to 4 (Pending Merge)")

            # 是否自动触发合成（hs004）：
            # - 默认关闭：前端需展示分镜视频并让用户确认/选择后，再调用 /tasks/{task_id}/merge 触发合成；
            # - 若需要“一次调用自动到成片”，可显式设置 UGC_AUTO_MERGE_ENABLED=true。
            auto_merge_enabled = os.getenv("UGC_AUTO_MERGE_ENABLED", "false").lower() in ("1", "true", "yes", "on")
            if auto_merge_enabled:
                base_url = os.getenv("N8N_UGC_BASE_URL", "https://webhook-n8n.hsai.cc/webhook").strip().rstrip("/")
                url_hs004 = f"{base_url}/ugc_result"

                jarvis_key = os.getenv("JARVIS_API_KEY", "").strip()
                if not jarvis_key:
                    log.error("UGC auto-merge skipped: missing env JARVIS_API_KEY")
                    VideoTasks.update_task_status(task_id, status=-1)
                    return

                # 进入合成中
                VideoTasks.update_task_status(task_id, status=5, step=3)
                payload = {
                    "task_id": task_id,
                    # 自动合成仅使用每个分镜的默认选中项（第一个候选）。
                    "shot_video_list": selected_video_list,
                    "jarvis_api_key": jarvis_key,
                }
                status_code, _, _ = await post_json(url_hs004, payload)
                if status_code >= 400:
                    log.error(f"UGC auto-merge trigger failed: {status_code}")
                    VideoTasks.update_task_status(task_id, status=-1)
                    return
                log.info(f"UGC auto-merge triggered: task_id={task_id}")

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
