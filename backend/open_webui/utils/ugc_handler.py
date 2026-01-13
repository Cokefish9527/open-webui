import logging
import json
import time
from typing import Dict, Any, Optional

from open_webui.models.hsai_ugc import VideoTasks, TaskScenes
from open_webui.socket.main import sio

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

            for i, video_url in enumerate(shot_video_list):
                TaskScenes.update_fragment_video_url(task_id, i, video_url)
            
            # 更新任务状态为 4 (待合成)
            VideoTasks.update_task_status(task_id, status=4, step=2)
            log.info(f"Task {task_id} status updated to 4 (Pending Merge)")

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
