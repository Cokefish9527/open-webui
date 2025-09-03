#!/usr/bin/env python3
"""
分页功能测试脚本
"""

import sys
import os

# 添加项目路径到sys.path
backend_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_path)

def test_pagination_models():
    """测试分页模型"""
    print("开始测试分页模型...")
    
    # 动态导入，避免循环依赖
    from open_webui.models.hsai_materials import (
        PaginationData,
        PaginatedHSAIMaterialResponse,
        HSAIMaterialResponse
    )

    from open_webui.models.hsai_tasks import (
        PaginatedHSAITaskResponse,
        HSAITaskResponse
    )
    
    # 测试PaginationData
    pagination = PaginationData(
        total=100,
        page=1,
        size=20,
        total_pages=5
    )
    print(f"PaginationData测试通过: {pagination}")
    
    # 测试PaginatedHSAIMaterialResponse
    # 先创建一个简单的素材响应对象
    material_response = HSAIMaterialResponse(
        id="test_material_1",
        name="测试素材",
        material_type="video",
        file_size=1024,
        created_at=1234567890,
        updated_at=1234567890
    )
    
    paginated_materials = PaginatedHSAIMaterialResponse(
        data=[material_response],
        pagination=pagination
    )
    print(f"PaginatedHSAIMaterialResponse测试通过: {paginated_materials}")
    
    # 测试PaginatedHSAITaskResponse
    # 先创建一个简单的任务响应对象
    task_response = HSAITaskResponse(
        id="test_task_1",
        title="测试任务",
        task_type="video_creation",
        status="pending",
        progress=0,
        priority=1,
        created_at=1234567890,
        updated_at=1234567890
    )
    
    paginated_tasks = PaginatedHSAITaskResponse(
        data=[task_response],
        pagination=pagination
    )
    print(f"PaginatedHSAITaskResponse测试通过: {paginated_tasks}")
    
    print("所有分页模型测试通过!")

if __name__ == "__main__":
    try:
        test_pagination_models()
        print("分页功能测试完成!")
    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()