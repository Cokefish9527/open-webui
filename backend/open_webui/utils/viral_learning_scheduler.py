"""
爆款学习工作流定时调度器

实现爆款学习工作流的循环调用策略和定时控制
"""

import asyncio
import logging
import time
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from open_webui.config.n8n_workflows import (
    N8NWorkflowType, 
    get_workflow_config,
    get_viral_learning_schedule_config,
    N8N_WORKFLOW_WEBHOOKS
)

log = logging.getLogger(__name__)

class ViralLearningScheduler:
    """爆款学习工作流定时调度器"""
    
    def __init__(self):
        self.config = get_viral_learning_schedule_config()
        self.workflow_config = get_workflow_config(N8NWorkflowType.VIRAL_LEARNING)
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.execution_count = 0
        self.daily_execution_count = 0
        self.last_execution_date = None
        self.last_execution_time = None
        self.failed_attempts = 0
        
    async def start(self):
        """启动定时调度器"""
        if self.is_running:
            log.warning("Viral learning scheduler is already running")
            return
            
        # 检查配置是否启用调度器
        if not self.config.get("enabled", False):
            log.info("Viral learning scheduler is disabled (enabled=false or empty config)")
            return
            
        # 验证必要的配置项
        if self.config.get("interval_minutes", 0) <= 0:
            log.warning("Viral learning scheduler disabled due to invalid interval_minutes")
            return
            
        self.is_running = True
        self.task = asyncio.create_task(self._schedule_loop())
        log.info(f"Viral learning scheduler started with {self.config['interval_minutes']} minutes interval")
    
    async def stop(self):
        """停止定时调度器"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        log.info("Viral learning scheduler stopped")
    
    async def _schedule_loop(self):
        """主调度循环"""
        # 等待第一个调度周期，而不是立即执行
        interval_seconds = self.config["interval_minutes"] * 60
        log.debug(f"Waiting {interval_seconds}s for first execution cycle")
        await asyncio.sleep(interval_seconds)
        
        while self.is_running:
            try:
                # 检查是否在工作时间内
                if not self._is_working_hours():
                    log.debug("Outside working hours, waiting 60s")
                    await asyncio.sleep(60)  # 非工作时间，每分钟检查一次
                    continue
                
                # 检查每日执行次数限制
                if not self._check_daily_limit():
                    log.debug("Daily limit reached, waiting 60s")
                    await asyncio.sleep(60)  # 达到每日限制，等待到第二天
                    continue
                
                # 执行工作流
                log.info("Executing scheduled viral learning workflow")
                await self._execute_viral_learning_workflow()
                
                # 等待下次执行
                interval_seconds = self.config["interval_minutes"] * 60
                log.debug(f"Waiting {interval_seconds}s for next execution cycle")
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                log.info("Viral learning scheduler loop cancelled")
                break
            except Exception as e:
                log.error(f"Error in viral learning scheduler loop: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再继续
    
    def _is_working_hours(self) -> bool:
        """检查是否在工作时间内"""
        now = datetime.now()
        current_hour = now.hour
        start_hour = self.config.get("start_hour", 8)
        end_hour = self.config.get("end_hour", 22)
        return start_hour <= current_hour < end_hour
    
    def _check_daily_limit(self) -> bool:
        """检查每日执行次数限制"""
        today = datetime.now().date()
        
        # 如果是新的一天，重置计数
        if self.last_execution_date != today:
            self.daily_execution_count = 0
            self.last_execution_date = today
        
        max_daily_calls = self.config.get("max_daily_calls", 48)
        return self.daily_execution_count < max_daily_calls
    
    async def _execute_viral_learning_workflow(self):
        """执行爆款学习工作流"""
        execution_start_time = time.time()
        
        try:
            log.info("Executing viral learning workflow...")
            
            # 准备payload
            payload = {
                "trigger_type": "scheduled",
                "execution_time": execution_start_time,
                "execution_count": self.execution_count + 1,
                "daily_count": self.daily_execution_count + 1,
                "scheduler_info": {
                    "interval_minutes": self.config["interval_minutes"],
                    "max_daily_calls": self.config["max_daily_calls"]
                }
            }
            
            # 调用n8n工作流
            result = await self._call_n8n_workflow(payload)
            
            # 更新执行统计
            self.execution_count += 1
            self.daily_execution_count += 1
            self.last_execution_time = execution_start_time
            self.failed_attempts = 0
            
            execution_time = time.time() - execution_start_time
            log.info(f"Viral learning workflow executed successfully in {execution_time:.2f}s")
            log.debug(f"Workflow result: {result}")
            
        except Exception as e:
            self.failed_attempts += 1
            log.error(f"Failed to execute viral learning workflow (attempt {self.failed_attempts}): {e}")
            
            # 如果失败次数超过配置的重试次数，等待更长时间
            retry_attempts = self.config.get("retry_attempts", 3)
            if self.failed_attempts >= retry_attempts:
                retry_delay_minutes = self.config.get("retry_delay_minutes", 5)
                log.warning(f"Max retry attempts reached, waiting {retry_delay_minutes} minutes")
                await asyncio.sleep(retry_delay_minutes * 60)
                self.failed_attempts = 0
    
    async def _call_n8n_workflow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """调用n8n爆款学习工作流"""
        webhook_url = N8N_WORKFLOW_WEBHOOKS[N8NWorkflowType.VIRAL_LEARNING]
        timeout = self.workflow_config["timeout"]
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "OpenWebUI-HSAI-Scheduler/1.0",
                        "X-Scheduler-Type": "viral-learning"
                    }
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"n8n workflow failed with status {response.status}: {error_text}")
                        
            except asyncio.TimeoutError:
                raise Exception(f"n8n workflow timeout after {timeout}s")
            except Exception as e:
                raise Exception(f"Error calling n8n workflow: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "is_running": self.is_running,
            "enabled": self.config.get("enabled", False),
            "execution_count": self.execution_count,
            "daily_execution_count": self.daily_execution_count,
            "last_execution_time": self.last_execution_time,
            "last_execution_date": str(self.last_execution_date) if self.last_execution_date else None,
            "failed_attempts": self.failed_attempts,
            "config": self.config,
            "next_execution_estimate": self._estimate_next_execution()
        }
    
    def _estimate_next_execution(self) -> Optional[str]:
        """估算下次执行时间"""
        if not self.is_running or not self.config.get("enabled", False):
            return None
            
        if not self._is_working_hours():
            # 如果不在工作时间，返回明天开始时间
            tomorrow = datetime.now().date() + timedelta(days=1)
            start_hour = self.config.get("start_hour", 8)
            next_start = datetime.combine(tomorrow, datetime.min.time().replace(hour=start_hour))
            return next_start.isoformat()
        
        if not self._check_daily_limit():
            # 如果达到每日限制，返回明天开始时间
            tomorrow = datetime.now().date() + timedelta(days=1)
            start_hour = self.config.get("start_hour", 8)
            next_start = datetime.combine(tomorrow, datetime.min.time().replace(hour=start_hour))
            return next_start.isoformat()
        
        # 正常情况下的下次执行时间
        interval_minutes = self.config.get("interval_minutes", 30)
        if self.last_execution_time:
            next_time = datetime.fromtimestamp(self.last_execution_time) + timedelta(minutes=interval_minutes)
        else:
            next_time = datetime.now() + timedelta(minutes=interval_minutes)
        
        return next_time.isoformat()

# 全局调度器实例
viral_learning_scheduler = ViralLearningScheduler()