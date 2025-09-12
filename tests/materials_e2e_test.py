import os
import io
import json
import time
import zipfile
import random
import string
from typing import List, Dict, Any, Optional

import requests

"""
材料管理模块端到端测试脚本
覆盖流程：
1. 获取目录树
2. 创建目录（多级）
3. 批量上传素材（单文件多次 + ZIP 批量）生成 ≥ 20 条数据
4. 分页获取素材列表校验
5. 软删除/移入回收站
6. 回收站列表、还原
7. 永久删除、批量操作
测试结束输出可供前端调试的 folder_id 与 material_id 列表到 tests/materials_test_output.json

使用前请替换以下占位变量：
BASE_URL: 后端服务根地址，例如 http://localhost:3000 或 http://127.0.0.1:8080
TOKEN: Bearer Token（仅填写不含 'Bearer ' 的部分，脚本会自动加前缀）
USER_ID: 当前用户ID（与 Token 对应用户一致）
ENTERPRISE_ID: 企业ID（用于回收站列表接口）
"""

# ========= 配置占位 =========
BASE_URL = os.environ.get("HSAI_BASE_URL", "http://127.0.0.1:8080")
TOKEN = os.environ.get("HSAI_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5NmUwZjQzLThiZmEtNDY0YS1iMzMzLTc3MzhkNGIzYjc2ZCJ9.AOSB4IFwd37m4mpnir4bZ0l_GjJuTl9VVG2XrwYmCOc")  # 不含 'Bearer '
USER_ID = os.environ.get("HSAI_USER_ID", "496e0f43-8bfa-464a-b333-7738d4b3b76d")  # 修改为正确的用户ID
ENTERPRISE_ID = os.environ.get("HSAI_ENTERPRISE_ID", "2")
API_PREFIX = os.environ.get("HSAI_API_PREFIX", "/api/v1")

# 基本路由前缀
MATERIALS_PREFIX = "/hsai/materials"

# 每步控制参数
NUM_FOLDERS_LEVEL1 = 3
NUM_FOLDERS_LEVEL2_PER_L1 = 2
NUM_SINGLE_UPLOADS = 12   # 单文件多次上传数量
NUM_ZIP_FILES = 12        # ZIP 内文件数量
PAGE_SIZE = 10

# 仅删除和还原少量，保留大部分供前端调试
NUM_SOFT_DELETE = 3
NUM_RESTORE = 2
NUM_PERMANENT_DELETE = 1

OUTPUT_JSON = os.path.join("tests", "materials_test_output.json")


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
    return _compose_url(BASE_URL, path)


def rand_str(prefix: str, n: int = 6) -> str:
    s = "".join(random.choices(string.ascii_lowercase + string.digits, k=n))
    return f"{prefix}_{s}"


def ensure_resp_ok(resp: requests.Response, step: str):
    if not resp.ok:
        snippet = resp.text[:200] if resp.text else ""
        raise RuntimeError(f"{step} failed: {resp.status_code} {snippet}")


def get_folders() -> List[Dict[str, Any]]:
    resp = requests.get(url(f"{MATERIALS_PREFIX}/folders"), headers=auth_headers(), timeout=60)
    ensure_resp_ok(resp, "get_folders")
    ctype = resp.headers.get("Content-Type", "")
    if "application/json" not in ctype.lower():
        raise RuntimeError(
            "get_folders 返回非JSON，可能 BASE_URL 指向前端或需要 API 前缀。"
            f" status={resp.status_code}, content-type={ctype}, body[:120]={resp.text[:120]}"
        )
    return resp.json()


