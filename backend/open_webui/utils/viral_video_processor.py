import json
import time
import logging
from typing import Dict, Any, Optional, Tuple, Union, List
import redis
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from open_webui.models.hsai_viral_videos import HSAIViralVideos, HSAIViralVideoStatus
from open_webui.models.hsai_tasks import HSAITasks, HSAITaskStatus, HSAITaskType
from open_webui.utils.redis_signal_handler import get_redis_client

# 配置日志
log = logging.getLogger(__name__)

__all__ = ['ViralVideoProcessor', 'start_viral_video_processor']


class ViralVideoProcessor:
    """爆款视频处理器，负责从Redis队列读取消息并处理任务表数据添加"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.redis_client = get_redis_client()
        self.main_queue_key = "viral_video_crawled_notification"
        self.processing_queue_key = "viral_video_processing"
        self.dead_letter_queue_key = "viral_video_dead_letter"
        self.max_retry_count = 3
        
    def start_processing(self):
        """启动视频处理循环"""
        log.info("启动爆款视频处理器...")
        while True:
            try:
                # 从主队列阻塞式读取消息
                message_data = self.redis_client.brpop([self.main_queue_key], timeout=30)
                if message_data:
                    # 确保返回的是元组类型
                    if isinstance(message_data, (list, tuple)) and len(message_data) == 2:
                        _, message_json = message_data
                        self._process_message(message_json)
                else:
                    # 超时继续循环
                    continue
            except Exception as e:
                log.error(f"处理视频消息时发生错误: {e}")
                time.sleep(5)  # 出错时短暂休眠
                
    def _process_message(self, message_json: bytes):
        """处理单条消息"""
        try:
            # 解析消息
            message = json.loads(message_json.decode('utf-8'))
            log.info(f"收到视频抓取通知消息: {message.get('video_url', '未知URL')}")
            
            # 备份消息到处理队列
            self._backup_message(message_json)
            
            # 处理视频数据添加
            success = self._handle_video_creation(message)
            
            if success:
                # 处理成功，从队列中删除消息
                self._remove_processed_message(message_json)
                log.info(f"视频消息处理成功: {message.get('video_url', '未知URL')}")
            else:
                # 处理失败，增加重试次数或放入死信队列
                self._handle_processing_failure(message, message_json)
                
        except json.JSONDecodeError as e:
            log.error(f"消息JSON解析失败: {e}")
            self._move_to_dead_letter_queue(message_json, "JSON解析失败")
        except Exception as e:
            log.error(f"处理消息时发生未知错误: {e}")
            self._handle_processing_failure(
                {"error_message": str(e)}, 
                message_json
            )
            
    def _backup_message(self, message_json: bytes):
        """备份消息到处理队列"""
        try:
            self.redis_client.lpush(self.processing_queue_key, message_json)
            log.debug("消息已备份到处理队列")
        except Exception as e:
            log.warning(f"备份消息到处理队列失败: {e}")
            
    def _remove_processed_message(self, message_json: bytes):
        """从队列中删除已处理的消息"""
        try:
            # 从主队列删除（理论上已经通过brpop取出了）
            # 从处理队列删除
            self.redis_client.lrem(self.processing_queue_key, 1, message_json.decode('utf-8'))
            log.debug("已处理消息已从队列中删除")
        except Exception as e:
            log.warning(f"删除已处理消息失败: {e}")
            
    def _handle_video_creation(self, message: Dict[str, Any]) -> bool:
        """处理视频数据添加"""
        try:
            # 开始数据库事务
            self.db_session.begin()
            
            try:
                # 创建视频记录
                video_data = {
                    "video_url": message.get("video_url", ""),
                    "title": message.get("video_title", ""),
                    "description": message.get("video_description", ""),
                    "thumbnail_url": message.get("thumbnail_url", ""),
                    "duration": message.get("duration", 0),
                    "platform": message.get("platform", ""),
                    "tags": message.get("tags", []),
                    "metadata": message.get("metadata", {}),
                    "status": HSAIViralVideoStatus.PENDING,
                    "is_learned": False,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time())
                }
                
                # 检查视频是否已存在
                existing_video = HSAIViralVideos.get_video_by_url(video_data["video_url"])
                if existing_video:
                    # 更新现有视频记录
                    video = HSAIViralVideos.update_video_by_id(
                        existing_video.id, 
                        video_data
                    )
                    video_id = existing_video.id
                else:
                    # 创建新视频记录
                    video = HSAIViralVideos.insert_new_video(video_data)
                    video_id = video.id if video else None
                
                # 提交事务
                self.db_session.commit()
                log.info(f"成功创建视频记录，视频ID: {video_id}")
                return True
                
            except Exception as e:
                # 回滚事务
                self.db_session.rollback()
                log.error(f"数据库操作失败: {e}")
                return False
                
        except SQLAlchemyError as e:
            log.error(f"数据库连接错误: {e}")
            return False
        except Exception as e:
            log.error(f"视频创建过程中发生错误: {e}")
            return False
            
    def _handle_processing_failure(self, message: Dict[str, Any], message_json: bytes):
        """处理消息处理失败"""
        try:
            # 增加重试次数
            retry_count = message.get("retry_count", 0) + 1
            message["retry_count"] = retry_count
            
            if retry_count < self.max_retry_count:
                # 重新放回主队列
                updated_message_json = json.dumps(message, ensure_ascii=False).encode('utf-8')
                self.redis_client.lpush(self.main_queue_key, updated_message_json)
                log.warning(f"消息处理失败，已重新入队，重试次数: {retry_count}")
            else:
                # 放入死信队列
                error_msg = message.get("error_message", "达到最大重试次数")
                self._move_to_dead_letter_queue(message_json, error_msg)
                log.error(f"消息处理失败且达到最大重试次数，已移至死信队列: {error_msg}")
                
        except Exception as e:
            log.error(f"处理失败消息时发生错误: {e}")
            self._move_to_dead_letter_queue(message_json, f"处理失败: {str(e)}")
            
    def _move_to_dead_letter_queue(self, message_json: bytes, reason: str):
        """将消息移至死信队列"""
        try:
            # 创建死信消息
            dead_letter_message = {
                "original_message": message_json.decode('utf-8'),
                "failure_reason": reason,
                "moved_at": int(time.time())
            }
            dead_letter_json = json.dumps(dead_letter_message, ensure_ascii=False).encode('utf-8')
            
            self.redis_client.lpush(self.dead_letter_queue_key, dead_letter_json)
            log.info(f"消息已移至死信队列，原因: {reason}")
        except Exception as e:
            log.error(f"移至死信队列失败: {e}")

# 工具函数
def start_viral_video_processor(db_session: Session):
    """启动爆款视频处理器"""
    processor = ViralVideoProcessor(db_session)
    processor.start_processing()