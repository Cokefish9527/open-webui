import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.models.hsai_materials import HSAIMaterialForm, HSAIMaterials
from pydantic import ValidationError

def test_material_form():
    print("Testing HSAIMaterialForm creation...")
    
    # 测试1: 基本表单数据
    try:
        form_data1 = HSAIMaterialForm(
            name="test_material",
            description="Test material for debugging",
            material_type="text",
            file_path="test/path/file.txt",
            file_size=1024,
            file_hash="abc123",
            mime_type="text/plain"
        )
        print(f"Test 1 - Basic form data: SUCCESS")
        print(f"Form data: {form_data1}")
    except ValidationError as e:
        print(f"Test 1 - Basic form data: FAILED - {e}")
    
    # 测试2: 包含properties_code字符串
    try:
        form_data2 = HSAIMaterialForm(
            name="test_material2",
            description="Test material with properties_code string",
            material_type="text",
            file_path="test/path/file2.txt",
            file_size=1024,
            file_hash="abc123",
            mime_type="text/plain",
            properties_code="prop1_prop2_prop3"  # 字符串格式
        )
        print(f"Test 2 - Form with properties_code string: SUCCESS")
        print(f"Form data: {form_data2}")
    except ValidationError as e:
        print(f"Test 2 - Form with properties_code string: FAILED - {e}")
    
    # 测试3: 尝试插入数据库
    try:
        user_id = "496e0f43-8bfa-464a-b333-7738d4b3b76d"
        result = HSAIMaterials.insert_new_material(user_id, form_data2)
        if result:
            print(f"Test 3 - Database insertion: SUCCESS - ID: {result.id}")
        else:
            print(f"Test 3 - Database insertion: FAILED")
    except Exception as e:
        print(f"Test 3 - Database insertion: FAILED - {e}")

if __name__ == "__main__":
    test_material_form()