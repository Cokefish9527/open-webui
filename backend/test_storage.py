import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.storage.provider import Storage

def test_storage():
    print("Testing storage provider...")
    
    # 创建测试文件内容
    content = b"Hello, this is a test file for storage testing."
    file_like = io.BytesIO(content)
    
    try:
        # 测试上传文件
        contents, file_path = Storage.upload_file(
            file=file_like,
            filename="test_storage.txt",
            tags={
                "user_id": "496e0f43-8bfa-464a-b333-7738d4b3b76d",
                "test": "true"
            }
        )
        print(f"Upload successful!")
        print(f"Contents length: {len(contents)}")
        print(f"File path: {file_path}")
        
        # 测试获取文件
        try:
            download_path = Storage.get_file(file_path)
            print(f"Get file successful! Download path: {download_path}")
        except Exception as e:
            print(f"Get file failed: {e}")
        
        # 测试删除文件
        try:
            Storage.delete_file(file_path)
            print(f"Delete file successful!")
        except Exception as e:
            print(f"Delete file failed: {e}")
            
    except Exception as e:
        print(f"Upload failed: {e}")

if __name__ == "__main__":
    test_storage()