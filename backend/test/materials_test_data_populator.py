import os
import sys
import json
import time
import random
import string
import zipfile
import requests
from io import BytesIO
from typing import List, Dict, Any, Optional
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 从环境变量或默认值获取配置
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8080")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")
TOKEN = os.environ.get("TOKEN", "")
ENTERPRISE_ID = os.environ.get("ENTERPRISE_ID", "test-enterprise-id")

# 构建完整URL
def url(path: str) -> str:
    """构建完整的API URL"""
    return f"{BASE_URL}{API_PREFIX}{path}"

# 生成随机字符串
def rand_str(prefix: str = "", length: int = 6) -> str:
    """生成随机字符串"""
    chars = string.ascii_lowercase + string.digits
    random_part = ''.join(random.choice(chars) for _ in range(length))
    return f"{prefix}_{random_part}" if prefix else random_part

# 构建ZIP文件
def build_zip_bytes(named_contents: List[Dict[str, Any]]) -> bytes:
    """构建包含指定内容的ZIP文件字节数据"""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in named_contents:
            zf.writestr(item["name"], item["content"])
    buffer.seek(0)
    return buffer.read()

# HTTP请求头
def auth_headers() -> Dict[str, str]:
    """生成认证请求头"""
    return {
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "HSAI Materials Test Data Populator/1.0"
    }

# 确保响应成功
def ensure_resp_ok(resp: requests.Response, operation: str) -> None:
    """确保HTTP响应成功"""
    if resp.status_code >= 400:
        error_msg = f"{operation} failed: {resp.status_code} {resp.text}"
        raise Exception(error_msg)

# 获取目录树
def get_folders() -> Dict[str, Any]:
    """获取目录树结构"""
    resp = requests.get(url("/hsai/material-folders/tree"), headers=auth_headers(), timeout=60)
    ensure_resp_ok(resp, "get_folders")
    return resp.json()

# 创建目录
def create_folder(name: str, parent_id: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    """创建目录"""
    data = {
        "name": name,
        "description": description or f"Auto-created folder for testing: {name}"
    }
    if parent_id:
        data["parent_id"] = parent_id
    
    resp = requests.post(url("/hsai/material-folders/"), headers=auth_headers(), json=data, timeout=60)
    ensure_resp_ok(resp, "create_folder")
    return resp.json()

# 上传单个文件
def upload_single_file(folder_id: str, filename: str, content: bytes, 
                      description: str = "auto-upload", tags: Optional[List[str]] = None,
                      auto_analyze: bool = False, scene_code: str = "", 
                      technique_code: str = "", properties_code: Optional[str] = None) -> Dict[str, Any]:
    """上传单个文件"""
    files = {
        "file": (filename, content, "application/octet-stream")
    }
    
    data = {
        "name": filename,
        "description": description,
        "folder_id": folder_id,
        "tags": json.dumps(tags or ["auto", "test"]),
        "auto_analyze": str(auto_analyze).lower(),
        "scene_code": scene_code,
        "technique_code": technique_code
    }
    
    if properties_code:
        data["properties_code"] = properties_code
    
    resp = requests.post(url("/hsai/materials/upload"), headers=auth_headers(), files=files, data=data, timeout=60)
    ensure_resp_ok(resp, "upload_single_file")
    return resp.json()

# 主函数
def main():
    """主函数"""
    print("=== HSAI Materials Test Data Populator ===")
    print(f"BASE_URL={BASE_URL}")
    print(f"API_PREFIX={API_PREFIX}")
    print(f"TOKEN={TOKEN[:10]}..." if TOKEN else "TOKEN=(empty)")
    
    try:
        # 1. 获取目录树
        print("开始获取目录树")
        folders = get_folders()
        print("成功获取目录树")
        
        # 2. 创建测试目录
        print("开始创建测试目录")
        root_folder1 = create_folder(f"test_root_{rand_str()}")
        root_folder1_id = root_folder1["id"]
        print(f"成功创建目录: {root_folder1['name']}")
        
        sub_folder1 = create_folder(f"test_root_{rand_str('sub')}", root_folder1_id)
        print(f"成功创建目录: {sub_folder1['name']}")
        
        sub_folder2 = create_folder(f"test_root_{rand_str('sub')}", root_folder1_id)
        print(f"成功创建目录: {sub_folder2['name']}")
        
        root_folder2 = create_folder(f"test_root_{rand_str()}")
        root_folder2_id = root_folder2["id"]
        print(f"成功创建目录: {root_folder2['name']}")
        
        sub_folder3 = create_folder(f"test_root_{rand_str('sub')}", root_folder2_id)
        print(f"成功创建目录: {sub_folder3['name']}")
        
        sub_folder4 = create_folder(f"test_root_{rand_str('sub')}", root_folder2_id)
        print(f"成功创建目录: {sub_folder4['name']}")
        print("✓ 创建目录完成")
        
        # 3. 上传测试文件
        print("开始上传测试文件")
        
        # 上传单个文件
        for i in range(3):
            content = f"hello {i} - {int(time.time())}".encode("utf-8")
            filename = f"single_{rand_str('txt')}"
            result = upload_single_file(
                root_folder1_id,
                filename,
                content,
                tags=["auto", "test"]
            )
            print(f"成功上传文件: {filename}")
        
        # 上传ZIP文件
        zip_name = f"batch_{rand_str('zip')}"
        files_in_zip = 3
        named_contents = []
        for i in range(files_in_zip):
            scene = f"scene{i % 3}"
            tech = f"tech{i % 2}"
            fname = f"asset_{i}.txt"
            path_in_zip = f"{scene}/{tech}/{fname}"
            named_contents.append({"name": path_in_zip, "content": f"zip file {i}".encode("utf-8")})
        
        content = build_zip_bytes(named_contents)
        result = upload_single_file(
            root_folder1_id,
            zip_name,
            content,
            extra_form={
                # 可选地传 scene_code/technique_code/properties_code，留空则由目录解析填充
                "scene_code": "",
                "technique_code": "",
                "properties_code": json.dumps(["auto"])
            }
        )
        print(f"成功上传ZIP文件: {zip_name}")
        print(f"成功上传ZIP文件，包含 {len(result)} 个项目")
        print("✓ 文件上传完成")
        
        # 4. 输出测试数据报告
        test_data = {
            "test_folders": [
                root_folder1,
                sub_folder1,
                sub_folder2,
                root_folder2,
                sub_folder3,
                sub_folder4
            ],
            "test_files": [
                # 单文件信息可以在这里添加
            ],
            "test_time": int(time.time()),
            "test_config": {
                "base_url": BASE_URL,
                "api_prefix": API_PREFIX,
                "enterprise_id": ENTERPRISE_ID
            }
        }
        
        output_file = Path(__file__).parent / "materials_test_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 输出测试数据 -> {output_file}")
        print("测试数据填充完成")
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
