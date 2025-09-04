#!/usr/bin/env python3
"""
测试任务指派人功能
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from open_webui.models.hsai_tasks import (
    HSAITaskForm, 
    HSAITaskUpdateForm, 
    HSAITasks,
    HSAITaskType
)

def test_task_assignee_functionality():
    """测试任务指派人功能"""
    
    # 创建测试用户ID
    user_id = "test_user_123"
    assignee_id = "assignee_user_456"
    
    print("开始测试任务指派人功能...")
    
    # 1. 测试创建带指派人的任务
    print("\n1. 测试创建带指派人的任务")
    task_form = HSAITaskForm(
        title="测试任务",
        description="这是一个测试任务",
        task_type=HSAITaskType.VIDEO_CREATION,
        assignee_id=assignee_id,
        priority=5
    )
    
    task = HSAITasks.insert_new_task(user_id, task_form)
    assert task is not None, "任务创建失败"
    assert task.assignee_id == assignee_id, f"任务指派人ID不正确: {task.assignee_id}"
    print(f"✓ 任务创建成功，ID: {task.id}, 指派人: {task.assignee_id}")
    
    # 2. 测试更新任务指派人
    print("\n2. 测试更新任务指派人")
    new_assignee_id = "new_assignee_789"
    update_form = HSAITaskUpdateForm(assignee_id=new_assignee_id)
    
    updated_task = HSAITasks.update_task_by_id(task.id, update_form)
    assert updated_task is not None, "任务更新失败"
    assert updated_task.assignee_id == new_assignee_id, f"任务指派人更新失败: {updated_task.assignee_id}"
    print(f"✓ 任务指派人更新成功: {updated_task.assignee_id}")
    
    # 3. 测试按指派人查询任务
    print("\n3. 测试按指派人查询任务")
    tasks = HSAITasks.get_tasks_by_user_id(user_id, assignee_id=new_assignee_id)
    assert len(tasks) > 0, "按指派人查询任务失败"
    assert tasks[0].assignee_id == new_assignee_id, "查询结果中的指派人ID不正确"
    print(f"✓ 按指派人查询任务成功，找到 {len(tasks)} 个任务")
    
    # 4. 测试任务计数
    print("\n4. 测试任务计数")
    task_count = HSAITasks.get_tasks_count(user_id, assignee_id=new_assignee_id)
    assert task_count > 0, "任务计数失败"
    print(f"✓ 任务计数成功，共 {task_count} 个任务")
    
    print("\n所有测试通过！任务指派人功能正常工作。")

if __name__ == "__main__":
    test_task_assignee_functionality()