import sys
import os
import time
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.models.hsai_materials import HSAIMaterials, HSAIMaterialForm
from open_webui.internal.db import get_db
from open_webui.models.hsai_materials import HSAIMaterial

def test_db_insert():
    print("Testing database insertion...")
    
    # 创建测试数据
    form_data = HSAIMaterialForm(
        name="test_material_db",
        description="Test material for database insertion",
        material_type="text",
        file_path="./uploads/test_material_db.txt",
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
    print(f"User ID: {user_id}")
    
    # 直接测试数据库插入
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
        
        print(f"Material data to insert: {material_data}")
        
        try:
            # 创建数据库记录
            result = HSAIMaterial(**material_data)
            print(f"Created HSAIMaterial object: {result}")
            
            db.add(result)
            print("Added to session")
            
            db.commit()
            print("Committed to database")
            
            db.refresh(result)
            print(f"Refreshed result: {result}")
            
            print("Database insertion successful!")
            
            # 清理测试数据
            db.delete(result)
            db.commit()
            print("Test data cleaned up")
            
        except Exception as e:
            print(f"Database insertion failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_db_insert()