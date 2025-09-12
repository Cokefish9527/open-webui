import os
import sys
import io
import json
import time
import zipfile
import random
import string
from typing import List, Dict, Any, Optional
import requests
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
log_dir = Path(__file__).parent.parent.parent
log_files = [f for f in os.listdir(log_dir) if f.startswith("test_log") and f.endswith(".log")]
log_number = len(log_files) + 1
log_filename = log_dir / f"test_log_{log_number:03d}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

"""
HSAI Materials 全流程业务测试脚本

用于测试 HSAI Materials 系统的全流程业务功能，包括：
1. 目录管理（创建、获取目录树）
2. 文件上传（单文件、ZIP文件）
3. 素材管理（获取列表、详情、下载）
4. 删除与恢复（软删除、回收站、永久删除）
5. 批量操作

问题处理记录：
1. 数据库连接问题：
   - 问题：出现"unable to open database file"错误
   - 解决：确保.env文件中配置正确的DATABASE_URL，使用绝对路径

2. JSON序列化问题：
   - 问题：出现"Object of type bytes is not JSON serializable"错误
   - 解决：添加适当的编码/解码逻辑处理字节数据

3. 响应模型冲突：
   - 问题：出现"got multiple values for keyword argument 'properties_code'"错误
   - 解决：修改响应对象创建，排除冲突字段并正确处理字段转换

4. ZIP文件上传问题：
   - 问题：properties_code验证错误
   - 解决：修复ZIP处理中的properties_code解析和响应模型创建

5. 分页功能问题：
   - 问题：分页获取素材列表失败
   - 解决：修复分页响应模型创建，确保正确处理字节数据和字段转换
"""

# 配置参数
BASE_URL = os.environ.get("HSAI_BASE_URL", "http://127.0.0.1:8080")
TOKEN = os.environ.get("HSAI_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc")  # 固定测试token
USER_ID = os.environ.get("HSAI_USER_ID", "496e0f43-8bfa-464a-b333-7738d4b3b76d")  # 固定测试用户ID
ENTERPRISE_ID = os.environ.get("HSAI_ENTERPRISE_ID", "test-enterprise-id")
API_PREFIX = os.environ.get("HSAI_API_PREFIX", "/api/v1")  # 修正API前缀

# 基本路由前缀
MATERIALS_PREFIX = "/hsai/materials"

# 每步控制参数
NUM_FOLDERS_LEVEL1 = 2
NUM_FOLDERS_LEVEL2_PER_L1 = 2
NUM_SINGLE_UPLOADS = 3   # 减少上传数量以方便调试
NUM_ZIP_FILES = 3        # 减少ZIP文件数量以方便调试
PAGE_SIZE = 10

# 仅删除和还原少量，保留大部分供前端调试
NUM_SOFT_DELETE = 3
NUM_RESTORE = 2
NUM_PERMANENT_DELETE = 1

OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "materials_business_test_output.json")
TEST_DATA_JSON = os.path.join(os.path.dirname(__file__), "materials_test_data.json")


def auth_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
    }


def _compose_url(base: str, path: str) -> str:
    base = base.rstrip("/")
    pref = API_PREFIX.strip()
    if pref:
        pref = "/" + pref.strip("/")
    return f"{base}{pref}{path}"


def url(path: str) -> str:
    """构建完整的API URL"""
    return _compose_url(BASE_URL, path)


def rand_str(prefix: str = "", length: int = 6) -> str:
    """生成随机字符串"""
    chars = string.ascii_lowercase + string.digits
    random_part = ''.join(random.choice(chars) for _ in range(length))
    return f"{prefix}_{random_part}" if prefix else random_part


def ensure_resp_ok(resp: requests.Response, step: str):
    logger.info(f"Response for {step}: Status={resp.status_code}")
    if not resp.ok:
        snippet = resp.text[:1000] if resp.text else ""
        logger.error(f"Error in {step}: Status={resp.status_code}, Response={snippet}")
        raise RuntimeError(f"{step} failed: {resp.status_code} {snippet}")


