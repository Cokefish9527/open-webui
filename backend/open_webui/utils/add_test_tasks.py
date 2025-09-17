#!/usr/bin/env python3
"""
添加测试任务数据脚本
用于前端开发人员调试使用
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


def add_test_tasks():
    """添加测试任务数据"""
    
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
        
        # 测试用户ID（使用用户记忆中的测试账号）
        test_user_id = "saiter2306@163.com"
        
        # 创建5个测试任务，模拟从Redis队列获取到的待确认学习爆款视频
        test_tasks = [
            {
                "title": "学习爆款视频：如何制作吸引人的短视频开头",
                "description": "该任务需要您确认是否学习这个爆款视频内容。视频来自抖音平台，时长45秒。",
                "task_type": HSAITaskType.VIDEO_CREATION,
                "status": HSAITaskStatus.PENDING,
                "config": '{"video_url": "https://example.com/video1.mp4", "thumbnail_url": "https://example.com/thumb1.jpg", "platform": "抖音", "duration": 45, "title": "如何制作吸引人的短视频开头", "tags": ["短视频", "开头技巧", "吸引人"], "video_id": "video_001"}',
                "inputs": '{"source": "viral_video_crawl", "crawl_timestamp": ' + str(int(time.time()) - 3600) + ', "enterprise_id": "ent_001"}',
                "tags": '["爆款学习", "待确认", "抖音"]',
                "priority": 10
            },
            {
                "title": "学习爆款视频：美食制作教程的拍摄技巧",
                "description": "该任务需要您确认是否学习这个爆款视频内容。视频来自快手平台，时长72秒。",
                "task_type": HSAITaskType.VIDEO_CREATION,
                "status": HSAITaskStatus.PENDING,
                "config": '{"video_url": "https://example.com/video2.mp4", "thumbnail_url": "https://example.com/thumb2.jpg", "platform": "快手", "duration": 72, "title": "美食制作教程的拍摄技巧", "tags": ["美食", "拍摄技巧", "教程"], "video_id": "video_002"}',
                "inputs": '{"source": "viral_video_crawl", "crawl_timestamp": ' + str(int(time.time()) - 7200) + ', "enterprise_id": "ent_001"}',
                "tags": '["爆款学习", "待确认", "快手"]',
                "priority": 8
            },
            {
                "title": "学习爆款视频：宠物日常的趣味剪辑方法",
                "description": "该任务需要您确认是否学习这个爆款视频内容。视频来自抖音平台，时长38秒。",
                "task_type": HSAITaskType.VIDEO_CREATION,
                "status": HSAITaskStatus.IN_PROGRESS,
                "config": '{"video_url": "https://example.com/video3.mp4", "thumbnail_url": "https://example.com/thumb3.jpg", "platform": "抖音", "duration": 38, "title": "宠物日常的趣味剪辑方法", "tags": ["宠物", "剪辑", "趣味"], "video_id": "video_003"}',
                "inputs": '{"source": "viral_video_crawl", "crawl_timestamp": ' + str(int(time.time()) - 10800) + ', "enterprise_id": "ent_001"}',
                "tags": '["爆款学习", "学习中", "抖音"]',
                "priority": 6
            },
            {
                "title": "学习爆款视频：旅行vlog的叙事结构",
                "description": "该任务需要您确认是否学习这个爆款视频内容。视频来自小红书平台，时长95秒。",
                "task_type": HSAITaskType.VIDEO_CREATION,
                "status": HSAITaskStatus.PENDING,
                "config": '{"video_url": "https://example.com/video4.mp4", "thumbnail_url": "https://example.com/thumb4.jpg", "platform": "小红书", "duration": 95, "title": "旅行vlog的叙事结构", "tags": ["旅行", "vlog", "叙事"], "video_id": "video_004"}',
                "inputs": '{"source": "viral_video_crawl", "crawl_timestamp": ' + str(int(time.time()) - 14400) + ', "enterprise_id": "ent_001"}',
                "tags": '["爆款学习", "待确认", "小红书"]',
                "priority": 7
            },
            {
                "title": "学习爆款视频：健身动作的标准示范",
                "description": "该任务需要您确认是否学习这个爆款视频内容。视频来自抖音平台，时长62秒。",
                "task_type": HSAITaskType.VIDEO_CREATION,
                "status": HSAITaskStatus.COMPLETED,
                "config": '{"video_url": "https://example.com/video5.mp4", "thumbnail_url": "https://example.com/thumb5.jpg", "platform": "抖音", "duration": 62, "title": "健身动作的标准示范", "tags": ["健身", "标准示范", "教程"], "video_id": "video_005", "learned_at": ' + str(int(time.time()) - 86400) + '}',
                "inputs": '{"source": "viral_video_crawl", "crawl_timestamp": ' + str(int(time.time()) - 90000) + ', "enterprise_id": "ent_001"}',
                "outputs": '{"analysis_result": {"script": "健身动作分解脚本...", "key_points": ["标准姿势", "呼吸节奏", "安全要点"], "material_id": "mat_001"}}',
                "tags": '["爆款学习", "已完成", "抖音"]',
                "priority": 5,
                "completed_at": int(time.time()) - 86400
            }
        ]
        
        # 添加测试任务到数据库
        created_tasks = []
        for i, task_data in enumerate(test_tasks):
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
                int(time.time()) - (len(test_tasks) - i) * 3600,  # 创建时间
                int(time.time()) - (len(test_tasks) - i) * 3600,  # 更新时间
                task_data.get("completed_at", None)
            )
            
            try:
                cursor.execute(sql, params)
                db_conn.commit()
                created_tasks.append(task_id)
                print(f"✅ 成功创建测试任务: {task_data['title']} (ID: {task_id})")
            except Exception as e:
                print(f"❌ 创建测试任务失败: {task_data['title']}, 错误: {e}")
        
        print(f"\n🎉 总共创建了 {len(created_tasks)} 个测试任务")
        db_conn.close()
        return created_tasks
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {str(e)}")
        if db_conn:
            db_conn.close()
        return []

if __name__ == "__main__":
    add_test_tasks()