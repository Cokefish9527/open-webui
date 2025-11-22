#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试蓝图进度模型的修改
"""

import os
import sys

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))


def test_blueprint_model():
    try:
        # 导入模型
        from open_webui.models.hsai_blueprint_progress import HSAIBlueprintProgress, HSAIBlueprintProgressModel
        
        # 检查模型是否包含新的字段
        if hasattr(HSAIBlueprintProgress, 'info_collection_processed'):
            print("✓ HSAIBlueprintProgress 模型包含 info_collection_processed 字段")
        else:
            print("✗ HSAIBlueprintProgress 模型不包含 info_collection_processed 字段")
            return False
            
        # 检查Pydantic模型是否包含新的字段
        if 'info_collection_processed' in HSAIBlueprintProgressModel.model_fields:
            print("✓ HSAIBlueprintProgressModel Pydantic模型包含 info_collection_processed 字段")
        else:
            print("✗ HSAIBlueprintProgressModel Pydantic模型不包含 info_collection_processed 字段")
            return False
            
        print("所有模型验证通过！")
        return True
        
    except Exception as e:
        print(f"模型验证时发生错误: {e}")
        return False


def main():
    print("== 测试蓝图进度模型修改 ==")
    success = test_blueprint_model()
    if success:
        print("✅ 蓝图进度模型验证完成。")
        return 0

    print("❌ 蓝图进度模型验证失败。")
    return 1


if __name__ == "__main__":
    sys.exit(main())