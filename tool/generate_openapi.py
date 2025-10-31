"""
离线生成 openapi.json。
- 通过导入 backend/open_webui/main.py 的 FastAPI app 对象，调用 get_openapi() 输出到项目根目录。
- 避免运行服务，确保在本地脚本环境完成再生。
"""
import json
import os
import sys
from pathlib import Path

from fastapi.openapi.utils import get_openapi


def resolve_app():
    # 将 backend 目录加入 sys.path，保证可以导入 open_webui 包
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    # 延迟导入以应用 sys.path
    from open_webui.main import app  # type: ignore

    return app


def main():
    app = resolve_app()
    openapi_schema = get_openapi(
        title=app.title if getattr(app, "title", None) else "Open WebUI",
        version=getattr(app, "version", "0.1.0"),
        routes=app.routes,
    )
    out_path = Path(__file__).resolve().parents[1] / "openapi.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, ensure_ascii=False, indent=2)
    print(f"✓ openapi.json 已生成：{out_path}")


if __name__ == "__main__":
    main()

