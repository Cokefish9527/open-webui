import json
from pathlib import Path



def normalize_tags(tags):
    if not tags:
        return tags
    mapping = {
        "billing": "计费管理", "计费管理": "计费管理", "�Ʒѹ���": "计费管理",
        "HSAI ��Ŀ����": "HSAI 项目管理", "HSAI 项目管理": "HSAI 项目管理", "HSAI ???????": "HSAI 项目管理",
        "organizations": "组织管理", "组织管理": "组织管理", "��֯����": "组织管理",
        "chats": "对话管理", "对话管理": "对话管理", "�Ի�����": "对话管理",
        "auths": "认证与授权", "认证与授权": "认证与授权", "��֤����Ȩ": "认证与授权",
        "users": "用户管理", "用户管理": "用户管理", "�û�����": "用户管理",
        "knowledge": "知识库管理", "知识库管理": "知识库管理", "֪ʶ�����": "知识库管理",
        "files": "文件管理", "文件管理": "文件管理", "�ļ�����": "文件管理",
        "models": "模型管理", "模型管理": "模型管理",
        "configs": "配置管理", "配置管理": "配置管理",
        "pipelines": "管线管理", "管线管理": "管线管理",
        "tasks": "任务管理", "任务管理": "任务管理",
    }
    canonical_order = [
        "计费管理", "HSAI 项目管理", "组织管理", "对话管理", "认证与授权", "用户管理",
        "知识库管理", "文件管理", "模型管理", "配置管理", "管线管理", "任务管理",
    ]
    mapped = [mapping.get(t, t) for t in tags]
    s = set(mapped)
    for c in canonical_order:
        if c in s:
            return [c]
    return list(s)
def patch_operation(path, method, op):
    # 标签统一
    op["tags"] = normalize_tags(op.get("tags", []))

    # 组织管理中文描述补齐
    if path.startswith("/api/v1/organizations"):
        if path == "/api/v1/organizations/" and method == "get":
            op["summary"] = "获取组织列表"
            op["description"] = "分页获取组织列表，仅系统管理员可访问。参数：page（页码，>=1），size（页大小，1-100）。返回包含分页信息的组织列表。"
        if path == "/api/v1/organizations/" and method == "post":
            op["summary"] = "创建组织"
            op["description"] = "创建新的组织，仅系统管理员可访问。"
        if path == "/api/v1/organizations/{organization_id}" and method == "get":
            op["summary"] = "获取组织详情"
            op["description"] = "按 ID 获取组织详情，需具备该组织的访问权限。未找到返回 404。"
        if path == "/api/v1/organizations/{organization_id}" and method == "post":
            op["summary"] = "更新组织信息"
            op["description"] = "更新指定组织的基础信息，需组织管理员或系统管理员权限。"
        if path == "/api/v1/organizations/{organization_id}" and method == "delete":
            op["summary"] = "删除组织"
            op["description"] = "删除指定组织，仅系统管理员可访问。若组织下仍有关联用户或项目，将返回 400。"
        if path == "/api/v1/organizations/{organization_id}/users" and method == "get":
            op["summary"] = "获取组织用户列表"
            op["description"] = "分页获取指定组织的用户列表，需组织访问权限。参数：page，size。"
        if path == "/api/v1/organizations/{organization_id}/users/{user_id}" and method == "post":
            op["summary"] = "将用户加入组织"
            op["description"] = "将指定用户加入组织并可设置其为组织管理员。"
        if path == "/api/v1/organizations/{organization_id}/users/{user_id}" and method == "delete":
            op["summary"] = "将用户从组织移除"
            op["description"] = "从组织中移除指定用户，需组织管理员或系统管理员权限。不可移除自己。"

    # HSAI 项目管理中文化补齐（关键两个接口）
    if path == "/api/v1/hsai/projects/{project_id}/tasks" and method == "get":
        op["summary"] = "获取项目任务列表"
        op["description"] = "获取指定项目下的所有任务（含主要任务与循环任务）。需要项目所属用户访问权限。"
        op["tags"] = ["HSAI 项目管理"]
    if path == "/api/v1/hsai/projects/{project_id}/summary" and method == "get":
        op["summary"] = "项目任务摘要"
        op["description"] = "返回项目概要（蓝图版本/同步状态/计划统计）、主要任务完成度、循环任务条目与近期状态日志等。"
        op["tags"] = ["HSAI 项目管理"]


def main():
    p = Path("openapi.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    for path, methods in data.get("paths", {}).items():
        for method, op in list(methods.items()):
            patch_operation(path, method.lower(), op)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("openapi.json 已规范化（标签与中文描述）")


if __name__ == "__main__":
    main()

