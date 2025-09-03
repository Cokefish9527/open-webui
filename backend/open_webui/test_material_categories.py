#!/usr/bin/env python3
"""
素材分类管理测试脚本
"""

import sys
import os
import json
import re
from pathlib import Path

# 添加项目路径到sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from open_webui.models.hsai_materials import (
    HSAIMaterialCategories,
    HSAIMaterialCategoryForm
)

def test_category_management():
    """测试分类管理功能"""
    print("开始测试素材分类管理功能...")
    
    # 1. 创建场景分类
    print("\n1. 创建场景分类...")
    scene_form = HSAIMaterialCategoryForm(
        name="frontdoor",
        display_name="正门口",
        category_type="scene",
        description="在建筑物正门口拍摄的素材"
    )
    
    scene_category = HSAIMaterialCategories.insert_new_category(scene_form)
    if scene_category:
        print(f"成功创建场景分类: {scene_category.name} ({scene_category.display_name})")
    else:
        print("创建场景分类失败")
        return False
    
    # 2. 创建手法分类
    print("\n2. 创建手法分类...")
    technique_form = HSAIMaterialCategoryForm(
        name="overhead",
        display_name="俯拍",
        category_type="technique",
        description="从上方俯视拍摄的手法"
    )
    
    technique_category = HSAIMaterialCategories.insert_new_category(technique_form)
    if technique_category:
        print(f"成功创建手法分类: {technique_category.name} ({technique_category.display_name})")
    else:
        print("创建手法分类失败")
        return False
    
    # 3. 创建属性分类
    print("\n3. 创建属性分类...")
    property_form = HSAIMaterialCategoryForm(
        name="silent",
        display_name="无声",
        category_type="property",
        description="没有配音的素材"
    )
    
    property_category = HSAIMaterialCategories.insert_new_category(property_form)
    if property_category:
        print(f"成功创建属性分类: {property_category.name} ({property_category.display_name})")
    else:
        print("创建属性分类失败")
        return False
    
    # 4. 获取分类列表
    print("\n4. 获取分类列表...")
    all_categories = HSAIMaterialCategories.get_all_categories()
    print(f"总分类数: {len(all_categories)}")
    
    scene_categories = HSAIMaterialCategories.get_categories_by_type("scene")
    print(f"场景分类数: {len(scene_categories)}")
    
    technique_categories = HSAIMaterialCategories.get_categories_by_type("technique")
    print(f"手法分类数: {len(technique_categories)}")
    
    property_categories = HSAIMaterialCategories.get_categories_by_type("property")
    print(f"属性分类数: {len(property_categories)}")
    
    # 5. 更新分类
    print("\n5. 更新分类...")
    update_form = HSAIMaterialCategoryForm(
        name="frontdoor_upd",
        display_name="正门口(更新)",
        category_type="scene",
        description="在建筑物正门口拍摄的素材(更新)"
    )
    
    updated_category = HSAIMaterialCategories.update_category_by_id(scene_category.id, update_form)
    if updated_category:
        print(f"成功更新分类: {updated_category.name} ({updated_category.display_name})")
    else:
        print("更新分类失败")
        return False
    
    # 6. 删除分类
    print("\n6. 删除分类...")
    delete_result = HSAIMaterialCategories.delete_category_by_id(property_category.id)
    if delete_result:
        print("成功删除属性分类")
    else:
        print("删除属性分类失败")
        return False
    
    # 7. 验证删除结果
    print("\n7. 验证删除结果...")
    remaining_categories = HSAIMaterialCategories.get_all_categories()
    print(f"删除后分类数: {len(remaining_categories)}")
    
    print("\n测试完成!")
    return True

def test_filename_generation():
    """测试文件名生成功能"""
    print("\n开始测试文件名生成功能...")
    
    # 直接从路由器导入函数
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'routers'))
    
    from open_webui.routers.hsai_materials import _generate_filename_with_codes, _parse_filename_for_codes
    
    # 测试文件名生成
    test_cases = [
        ("测试素材", "frontdoor", "overhead", ["silent", "wide"]),
        ("企业介绍", "office", "tracking", ["voiced"]),
        ("产品展示", "showcase", "closeup", ["music"]),
    ]
    
    for name, scene, technique, properties in test_cases:
        filename = _generate_filename_with_codes(name, scene, technique, properties)
        print(f"生成文件名: {filename}")
        
        # 测试文件名解析
        parsed = _parse_filename_for_codes(filename + ".mp4")
        print(f"解析结果: {parsed}")
        print()
    
    print("文件名生成和解析测试完成!")

def test_filename_parsing():
    """测试文件名解析功能"""
    print("\n开始测试文件名解析功能...")
    
    from open_webui.routers.hsai_materials import _parse_filename_for_codes
    
    # 测试用例
    test_cases = [
        "测试素材_frontdoor_overhead_silent_wide_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6.mp4",
        "企业介绍_office_tracking_voiced_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6.mp4",
        "simple_name_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6.mp4",
        "only_name.mp4"
    ]
    
    for filename in test_cases:
        parsed = _parse_filename_for_codes(filename)
        print(f"文件名: {filename}")
        print(f"解析结果: {parsed}")
        print()
    
    print("文件名解析测试完成!")

if __name__ == "__main__":
    # 运行测试
    success = test_category_management()
    if success:
        test_filename_generation()
        test_filename_parsing()
        print("\n所有测试通过!")
    else:
        print("\n测试失败!")
        sys.exit(1)