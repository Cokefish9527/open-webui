#!/usr/bin/env python3
"""
压缩包处理功能测试脚本
"""

import sys
import os
import zipfile
import tempfile
from pathlib import Path

def create_test_zip():
    """创建测试用的压缩包"""
    # 创建临时目录结构
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    # 创建目录结构
    scene_dir = temp_path / "frontdoor"
    scene_dir.mkdir()
    
    technique_dir = scene_dir / "overhead"
    technique_dir.mkdir()
    
    # 创建测试文件
    test_files = [
        (technique_dir / "test_video.mp4", "video content"),
        (technique_dir / "test_image.jpg", "image content"),
        (scene_dir / "another_video.mp4", "another video content"),
    ]
    
    for file_path, content in test_files:
        with open(file_path, "w") as f:
            f.write(content)
    
    # 创建压缩包
    zip_path = temp_path / "test_materials.zip"
    with zipfile.ZipFile(zip_path, 'w') as zip_ref:
        for file_path, _ in test_files:
            arc_name = file_path.relative_to(temp_path)
            zip_ref.write(file_path, arc_name)
    
    print(f"创建测试压缩包: {zip_path}")
    return zip_path, temp_path

def test_zip_structure(zip_path):
    """测试压缩包结构"""
    print("测试压缩包结构:")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for info in zip_ref.infolist():
            print(f"  {info.filename}")

if __name__ == "__main__":
    zip_path, temp_dir = create_test_zip()
    test_zip_structure(zip_path)
    print("压缩包处理测试完成!")
    
    # 清理临时文件
    import shutil
    shutil.rmtree(temp_dir)