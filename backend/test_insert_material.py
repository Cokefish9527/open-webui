import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.models.hsai_materials import HSAIMaterials, HSAIMaterialForm

def test_insert_material():
    # 创建测试数据
    form_data = HSAIMaterialForm(
        name="test_material",
        description="Test material for debugging",
        material_type="text",
        file_path="test/path/file.txt",
        file_size=1024,
        file_hash="abc123",
        mime_type="text/plain"
    )
    
    print("Testing insert_new_material...")
    print(f"Form data: {form_data}")
    
    # 尝试插入素材记录
    user_id = "496e0f43-8bfa-464a-b333-7738d4b3b76d"  # 使用测试脚本中的用户ID
    result = HSAIMaterials.insert_new_material(user_id, form_data)
    
    if result:
        print(f"Success! Material created with ID: {result.id}")
    else:
        print("Failed to create material record")

if __name__ == "__main__":
    test_insert_material()