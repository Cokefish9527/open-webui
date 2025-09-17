#!/usr/bin/env python3
"""
添加TikTok视频任务数据脚本
从视频链接提取信息并添加到hsai_tasks表
"""

import sys
import os
import time
import sqlite3
from enum import Enum

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

class HSAITaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HSAITaskType(str, Enum):
    """任务类型枚举"""
    VIDEO_CREATION = "video_creation"
    CONTENT_ANALYSIS = "content_analysis"
    MATERIAL_PROCESSING = "material_processing"
    PLATFORM_PUBLISHING = "platform_publishing"
    WORKFLOW_EXECUTION = "workflow_execution"


def add_tiktok_task(video_url):
    """添加TikTok视频任务数据"""
    
    # 数据库路径
    db_path = "data/webui.db"
    db_paths = [
        db_path,
        "./data/webui.db",
        "../data/webui.db",
        "c:/work/open-webui/backend/data/webui.db",
        "D:/Work/hsch/open-webui/backend/data/webui.db"
    ]
    
    db_conn = None
    for path in db_paths:
        try:
            db_conn = sqlite3.connect(path)
            print(f"✅ 连接到数据库: {path}")
            break
        except Exception as e:
            print(f"❌ 无法连接到数据库 {path}: {e}")
            continue
    
    if not db_conn:
        print("❌ 无法连接到任何数据库")
        return
    
    try:
        cursor = db_conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hsai_tasks'
        """)
        
        if not cursor.fetchone():
            print("❌ hsai_tasks 表不存在")
            return
        
        print("✅ hsai_tasks 表存在")
        
        # 从URL提取信息
        # 示例URL: https://www.tiktok.com/@bykovfx/video/7545796456385449223
        import re
        username_match = re.search(r'@([^/]+)/video/', video_url)
        video_id_match = re.search(r'/video/(\d+)', video_url)
        
        username = username_match.group(1) if username_match else "unknown"
        video_id = video_id_match.group(1) if video_id_match else "unknown"
        
        # 测试用户ID（使用用户记忆中的测试账号）
        test_user_id = "saiter2306@163.com"
        
        # 创建任务数据
        task_data = {
            "title": f"学习TikTok爆款视频：@{username}的视频内容",
            "description": f"该任务需要您确认是否学习这个TikTok爆款视频内容。视频来自TikTok平台，ID为{video_id}。",
            "task_type": HSAITaskType.VIDEO_CREATION,
            "status": HSAITaskStatus.PENDING,
            "config": f'{{"video_url": "{video_url}", "thumbnail_url": "", "platform": "TikTok", "duration": 0, "title": "@{username}的视频", "tags": ["TikTok", "爆款学习"], "video_id": "{video_id}"}}',
            "inputs": f'{{"source": "viral_video_crawl", "crawl_timestamp": {int(time.time())}, "enterprise_id": "ent_001"}}',
            "tags": '["爆款学习", "待确认", "TikTok"]',
            "priority": 10
        }
        
        # 生成任务ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # 构建SQL插入语句
        sql = """
        INSERT INTO hsai_tasks (
            id, title, description, task_type, status, user_id, 
            config, inputs, outputs, tags, priority, 
            created_at, updated_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # 准备参数
        params = (
            task_id,
            task_data["title"],
            task_data["description"],
            task_data["task_type"],
            task_data["status"],
            test_user_id,
            task_data.get("config", None),
            task_data.get("inputs", None),
            task_data.get("outputs", None),
            task_data.get("tags", None),
            task_data.get("priority", 0),
            int(time.time()),  # 创建时间
            int(time.time()),  # 更新时间
            task_data.get("completed_at", None)
        )
        
        try:
            cursor.execute(sql, params)
            db_conn.commit()
            print(f"✅ 成功创建TikTok视频任务:")
            print(f"   标题: {task_data['title']}")
            print(f"   ID: {task_id}")
            print(f"   视频链接: {video_url}")
            print(f"   用户名: {username}")
            print(f"   视频ID: {video_id}")
        except Exception as e:
            print(f"❌ 创建TikTok视频任务失败: {e}")
            return None
        
        db_conn.close()
        return task_id
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {str(e)}")
        if db_conn:
            db_conn.close()
        return None

if __name__ == "__main__":
    # TikTok视频链接
    tiktok_url = "https://www.tiktok.com/@bykovfx/video/7545796456385449223"
    add_tiktok_task(tiktok_url)