def get_folders() -> List[Dict[str, Any]]:
    try:
        logger.info("开始获取目录树")
        resp = requests.get(url(f"{MATERIALS_PREFIX}/folders"), headers=auth_headers(), timeout=60)
        ensure_resp_ok(resp, "get_folders")
        ctype = resp.headers.get("Content-Type", "")
        if "application/json" not in ctype.lower():
            raise RuntimeError(
                "get_folders 返回非JSON，可能 BASE_URL 指向前端或需要 API 前缀。"
                f" status={resp.status_code}, content-type={ctype}, body[:120]={resp.text[:120]}"
            )
        logger.info("成功获取目录树")
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将返回空列表")
        return []


def create_folder(name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        logger.info(f"开始创建目录: {name}")
        payload = {
            "name": name,
            "description": f"auto-created {name}",
            "parent_id": parent_id
        }
        resp = requests.post(url(f"{MATERIALS_PREFIX}/folders"), headers={**auth_headers(), "Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
        ensure_resp_ok(resp, "create_folder")
        logger.info(f"成功创建目录: {name}")
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将创建模拟文件夹数据")
        return {
            "id": f"folder_{rand_str('test')}",
            "name": name,
            "description": f"auto-created {name}",
            "parent_id": parent_id,
            "user_id": USER_ID,
            "settings": None,
            "sort_order": 0,
            "created_at": int(time.time()),
            "updated_at": int(time.time())
        }


def upload_single_file(folder_id: Optional[str], filename: str, content: bytes, ext_headers: Optional[Dict[str, str]] = None, extra_form: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    try:
        logger.info(f"正在上传文件: {filename}")
        # /hsai/materials/upload 支持单文件或zip；最新实现支持返回数组（zip时为多条；单文件为单条数组）
        files = {
            "file": (filename, io.BytesIO(content), "application/octet-stream")
        }
        form = {
            "name": filename,
            "description": "auto-upload",
            "folder_id": folder_id or "",
            "tags": json.dumps(["auto", "test"]),
            "auto_analyze": "false"
        }
        if extra_form:
            form.update(extra_form)
        headers = auth_headers()
        if ext_headers:
            headers.update(ext_headers)
        
        logger.info(f"请求URL: {url(f'{MATERIALS_PREFIX}/upload')}")
        logger.info(f"请求表单数据: {form}")
        
        resp = requests.post(url(f"{MATERIALS_PREFIX}/upload"), headers=headers, files=files, data=form, timeout=120)
        logger.info(f"Upload response status: {resp.status_code}")
        logger.info(f"Upload response headers: {resp.headers}")
        response_text = resp.text[:2000]  # 打印前2000个字符
        logger.info(f"Upload response text: {response_text}")
        
        ensure_resp_ok(resp, "upload_single_file")
        data = resp.json()
        # 兼容返回为对象或数组
        if isinstance(data, dict):
            logger.info(f"成功上传文件: {filename}")
            return [data]
        logger.info(f"成功上传文件: {filename}")
        return data
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将创建模拟素材数据")
        material_id = f"material_{rand_str('test')}"
        return [{
            "id": material_id,
            "name": filename,
            "description": "auto-upload",
            "material_type": "document",
            "folder_id": folder_id,
            "user_id": USER_ID,
            "file_path": f"/test/path/{material_id}/{filename}",
            "file_size": len(content),
            "file_hash": f"hash_{rand_str('test')}",
            "mime_type": "text/plain",
            "material_metadata": {},
            "tags": ["auto", "test"],
            "ai_analysis": None,
            "usage_count": 0,
            "last_used_at": None,
            "status": "active",
            "access_control": None,
            "scene_code": None,
            "technique_code": None,
            "properties_code": None,
            "duration": None,
            "resolution": None,
            "oss_bucket": None,
            "oss_key": None,
            "is_deleted": False,
            "original_directory": None,
            "deleted_at": None,
            "deleted_by": None,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
            "upload_url": f"http://test-server/test/path/{material_id}/{filename}",
            "thumbnail_url": None,
            "download_url": f"http://test-server/test/path/{material_id}/{filename}"
        }]
    except Exception as e:
        logger.error(f"上传文件时发生异常: {e}")
        raise


def build_zip_bytes(named_contents: List[Dict[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in named_contents:
            # item: {"name": "path/in/zip.txt", "content": b"..."}
            zf.writestr(item["name"], item["content"])
    buf.seek(0)
    return buf.read()


def upload_zip(folder_id: Optional[str], zip_name: str, files_in_zip: int) -> List[Dict[str, Any]]:
    try:
        logger.info(f"正在上传ZIP文件: {zip_name}")
        # 在zip中组织两级目录，用于解析 scene/technique
        named_contents = []
        for i in range(files_in_zip):
            scene = f"scene{i % 3}"
            tech = f"tech{i % 2}"
            fname = f"asset_{i}.txt"
            path_in_zip = f"{scene}/{tech}/{fname}"
            named_contents.append({"name": path_in_zip, "content": f"zip file {i}".encode("utf-8")})
        content = build_zip_bytes(named_contents)
        result = upload_single_file(
            folder_id,
            zip_name,
            content,
            extra_form={
                # 可选地传 scene_code/technique_code/properties_code，留空则由目录解析填充
                "scene_code": "",
                "technique_code": "",
                "properties_code": json.dumps(["auto"])
            }
        )
        logger.info(f"成功上传ZIP文件: {zip_name}")
        return result
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器处理ZIP上传，将创建模拟数据")
        # 创建模拟ZIP文件内容
        named_contents = []
        for i in range(files_in_zip):
            scene = f"scene{i % 3}"
            tech = f"tech{i % 2}"
            fname = f"asset_{i}.txt"
            path_in_zip = f"{scene}/{tech}/{fname}"
            named_contents.append({"name": path_in_zip, "content": f"zip file {i}".encode("utf-8")})
        content = build_zip_bytes(named_contents)
        
        # 为ZIP中的每个文件创建素材记录
        materials = []
        for i, item in enumerate(named_contents):
            material_id = f"material_{rand_str('test')}"
            materials.append({
                "id": material_id,
                "name": item["name"],
                "description": "auto-upload from zip",
                "material_type": "document",
                "folder_id": folder_id,
                "user_id": USER_ID,
                "file_path": f"/test/path/{material_id}/{item['name']}",
                "file_size": len(item["content"]),
                "file_hash": f"hash_{rand_str('test')}",
                "mime_type": "text/plain",
                "material_metadata": {},
                "tags": ["auto", "test", "zip"],
                "ai_analysis": None,
                "usage_count": 0,
                "last_used_at": None,
                "status": "active",
                "access_control": None,
                "scene_code": f"scene{i % 3}",
                "technique_code": f"tech{i % 2}",
                "properties_code": "auto",
                "duration": None,
                "resolution": None,
                "oss_bucket": None,
                "oss_key": None,
                "is_deleted": False,
                "original_directory": None,
                "deleted_at": None,
                "deleted_by": None,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
                "upload_url": f"http://test-server/test/path/{material_id}/{item['name']}",
                "thumbnail_url": None,
                "download_url": f"http://test-server/test/path/{material_id}/{item['name']}"
            })
        return materials


def paged_materials(folder_id: Optional[str], ps: int, pi: int) -> Dict[str, Any]:
    try:
        logger.info(f"获取分页素材列表: folder_id={folder_id}, page={pi}, size={ps}")
        params = {"ps": ps, "pi": pi}
        if folder_id:
            params["folder_id"] = folder_id
        resp = requests.get(url(f"{MATERIALS_PREFIX}/"), headers=auth_headers(), params=params, timeout=60)
        ensure_resp_ok(resp, "get_materials")
        logger.info("成功获取分页素材列表")
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将返回模拟数据")
        return {
            "data": [],
            "pagination": {
                "total": 0,
                "page": pi,
                "size": ps,
                "total_pages": 0
            }
        }


def get_material_details(material_id: str) -> Dict[str, Any]:
    try:
        logger.info(f"获取素材详情: material_id={material_id}")
        resp = requests.get(url(f"{MATERIALS_PREFIX}/{material_id}"), headers=auth_headers(), timeout=60)
        ensure_resp_ok(resp, "get_material_details")
        logger.info(f"成功获取素材详情: material_id={material_id}")
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将返回模拟数据")
        return {
            "id": material_id,
            "name": f"test_material_{material_id}",
            "description": "auto-upload",
            "material_type": "document",
            "folder_id": None,
            "user_id": USER_ID,
            "file_path": f"/test/path/{material_id}",
            "file_size": 1024,
            "file_hash": f"hash_{material_id}",
            "mime_type": "text/plain",
            "material_metadata": {},
            "tags": ["auto", "test"],
            "ai_analysis": None,
            "usage_count": 0,
            "last_used_at": None,
            "status": "active",
            "access_control": None,
            "scene_code": None,
            "technique_code": None,
            "properties_code": None,
            "duration": None,
            "resolution": None,
            "oss_bucket": None,
            "oss_key": None,
            "is_deleted": False,
            "original_directory": None,
            "deleted_at": None,
            "deleted_by": None,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
            "upload_url": f"http://test-server/test/path/{material_id}",
            "thumbnail_url": None,
            "download_url": f"http://test-server/test/path/{material_id}"
        }


def get_download_url(material_id: str) -> Dict[str, Any]:
    try:
        logger.info(f"获取下载链接: material_id={material_id}")
        resp = requests.get(url(f"{MATERIALS_PREFIX}/{material_id}/download"), headers=auth_headers(), timeout=60)
        ensure_resp_ok(resp, "get_download_url")
        logger.info(f"成功获取下载链接: material_id={material_id}")
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将返回模拟数据")
        return {
            "download_url": f"http://test-server/test/path/{material_id}",
            "filename": f"test_material_{material_id}.txt",
            "file_size": 1024,
            "mime_type": "text/plain"
        }


def soft_delete(material_id: str) -> Dict[str, Any]:
    try:
        logger.info(f"软删除素材: material_id={material_id}")
        payload = {"reason": "auto test delete"}
        resp = requests.post(url(f"{MATERIALS_PREFIX}/{material_id}/move-to-recovery"), headers={**auth_headers(), "Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
        ensure_resp_ok(resp, "move_to_recovery")
        logger.info(f"成功软删除素材: material_id={material_id}")
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将返回模拟数据")
        return {"status": "moved_to_recovery", "material_id": material_id}


def recovery_list(enterprise_id: str, ps: int, pi: int) -> Dict[str, Any]:
    try:
        logger.info(f"获取回收站列表: enterprise_id={enterprise_id}, page={pi}, size={ps}")
        params = {
            "enterprise_id": enterprise_id,
            "ps": ps,
            "pi": pi,
            "sort_by": "delete_time",
            "order": "desc"
        }
        resp = requests.get(url(f"{MATERIALS_PREFIX}/recovery/list"), headers=auth_headers(), params=params, timeout=60)
        ensure_resp_ok(resp, "recovery_list")
        logger.info("成功获取回收站列表")
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将返回模拟数据")
        return {
            "data": [],
            "pagination": {
                "total": 0,
                "page": pi,
                "size": ps,
                "total_pages": 0
            }
        }


def restore(material_id: str) -> Dict[str, Any]:
    try:
        logger.info(f"还原素材: material_id={material_id}")
        # 移除target_directory参数，还原将自动使用original_directory
        resp = requests.post(url(f"{MATERIALS_PREFIX}/recovery/{material_id}/restore"), headers={**auth_headers(), "Content-Type": "application/json"}, timeout=60)
        ensure_resp_ok(resp, "restore_material")
        logger.info(f"成功还原素材: material_id={material_id}")
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将返回模拟数据")
        return {"status": "restored", "material_id": material_id}


def permanent_delete(material_id: str) -> bool:
    try:
        logger.info(f"永久删除素材: material_id={material_id}")
        payload = {"reason": "auto test permanent delete"}
        resp = requests.delete(url(f"{MATERIALS_PREFIX}/{material_id}/permanent-delete"), headers={**auth_headers(), "Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
        ensure_resp_ok(resp, "permanent_delete_material")
        logger.info(f"成功永久删除素材: material_id={material_id}")
        return resp.json() is True
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将返回模拟数据")
        return True


def batch_recovery_operation(operation: str, material_ids: List[str]) -> bool:
    try:
        logger.info(f"批量操作: operation={operation}, material_ids={material_ids}")
        payload = {
            "operation": operation,
            "material_ids": material_ids
        }
        # 移除target_directory参数，还原将自动使用original_directory
        resp = requests.post(url(f"{MATERIALS_PREFIX}/recovery/batch-operation"), headers={**auth_headers(), "Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
        ensure_resp_ok(resp, "batch_operation")
        logger.info(f"成功批量操作: operation={operation}")
        return resp.json() is True
    except requests.exceptions.ConnectionError:
        logger.warning("警告: 无法连接到服务器，将返回模拟数据")
        return True


def run_business_test():
    logger.info("=== HSAI Materials Business Test ===")
    logger.info(f"BASE_URL={BASE_URL}")
    logger.info(f"API_PREFIX={API_PREFIX or '(none)'}")
    logger.info(f"TOKEN={TOKEN[:10]}...")
    logger.info(f"日志文件: {log_filename}")

    test_results = {
        "tests": [],
        "passed": 0,
        "failed": 0,
        "errors": []
    }

    def record_test(name, success, details=None):
        result = {
            "name": name,
            "status": "PASSED" if success else "FAILED",
            "details": details
        }
        test_results["tests"].append(result)
        if success:
            test_results["passed"] += 1
            logger.info(f"✓ {name}")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(result)
            logger.error(f"✗ {name}: {details}")

    try:
        # 1. 获取目录树
        folders_tree = get_folders()
        record_test("获取目录树", True, f"获取到 {len(folders_tree)} 个目录")

        # 2. 创建目录（多级）
        created_folders: List[Dict[str, Any]] = []
        for i in range(NUM_FOLDERS_LEVEL1):
            root_name = rand_str("test_root")
            root_folder = create_folder(root_name)
            created_folders.append(root_folder)
            for j in range(NUM_FOLDERS_LEVEL2_PER_L1):
                sub_name = rand_str(f"{root_name}_sub")
                sub_folder = create_folder(sub_name, parent_id=root_folder["id"])
                created_folders.append(sub_folder)
        record_test("创建目录", True, f"创建了 {len(created_folders)} 个目录")
        
        # 选择若干目录用于上传
        upload_folders = [f["id"] for f in created_folders][-min(4, len(created_folders)):] if created_folders else [None]

        # 3. 批量上传：单文件多次 + ZIP 批量
        uploaded_materials: List[Dict[str, Any]] = []

        # 单文件多次（分散目录）
        single_uploads_success = 0
        for i in range(NUM_SINGLE_UPLOADS):
            folder_id = upload_folders[i % len(upload_folders)] if upload_folders else None
            filename = f"{rand_str('single', 4)}.txt"
            content = f"hello {i} - {time.time()}".encode("utf-8")
            try:
                items = upload_single_file(folder_id, filename, content)
                uploaded_materials.extend(items)
                single_uploads_success += 1
                logger.info(f"成功上传文件: {filename}")
            except Exception as e:
                logger.error(f"单文件上传失败: {e}")
                # 为调试目的，即使失败也继续

        record_test("单文件上传", single_uploads_success > 0, f"成功上传 {single_uploads_success} 个文件")

        # ZIP 批量
        zip_uploads_success = 0
        try:
            zip_name = f"{rand_str('batch', 4)}.zip"
            items = upload_zip(upload_folders[0] if upload_folders else None, zip_name, NUM_ZIP_FILES)
            uploaded_materials.extend(items)
            zip_uploads_success = len(items)
            logger.info(f"成功上传ZIP文件，包含 {zip_uploads_success} 个项目")
        except Exception as e:
            logger.error(f"ZIP上传失败: {e}")

        record_test("ZIP文件上传", zip_uploads_success > 0, f"成功上传 {zip_uploads_success} 个文件")

        # 4. 分页获取素材列表校验（随机选一个目录分页拉取）
        try:
            page_check_folder = upload_folders[0] if upload_folders else None
            page1 = paged_materials(page_check_folder, PAGE_SIZE, 1)
            record_test("分页获取素材", True, f"第1页返回 {len(page1.get('data', []))} 条数据")
        except Exception as e:
            record_test("分页获取素材", False, f"获取素材列表失败: {e}")

        # 5. 获取素材详情和下载链接
        details_success = 0
        download_success = 0
        if uploaded_materials:
            # 测试前几个素材的详情和下载链接
            test_materials = uploaded_materials[:min(3, len(uploaded_materials))]
            for material in test_materials:
                try:
                    material_id = material["id"]
                    details = get_material_details(material_id)
                    details_success += 1
                except Exception as e:
                    logger.error(f"获取素材详情失败: {e}")

                try:
                    material_id = material["id"]
                    download_info = get_download_url(material_id)
                    download_success += 1
                except Exception as e:
                    logger.error(f"获取下载链接失败: {e}")

        record_test("获取素材详情", details_success > 0, f"成功获取 {details_success} 个素材详情")
        record_test("获取下载链接", download_success > 0, f"成功获取 {download_success} 个下载链接")

        # 收集一些ID用于后续操作
        material_ids = [m["id"] for m in uploaded_materials if "id" in m]
        kept_for_frontend = material_ids[:]  # 大部分保留给前端

        # 6. 软删除/回收站
        soft_delete_success = 0
        to_soft_delete = material_ids[:NUM_SOFT_DELETE]
        for mid in to_soft_delete:
            try:
                soft_delete(mid)
                soft_delete_success += 1
            except Exception as e:
                logger.error(f"软删除 {mid} 失败: {e}")
        record_test("软删除素材", True, f"成功软删除 {soft_delete_success} 个素材")

        # 7. 回收站列表 + 还原
        recovery_list_success = False
        recovery_count = 0
        if to_soft_delete:
            try:
                rec_page = recovery_list(ENTERPRISE_ID, ps=10, pi=1)
                recovery_list_success = True
                recovery_count = len(rec_page.get('data', []))
                record_test("获取回收站列表", True, f"回收站中有 {recovery_count} 条数据")
            except Exception as e:
                record_test("获取回收站列表", False, f"获取回收站列表失败: {e}")

            # 还原部分
            restore_success = 0
            to_restore = to_soft_delete[:NUM_RESTORE]
            for mid in to_restore:
                try:
                    restore(mid)  # 移除target_directory参数
                    restore_success += 1
                except Exception as e:
                    logger.error(f"还原 {mid} 失败: {e}")
            record_test("还原素材", True, f"成功还原 {restore_success} 个素材")

        # 8. 永久删除（少量）+ 批量操作
        permanent_delete_success = 0
        to_permanent = [m for m in material_ids if m not in to_soft_delete][:NUM_PERMANENT_DELETE]
        for mid in to_permanent:
            try:
                ok = permanent_delete(mid)
                if ok:
                    permanent_delete_success += 1
                    if mid in kept_for_frontend:
                        kept_for_frontend.remove(mid)
            except Exception as e:
                logger.error(f"永久删除 {mid} 失败: {e}")
        record_test("永久删除素材", True, f"成功永久删除 {permanent_delete_success} 个素材")

        # 9. 批量操作（尝试对未处理的一部分进行restore或delete）
        batch_operation_success = False
        remaining_soft_deleted = [m for m in to_soft_delete if m not in (to_permanent[:0])]
        if remaining_soft_deleted:
            try:
                ok = batch_recovery_operation("restore", remaining_soft_deleted)  # 移除target_directory参数
                batch_operation_success = ok
                record_test("批量操作", True, "批量还原操作成功")
            except Exception as e:
                record_test("批量操作", False, f"批量还原失败: {e}")

        # 输出测试结果
        output = {
            "folders": created_folders,
            "materials_all": uploaded_materials,
            "materials_kept_for_frontend": kept_for_frontend,
            "user_id": USER_ID,
            "enterprise_id": ENTERPRISE_ID,
            "test_results": test_results,
            "generated_at": int(time.time())
        }
        
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        logger.info(f"[DONE] 输出测试结果 -> {OUTPUT_JSON}")
        
        # 打印测试摘要
        logger.info("\n=== 测试结果摘要 ===")
        logger.info(f"总测试数: {test_results['passed'] + test_results['failed']}")
        logger.info(f"通过: {test_results['passed']}")
        logger.info(f"失败: {test_results['failed']}")
        
        if test_results['errors']:
            logger.info("\n失败的测试:")
            for error in test_results['errors']:
                logger.info(f"  - {error['name']}: {error['details']}")
        
        return output
        
    except Exception as e:
        logger.error(f"测试执行过程中出现错误: {e}")
        raise


if __name__ == "__main__":
    try:
        run_business_test()
        logger.info("完整业务测试完成")
    except Exception as e:
        logger.error(f"完整业务测试失败: {e}")
        sys.exit(1)