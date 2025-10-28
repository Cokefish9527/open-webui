import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

if "DATABASE_URL" not in os.environ:
    if ENV_PATH.exists():
        with ENV_PATH.open("r", encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("DATABASE_URL="):
                    value = line.split("=", 1)[1].strip().strip("'\"")
                    if value:
                        os.environ["DATABASE_URL"] = value
                    break

if "DATABASE_URL" not in os.environ:
    default_db_path = Path(__file__).resolve().parent / "data" / "webui.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{default_db_path.as_posix()}"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "open_webui.main:app",
        host="0.0.0.0",
        port=8080,
        forwarded_allow_ips="*",
        workers=1,
        ws="auto"
    )