def create_folder(name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
    payload = {
        "name": name,
        "description": f"auto-created {name}",
        "parent_id": parent_id
    }
    resp = requests.post(url(f"{MATERIALS_PREFIX}/folders"), headers={**auth_headers(), "Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
    ensure_resp_ok(resp, "create_folder")
    return resp.json()


def upload_single_file(folder_id: Optional[str], filename: str, content: bytes, ext_headers: Optional[Dict[str, str]] = None, extra_form: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
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
    resp = requests.post(url(f"{MATERIALS_PREFIX}/upload"), headers=headers, files=files, data=form, timeout=120)
    print(f"Upload response status: {resp.status_code}")
    print(f"Upload response headers: {resp.headers}")
    print(f"Upload response text: {resp.text[:500]}")  # 打印前500个字符
    ensure_resp_ok(resp, "upload_single_file")
    data = resp.json()
    # 兼容返回为对象或数组
    if isinstance(data, dict):
        return [data]
    return data


def build_zip_bytes(named_contents: List[Dict[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in named_contents:
            # item: {"name": "path/in/zip.txt", "content": b"..."}
            zf.writestr(item["name"], item["content"])
    buf.seek(0)
    return buf.read()


def upload_zip(folder_id: Optional[str], zip_name: str, files_in_zip: int) -> List[Dict[str, Any]]:
    # 在zip中组织两级目录，用于解析 scene/technique
    named_contents = []
    for i in range(files_in_zip):
        scene = f"scene{i % 3}"
        tech = f"tech{i % 2}"
        fname = f"asset_{i}.txt"
        path_in_zip = f"{scene}/{tech}/{fname}"
        named_contents.append({"name": path_in_zip, "content": f"zip file {i}".encode("utf-8")})
    content = build_zip_bytes(named_contents)
    return upload_single_file(
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


def paged_materials(folder_id: Optional[str], ps: int, pi: int) -> Dict[str, Any]:
    params = {"ps": ps, "pi": pi}
    if folder_id:
        params["folder_id"] = folder_id
    resp = requests.get(url(f"{MATERIALS_PREFIX}/"), headers=auth_headers(), params=params, timeout=60)
    ensure_resp_ok(resp, "get_materials")
    return resp.json()


def soft_delete(material_id: str) -> Dict[str, Any]:
    payload = {"reason": "auto test delete"}
    resp = requests.post(url(f"{MATERIALS_PREFIX}/{material_id}/move-to-recovery"), headers={**auth_headers(), "Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
    ensure_resp_ok(resp, "move_to_recovery")
    return resp.json()


def recovery_list(enterprise_id: str, ps: int, pi: int) -> Dict[str, Any]:
    params = {
        "enterprise_id": enterprise_id,
        "ps": ps,
        "pi": pi,
        "sort_by": "delete_time",
        "order": "desc"
    }
    resp = requests.get(url(f"{MATERIALS_PREFIX}/recovery/list"), headers=auth_headers(), params=params, timeout=60)
    ensure_resp_ok(resp, "recovery_list")
    return resp.json()


def restore(material_id: str, target_directory: str) -> Dict[str, Any]:
    payload = {"target_directory": target_directory}
    resp = requests.post(url(f"{MATERIALS_PREFIX}/recovery/{material_id}/restore"), headers={**auth_headers(), "Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
    ensure_resp_ok(resp, "restore_material")
    return resp.json()


def permanent_delete(material_id: str) -> bool:
    payload = {"reason": "auto test permanent delete"}
    resp = requests.delete(url(f"{MATERIALS_PREFIX}/{material_id}/permanent-delete"), headers={**auth_headers(), "Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
    ensure_resp_ok(resp, "permanent_delete_material")
    return resp.json() is True


def batch_recovery_operation(operation: str, material_ids: List[str], target_directory: Optional[str] = None) -> bool:
    payload = {
        "operation": operation,
        "material_ids": material_ids
    }
    if operation == "restore":
        payload["target_directory"] = target_directory or "restored/auto"
    resp = requests.post(url(f"{MATERIALS_PREFIX}/recovery/batch-operation"), headers={**auth_headers(), "Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
    ensure_resp_ok(resp, "batch_operation")
    return resp.json() is True


def main():
    print("=== HSAI Materials E2E Test ===")
    print(f"BASE_URL={BASE_URL}")
    print(f"API_PREFIX={API_PREFIX or '(none)'}")
    if "REPLACE_WITH" in TOKEN or "REPLACE_WITH" in USER_ID or "REPLACE_WITH" in ENTERPRISE_ID:
        raise SystemExit("请先设置 TOKEN/USER_ID/ENTERPRISE_ID 或通过环境变量 HSAI_TOKEN/HSAI_USER_ID/HSAI_ENTERPRISE_ID 提供")

    # 1. 获取目录树
    folders_tree = get_folders()
    print(f"[1] 当前目录数: {len(folders_tree)}")

    # 2. 创建目录（多级）
    created_folders: List[Dict[str, Any]] = []
    for i in range(NUM_FOLDERS_LEVEL1):
        root_name = rand_str("auto_root")
        root_folder = create_folder(root_name)
        created_folders.append(root_folder)
        for j in range(NUM_FOLDERS_LEVEL2_PER_L1):
            sub_name = rand_str(f"{root_name}_sub")
            sub_folder = create_folder(sub_name, parent_id=root_folder["id"])
            created_folders.append(sub_folder)
    print(f"[2] 新建目录数: {len(created_folders)}")
    # 选择若干目录用于上传
    upload_folders = [f["id"] for f in created_folders][-min(4, len(created_folders)):] if created_folders else [None]

    # 3. 批量上传：单文件多次 + ZIP 批量
    uploaded_materials: List[Dict[str, Any]] = []

    # 单文件多次（分散目录）
    for i in range(NUM_SINGLE_UPLOADS):
        folder_id = upload_folders[i % len(upload_folders)] if upload_folders else None
        filename = f"{rand_str('single', 4)}.txt"
        content = f"hello {i} - {time.time()}".encode("utf-8")
        items = upload_single_file(folder_id, filename, content)
        uploaded_materials.extend(items)

    # ZIP 批量
    zip_name = f"{rand_str('batch', 4)}.zip"
    items = upload_zip(upload_folders[0] if upload_folders else None, zip_name, NUM_ZIP_FILES)
    uploaded_materials.extend(items)

    print(f"[3] 上传素材数: {len(uploaded_materials)} (目标≥20)")

    # 4. 分页获取素材列表校验（随机选一个目录分页拉取）
    page_check_folder = upload_folders[0] if upload_folders else None
    page1 = paged_materials(page_check_folder, PAGE_SIZE, 1)
    print(f"[4] 分页获取 page=1 size={PAGE_SIZE}, 返回 {len(page1.get('data', []))} 条, total={page1.get('pagination', {}).get('total')}")

    # 收集一些ID用于后续操作
    material_ids = [m["id"] for m in uploaded_materials if "id" in m]
    kept_for_frontend = material_ids[:]  # 大部分保留给前端

    # 5. 软删除/回收站
    to_soft_delete = material_ids[:NUM_SOFT_DELETE]
    for mid in to_soft_delete:
        try:
            soft_delete(mid)
        except Exception as e:
            print(f"[5] soft delete {mid} 失败: {e}")
    print(f"[5] 软删除数量: {len(to_soft_delete)}")

    # 6. 回收站列表 + 还原
    if to_soft_delete:
        rec_page = recovery_list(ENTERPRISE_ID, ps=10, pi=1)
        print(f"[6] 回收站列表 count={len(rec_page.get('data', []))}, total={rec_page.get('pagination', {}).get('total')}")
        # 还原部分
        to_restore = to_soft_delete[:NUM_RESTORE]
        for mid in to_restore:
            try:
                restore(mid, target_directory="restored/auto")
            except Exception as e:
                print(f"[6] restore {mid} 失败: {e}")
        print(f"[6] 还原数量: {len(to_restore)}")

    # 7. 永久删除（少量）+ 批量操作（尝试对未处理的一部分进行restore或delete）
    to_permanent = [m for m in material_ids if m not in to_soft_delete][:NUM_PERMANENT_DELETE]
    for mid in to_permanent:
        try:
            ok = permanent_delete(mid)
            print(f"[7] 永久删除 {mid} -> {ok}")
            if ok and mid in kept_for_frontend:
                kept_for_frontend.remove(mid)
        except Exception as e:
            print(f"[7] permanent delete {mid} 失败: {e}")

    # 批量操作：对软删除列表的剩余部分执行批量还原
    remaining_soft_deleted = [m for m in to_soft_delete if m not in (to_permanent[:0])]
    if remaining_soft_deleted:
        try:
            ok = batch_recovery_operation("restore", remaining_soft_deleted, target_directory="restored/batch")
            print(f"[7] 批量还原 -> {ok}")
        except Exception as e:
            print(f"[7] 批量还原失败: {e}")

    # 输出前端可复用数据
    output = {
        "folders": created_folders,
        "materials_all": uploaded_materials,
        "materials_kept_for_frontend": kept_for_frontend,
        "user_id": USER_ID,
        "enterprise_id": ENTERPRISE_ID,
        "generated_at": int(time.time())
    }
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[DONE] 输出测试数据 -> {OUTPUT_JSON}")
    print("请将 BASE_URL/TOKEN/USER_ID/ENTERPRISE_ID 填入或以环境变量提供后运行：")
    print("  PowerShell 示例：")
    print('  $env:HSAI_BASE_URL="http://localhost:3000"; $env:HSAI_TOKEN="..."; $env:HSAI_USER_ID="..."; $env:HSAI_ENTERPRISE_ID="..."; python tests/materials_e2e_test.py')


if __name__ == "__main__":
    main()