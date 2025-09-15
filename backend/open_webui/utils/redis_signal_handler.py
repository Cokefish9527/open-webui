"""
Redis信号处理器

监听Redis信号变化，处理n8n工作流的实时状态更新
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from redis import asyncio as aioredis

from open_webui.env import WEBSOCKET_REDIS_URL
from open_webui.socket.main import sio

log = logging.getLogger(__name__)

class RedisSignalHandler:
    """Redis信号处理器"""
    
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # 信号模式定义
        self.signal_patterns = {
            'workflow_status': 'n8n:workflow:status:*',
            'task_complete': 'n8n:task:complete:*',
            'video_synthesis': 'n8n:video:synthesis:*',
            'kpi_calculated': 'n8n:kpi:calculated:*'
        }
        
        # 信号处理映射
        self.signal_handlers = {
            'workflow_status': self._handle_workflow_status,
            'task_complete': self._handle_task_complete,
            'video_synthesis': self._handle_video_synthesis,
            'kpi_calculated': self._handle_kpi_calculated
        }
    
    async def initialize(self):
        """初始化Redis连接"""
        try:
            if WEBSOCKET_REDIS_URL:
                self.redis_client = aioredis.from_url(WEBSOCKET_REDIS_URL)
                log.info("Redis信号处理器初始化成功")
            else:
                log.warning("未配置Redis URL，Redis信号处理器无法初始化")
        except Exception as e:
            log.error(f"Redis信号处理器初始化失败: {e}")
    
    async def start_monitoring(self):
        """开始监听Redis信号"""
        if self.is_monitoring or not self.redis_client:
            return
            
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        log.info("Redis信号监听已启动")
    
    async def stop_monitoring(self):
        """停止监听Redis信号"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        log.info("Redis信号监听已停止")
    
    async def _monitoring_loop(self):
        """监听循环"""
        try:
            # 创建pubsub连接
            self.pubsub = self.redis_client.pubsub()
            
            # 订阅所有信号模式
            for pattern in self.signal_patterns.values():
                await self.pubsub.psubscribe(pattern)
            
            log.info("已订阅Redis信号频道")
            
            # 监听消息
            async for message in self.pubsub.listen():
                if not self.is_monitoring:
                    break
                    
                if message['type'] == 'pmessage':
                    await self._handle_signal(message)
                    
        except asyncio.CancelledError:
            log.info("Redis信号监听循环被取消")
        except Exception as e:
            log.error(f"Redis信号监听循环出错: {e}")
        finally:
            if self.pubsub:
                await self.pubsub.close()
    
    async def _handle_signal(self, message):
        """处理Redis信号"""
        try:
            channel = message['channel'].decode('utf-8')
            data = json.loads(message['data'].decode('utf-8'))
            
            log.info(f"接收到Redis信号: {channel}")
            
            # 根据频道类型调用相应的处理函数
            for signal_type, pattern in self.signal_patterns.items():
                if pattern.rstrip('*') in channel:
                    handler = self.signal_handlers.get(signal_type)
                    if handler:
                        await handler(data)
                    break
                    
        except Exception as e:
            log.error(f"处理Redis信号时出错: {e}")
    
    async def _handle_workflow_status(self, data: Dict[str, Any]):
        """处理工作流状态更新信号"""
        try:
            user_id = data.get('user_id')
            execution_id = data.get('execution_id')
            status = data.get('status')
            progress = data.get('progress', 0)
            message = data.get('message', '')
            
            if user_id:
                # 通过Socket.IO向前端发送状态更新
                await sio.emit('workflow_status', {
                    'type': 'workflow_status',
                    'execution_id': execution_id,
                    'status': status,
                    'progress': progress,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }, room=f'user_{user_id}')
                
                log.info(f"已发送工作流状态更新给用户 {user_id}: {status} ({progress}%)")
                
        except Exception as e:
            log.error(f"处理工作流状态信号时出错: {e}")
    
    async def _handle_task_complete(self, data: Dict[str, Any]):
        """处理任务完成信号"""
        try:
            user_id = data.get('user_id')
            task_id = data.get('task_id')
            task_result = data.get('result')
            kpi_data = data.get('kpi_data', {})
            
            if user_id:
                # 发送任务完成通知
                await sio.emit('task_complete', {
                    'type': 'task_complete',
                    'task_id': task_id,
                    'result': task_result,
                    'kpi_data': kpi_data,
                    'timestamp': datetime.now().isoformat()
                }, room=f'user_{user_id}')
                
                log.info(f"已发送任务完成通知给用户 {user_id}: {task_id}")
                
        except Exception as e:
            log.error(f"处理任务完成信号时出错: {e}")
    
    async def _handle_video_synthesis(self, data: Dict[str, Any]):
        """处理视频合成信号"""
        try:
            user_id = data.get('user_id')
            video_id = data.get('video_id')
            status = data.get('status')
            progress = data.get('progress', 0)
            video_url = data.get('video_url', '')
            
            if user_id:
                # 发送视频合成状态更新
                await sio.emit('video_synthesis', {
                    'type': 'video_synthesis',
                    'video_id': video_id,
                    'status': status,
                    'progress': progress,
                    'video_url': video_url,
                    'timestamp': datetime.now().isoformat()
                }, room=f'user_{user_id}')
                
                log.info(f"已发送视频合成状态给用户 {user_id}: {video_id} - {status}")
                
        except Exception as e:
            log.error(f"处理视频合成信号时出错: {e}")
    
    async def _handle_kpi_calculated(self, data: Dict[str, Any]):
        """处理KPI计算完成信号"""
        try:
            user_id = data.get('user_id')
            kpi_data = data.get('kpi_data', {})
            calculation_time = data.get('calculation_time', '')
            
            if user_id:
                # 发送KPI计算完成通知
                await sio.emit('kpi_update', {
                    'type': 'kpi_update',
                    'kpi_data': kpi_data,
                    'calculation_time': calculation_time,
                    'timestamp': datetime.now().isoformat()
                }, room=f'user_{user_id}')
                
                log.info(f"已发送KPI更新给用户 {user_id}")
                
        except Exception as e:
            log.error(f"处理KPI计算信号时出错: {e}")

# 全局Redis信号处理器实例
redis_signal_handler = RedisSignalHandler()