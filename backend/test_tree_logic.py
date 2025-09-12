#!/usr/bin/env python3
"""
测试数据库查询和树构建逻辑
"""

import sys
import os
sys.path.append('c:/work/open-webui/backend')

from open_webui.models.hsai_materials import HSAIMaterialFolders

def test_folders_data():
    """测试文件夹数据获取和树构建"""
    print("=== 测试文件夹数据和树构建逻辑 ===")
    
    # 使用固定的测试用户ID（从之前的日志中获取）
    test_user_id = "496e0f43-8bfa-464a-b333-7738d4b3b76d"
    
    try:
        # 1. 获取原始数据库数据
        print("1️⃣ 从数据库获取文件夹数据...")
        folders = HSAIMaterialFolders.get_folders_by_user_id(test_user_id)
        print(f"✅ 获取到 {len(folders)} 个文件夹")
        
        # 2. 分析数据
        root_folders = []
        child_folders = []
        
        for folder in folders:
            if folder.parent_id is None:
                root_folders.append(folder)
            else:
                child_folders.append(folder)
        
        print(f"📊 数据分析:")
        print(f"   根文件夹: {len(root_folders)}")
        print(f"   子文件夹: {len(child_folders)}")
        
        # 3. 显示一些样本数据
        print(f"\n📋 根文件夹样本 (前5个):")
        for i, folder in enumerate(root_folders[:5]):
            print(f"   [{i+1}] {folder.name} (ID: {folder.id})")
        
        print(f"\n📋 子文件夹样本 (前10个):")
        for i, folder in enumerate(child_folders[:10]):
            print(f"   [{i+1}] {folder.name} (ID: {folder.id}) -> 父目录: {folder.parent_id}")
        
        # 4. 测试树构建逻辑（模拟路由中的逻辑）
        print(f"\n🌳 测试树构建逻辑...")
        
        # 第一轮：创建所有的response对象
        folder_dict = {folder.id: folder for folder in folders}
        response_dict = {}  # 用于存储HSAIMaterialFolderResponse对象
        root_responses = []
        
        # 模拟HSAIMaterialFolderResponse的创建
        class MockFolderResponse:
            def __init__(self, folder):
                self.id = folder.id
                self.name = folder.name
                self.parent_id = folder.parent_id
                self.children = []
        
        for folder in folders:
            folder_response = MockFolderResponse(folder)
            response_dict[folder.id] = folder_response
            
            if folder.parent_id is None:
                root_responses.append(folder_response)
        
        # 第二轮：建立父子关系
        for folder in folders:
            if folder.parent_id is not None:
                parent_response = response_dict.get(folder.parent_id)
                child_response = response_dict.get(folder.id)
                if parent_response and child_response:
                    parent_response.children.append(child_response)
        
        # 5. 验证树构建结果
        print(f"🔍 树构建结果验证:")
        print(f"   根级响应对象: {len(root_responses)}")
        
        folders_with_children = 0
        total_children = 0
        
        for root in root_responses:
            if root.children:
                folders_with_children += 1
                children_count = len(root.children)
                total_children += children_count
                if folders_with_children <= 5:  # 只显示前5个
                    print(f"   {root.name} (ID: {root.id}) - {children_count} 个子目录")
                    for child in root.children[:3]:  # 显示前3个子目录
                        print(f"     └── {child.name} (ID: {child.id})")
        
        print(f"📈 树构建统计:")
        print(f"   有子目录的根文件夹: {folders_with_children}")
        print(f"   总计子目录数量: {total_children}")
        
        # 6. 检查特定的测试用例
        print(f"\n🎯 检查最近的测试数据...")
        
        # 查找最近创建的测试文件夹
        test_folders = [f for f in folders if 'debug_' in f.name or 'test_folder_' in f.name]
        test_folders.sort(key=lambda x: x.created_at, reverse=True)
        
        print(f"📝 最近的测试文件夹 (前5个):")
        for i, folder in enumerate(test_folders[:5]):
            parent_info = f"父目录: {folder.parent_id}" if folder.parent_id else "根目录"
            print(f"   [{i+1}] {folder.name} (ID: {folder.id}) - {parent_info}")
            
            # 检查这个文件夹在树中的位置
            if folder.parent_id:
                parent_response = response_dict.get(folder.parent_id)
                if parent_response:
                    found_in_children = any(child.id == folder.id for child in parent_response.children)
                    print(f"       树中状态: {'✅ 正确出现在父目录children中' if found_in_children else '❌ 未出现在父目录children中'}")
                else:
                    print(f"       树中状态: ❌ 父目录不存在")
            else:
                found_in_roots = any(root.id == folder.id for root in root_responses)
                print(f"       树中状态: {'✅ 正确出现在根目录列表中' if found_in_roots else '❌ 未出现在根目录列表中'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_folders_data()