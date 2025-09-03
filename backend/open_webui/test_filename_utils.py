#!/usr/bin/env python3
"""
文件名工具函数测试脚本
"""

import sys
import os
import re
from pathlib import Path

# 文件名生成函数
def _generate_filename_with_codes(material_name: str, scene_code: str, technique_code: str, properties_code: list) -> str:
    """
    根据分类代码生成文件名
    
    Args:
        material_name: 素材名称
        scene_code: 场景代码
        technique_code: 手法代码
        properties_code: 属性代码列表
        
    Returns:
        str: 生成的文件名
    """
    # 清理素材名称，移除特殊字符并确保使用英文字符
    clean_name = "".join(c for c in material_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    clean_name = clean_name.replace(' ', '_')
    
    # 确保所有组件都是英文字符
    if scene_code:
        scene_code = re.sub(r'[^a-zA-Z0-9_]', '', scene_code)
    
    if technique_code:
        technique_code = re.sub(r'[^a-zA-Z0-9_]', '', technique_code)
    
    if properties_code:
        # 确保属性代码列表中的每个元素都是英文字符
        properties_code = [re.sub(r'[^a-zA-Z0-9_]', '', prop) for prop in properties_code]
        # 过滤掉空字符串
        properties_code = [prop for prop in properties_code if prop]
    
    # 构建文件名组件
    filename_parts = [clean_name]
    
    if scene_code:
        filename_parts.append(scene_code)
    
    if technique_code:
        filename_parts.append(technique_code)
    
    if properties_code:
        # 将属性代码列表合并为单个字符串
        properties_str = "_".join(properties_code)
        filename_parts.append(properties_str)
    
    # 用下划线连接所有部分
    filename_base = "_".join(filename_parts)
    
    # 限制总长度以避免文件名过长
    if len(filename_base) > 100:
        filename_base = filename_base[:100]
    
    # 添加模拟哈希值
    mock_hash = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
    return f"{filename_base}_{mock_hash}"

# 文件名解析函数
def _parse_filename_for_codes(filename: str) -> dict:
    """
    从文件名中解析分类代码信息
    
    Args:
        filename (str): 文件名
        
    Returns:
        dict: 包含解析出的分类代码信息
    """
    # 移除文件扩展名
    stem = Path(filename).stem
    
    # 尝试从文件名中提取哈希值（假设是文件名最后32个字符）
    hash_pattern = re.compile(r'([a-fA-F0-9]{32})$')
    hash_match = hash_pattern.search(stem)
    
    if hash_match:
        # 如果找到哈希值，移除它以获取基础文件名
        hash_value = hash_match.group(1)
        base_name = stem[:hash_match.start()]
        # 移除可能的尾部下划线
        if base_name.endswith('_'):
            base_name = base_name[:-1]
    else:
        base_name = stem
    
    # 分割文件名组件
    parts = base_name.split('_')
    
    if len(parts) < 2:
        # 文件名格式不符合预期
        return {
            "name": base_name,
            "scene_code": None,
            "technique_code": None,
            "properties_code": None
        }
    
    # 第一个部分是素材名称
    material_name = parts[0]
    
    # 其余部分可能是分类代码
    codes = parts[1:] if len(parts) > 1 else []
    
    # 简单的启发式解析（实际应用中可能需要更复杂的逻辑）
    scene_code = codes[0] if len(codes) > 0 else None
    technique_code = codes[1] if len(codes) > 1 else None
    properties_code = codes[2:] if len(codes) > 2 else None
    
    return {
        "name": material_name,
        "scene_code": scene_code,
        "technique_code": technique_code,
        "properties_code": properties_code
    }

def test_filename_generation():
    """测试文件名生成功能"""
    print("开始测试文件名生成功能...")
    
    # 测试文件名生成
    test_cases = [
        ("测试素材", "frontdoor", "overhead", ["silent", "wide"]),
        ("企业介绍", "office", "tracking", ["voiced"]),
        ("产品展示", "showcase", "closeup", ["music"]),
        ("中文名称", "正门口", "俯拍", ["无声"]),  # 测试中文字符处理
    ]
    
    for name, scene, technique, properties in test_cases:
        filename = _generate_filename_with_codes(name, scene, technique, properties)
        print(f"生成文件名: {filename}")
        
        # 测试文件名解析
        parsed = _parse_filename_for_codes(filename + ".mp4")
        print(f"解析结果: {parsed}")
        print()

def test_filename_parsing():
    """测试文件名解析功能"""
    print("开始测试文件名解析功能...")
    
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

def test_english_characters():
    """测试英文字符处理"""
    print("开始测试英文字符处理...")
    
    # 测试中文字符被正确过滤
    test_cases = [
        ("中文测试", "正门口", "俯拍", ["无声"]),
        ("English Test", "front-door", "over_head", ["no-sound"]),
    ]
    
    for name, scene, technique, properties in test_cases:
        filename = _generate_filename_with_codes(name, scene, technique, properties)
        print(f"原始输入: name={name}, scene={scene}, technique={technique}, properties={properties}")
        print(f"生成文件名: {filename}")
        
        # 测试文件名解析
        parsed = _parse_filename_for_codes(filename + ".mp4")
        print(f"解析结果: {parsed}")
        print()

if __name__ == "__main__":
    test_filename_generation()
    test_filename_parsing()
    test_english_characters()
    print("所有测试完成!")