import sys
import os
import time
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.models.hsai_materials import HSAIMaterialModel, HSAIMaterialForm
from open_webui.internal.db import get_db
from open_webui.models.hsai_materials import HSAIMaterial

def test_pydantic_model():
    print("Testing Pydantic model validation...")
    
    # 创建测试数据
    form_data = HSAIMaterialForm(
        name="test_material_pydantic",
        description="Test material for Pydantic model",
        material_type="text",
        file_path="./uploads/test_material_pydantic.txt",
        file_size=1024,
        file_hash="abc123def456",
        mime_type="text/plain",
        scene_code="SC001",
        technique_code="TC001",
        properties_code="prop1_prop2_prop3",
        material_metadata={"test": "metadata"}
    )
    
    user_id = "496e0f43-8bfa-464a-b333-7738d4b3b76d"
    
    print(f"Form data: {form_data}")
    
    # 直接测试数据库插入并创建Pydantic模型
    with get_db() as db:
        id = str(uuid.uuid4())
        print(f"Generated ID: {id}")
        
        # 创建模型数据
        material_data = {
            "id": id,
            "user_id": user_id,
            **form_data.model_dump(),
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        
        print(f"Material data: {material_data}")
        
        try:
            # 创建数据库记录
            result = HSAIMaterial(**material_data)
            db.add(result)
            db.commit()
            db.refresh(result)
            
            # 创建Pydantic模型
            pydantic_model = HSAIMaterialModel.model_validate(result)
            print(f"Pydantic model created: {pydantic_model}")
            print(f"Pydantic model dict: {pydantic_model.model_dump()}")
            
            print("Pydantic model validation successful!")
            
            # 清理测试数据
            db.delete(result)
            db.commit()
            print("Test data cleaned up")
            
        except Exception as e:
            print(f"Pydantic model validation failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_pydantic_model()