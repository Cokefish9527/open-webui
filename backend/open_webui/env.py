import importlib.metadata
import json
import logging
import os
import pkgutil
import sys
import shutil
from uuid import uuid4
from pathlib import Path

import markdown
from bs4 import BeautifulSoup
from open_webui.constants import ERROR_MESSAGES

####################################
# Load .env file
####################################

OPEN_WEBUI_DIR = Path(__file__).parent  # the path containing this file
print(OPEN_WEBUI_DIR)

BACKEND_DIR = OPEN_WEBUI_DIR.parent  # the path containing this file
BASE_DIR = BACKEND_DIR.parent  # the path containing the backend/

print(BACKEND_DIR)
print(BASE_DIR)

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(str(BASE_DIR / ".env")))
except ImportError:
    print("dotenv not installed, skipping...")

DOCKER = os.environ.get("DOCKER", "False").lower() == "true"

# device type embedding models - "cpu" (default), "cuda" (nvidia gpu required) or "mps" (apple silicon) - choosing this right can lead to better performance
USE_CUDA = os.environ.get("USE_CUDA_DOCKER", "false")

if USE_CUDA.lower() == "true":
    try:
        import torch

        assert torch.cuda.is_available(), "CUDA not available"
        DEVICE_TYPE = "cuda"
    except Exception as e:
        cuda_error = (
            "Error when testing CUDA but USE_CUDA_DOCKER is true. "
            f"Resetting USE_CUDA_DOCKER to false: {e}"
        )
        os.environ["USE_CUDA_DOCKER"] = "false"
        USE_CUDA = "false"
        DEVICE_TYPE = "cpu"
else:
    DEVICE_TYPE = "cpu"

try:
    import torch

    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        DEVICE_TYPE = "mps"
except Exception:
    pass

####################################
# LOGGING
####################################

GLOBAL_LOG_LEVEL = os.environ.get("GLOBAL_LOG_LEVEL", "").upper()
# Python 3.8 compatibility
level_names = {
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.FATAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'WARN': logging.WARN,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET
}
if GLOBAL_LOG_LEVEL in level_names:
    logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL, force=True)
else:
    GLOBAL_LOG_LEVEL = "INFO"

log = logging.getLogger(__name__)
log.info(f"GLOBAL_LOG_LEVEL: {GLOBAL_LOG_LEVEL}")

cuda_error = None
if "cuda_error" in locals():
    log.exception(cuda_error)
    del cuda_error

log_sources = [
    "AUDIO",
    "COMFYUI",
    "CONFIG",
    "DB",
    "IMAGES",
    "MAIN",
    "MODELS",
    "OLLAMA",
    "OPENAI",
    "RAG",
    "WEBHOOK",
    "SOCKET",
    "OAUTH",
]

SRC_LOG_LEVELS = {}

for source in log_sources:
    log_env_var = source + "_LOG_LEVEL"
    SRC_LOG_LEVELS[source] = os.environ.get(log_env_var, "").upper()
    if SRC_LOG_LEVELS[source] not in level_names:
        SRC_LOG_LEVELS[source] = GLOBAL_LOG_LEVEL
    log.info(f"{log_env_var}: {SRC_LOG_LEVELS[source]}")

log.setLevel(SRC_LOG_LEVELS["CONFIG"])

WEBUI_NAME = os.environ.get("WEBUI_NAME", "Open WebUI")
if WEBUI_NAME != "Open WebUI":
    WEBUI_NAME += " (Open WebUI)"

WEBUI_FAVICON_URL = "https://openwebui.com/favicon.png"

TRUSTED_SIGNATURE_KEY = os.environ.get("TRUSTED_SIGNATURE_KEY", "")

####################################
# ENV (dev,test,prod)
####################################

ENV = os.environ.get("ENV", "dev")

FROM_INIT_PY = os.environ.get("FROM_INIT_PY", "False").lower() == "true"

if FROM_INIT_PY:
    PACKAGE_DATA = {"version": importlib.metadata.version("open-webui")}
else:
    try:
        PACKAGE_DATA = json.loads((BASE_DIR / "package.json").read_text())
    except Exception:
        PACKAGE_DATA = {"version": "0.0.0"}

VERSION = PACKAGE_DATA["version"]
INSTANCE_ID = os.environ.get("INSTANCE_ID", str(uuid4()))


# Function to parse each section
def parse_section(section):
    items = []
    if section is None:
        return items
    for li in section.find_all("li"):
        # Extract raw HTML string
        raw_html = str(li)

        # Extract text without HTML tags
        text = li.get_text(separator=" ", strip=True)

        # Split into title and content
        parts = text.split(": ", 1)
        title = parts[0].strip() if len(parts) > 1 else ""
        content = parts[1].strip() if len(parts) > 1 else text

        items.append({"title": title, "content": content, "raw": raw_html})
    return items


try:
    changelog_path = BASE_DIR / "CHANGELOG_EXTRA.md"
    with open(str(changelog_path.absolute()), "r", encoding="utf8") as file:
        changelog_content = file.read()

except Exception:
    try:
        changelog_content = (
            pkgutil.get_data("open_webui", "CHANGELOG_EXTRA.md") or b""
        ).decode()
    except Exception:
        # 如果CHANGELOG_EXTRA.md不存在，尝试加载CHANGELOG.md
        try:
            changelog_path = BASE_DIR / "CHANGELOG.md"
            with open(str(changelog_path.absolute()), "r", encoding="utf8") as file:
                changelog_content = file.read()
        except Exception:
            try:
                changelog_content = (
                    pkgutil.get_data("open_webui", "CHANGELOG.md") or b""
                ).decode()
            except Exception:
                # 如果都不存在，使用默认内容
                changelog_content = "# Changelog\n\nNo changelog available."

# Convert markdown content to HTML
html_content = markdown.markdown(changelog_content)

# Parse the HTML content
soup = BeautifulSoup(html_content, "html.parser")

# Initialize JSON structure
changelog_json = {}

# Iterate over each version
for version in soup.find_all("h2"):
    version_text = version.get_text().strip()
    version_parts = version_text.split(" - ")
    version_number = version_parts[0][1:-1]  # Remove brackets
    
    # Handle case where date is not present
    if len(version_parts) > 1:
        date = version_parts[1]
    else:
        date = "Unknown Date"
    
    version_data = {"date": date}

    # Find the next sibling that is a h3 tag (section title)
    current = version.find_next_sibling()

    while current and current.name != "h2":
        if current.name == "h3":
            section_title = current.get_text().lower()  # e.g., "added", "fixed"
            next_sibling = current.find_next_sibling("ul")
            if next_sibling is not None:
                section_items = parse_section(next_sibling)
                version_data[section_title] = section_items

        # Move to the next element
        current = current.find_next_sibling()

    changelog_json[version_number] = version_data

CHANGELOG = changelog_json

####################################
# SAFE_MODE
####################################

SAFE_MODE = os.environ.get("SAFE_MODE", "false").lower() == "true"

####################################
# ENABLE_FORWARD_USER_INFO_HEADERS
####################################

ENABLE_FORWARD_USER_INFO_HEADERS = (
    os.environ.get("ENABLE_FORWARD_USER_INFO_HEADERS", "False").lower() == "true"
)

####################################
# WEBUI_BUILD_HASH
####################################

WEBUI_BUILD_HASH = os.environ.get("WEBUI_BUILD_HASH", "dev-build")

####################################
# DATA/FRONTEND BUILD DIR
####################################

DATA_DIR = Path(os.getenv("DATA_DIR", BACKEND_DIR / "data")).resolve()

if FROM_INIT_PY:
    NEW_DATA_DIR = Path(os.getenv("DATA_DIR", OPEN_WEBUI_DIR / "data")).resolve()
    NEW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check if the data directory exists in the package directory
    if DATA_DIR.exists() and DATA_DIR != NEW_DATA_DIR:
        log.info(f"Moving {DATA_DIR} to {NEW_DATA_DIR}")
        for item in DATA_DIR.iterdir():
            dest = NEW_DATA_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        # Zip the data directory
        shutil.make_archive(str(DATA_DIR.parent / "open_webui_data"), "zip", str(DATA_DIR))

        # Remove the old data directory
        shutil.rmtree(DATA_DIR)

    DATA_DIR = Path(os.getenv("DATA_DIR", OPEN_WEBUI_DIR / "data"))

STATIC_DIR = Path(os.getenv("STATIC_DIR", OPEN_WEBUI_DIR / "static"))

FONTS_DIR = Path(os.getenv("FONTS_DIR", OPEN_WEBUI_DIR / "static" / "fonts"))

FRONTEND_BUILD_DIR = Path(os.getenv("FRONTEND_BUILD_DIR", BASE_DIR / "build")).resolve()

if FROM_INIT_PY:
    FRONTEND_BUILD_DIR = Path(
        os.getenv("FRONTEND_BUILD_DIR", OPEN_WEBUI_DIR / "frontend")
    ).resolve()

####################################
# Database
####################################

# Check if the file exists
if os.path.exists(f"{DATA_DIR}/ollama.db"):
    # Rename the file
    os.rename(f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/webui.db")
    log.info("Database migrated from Ollama-WebUI successfully.")
else:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR}/webui.db")

# Replace the postgres:// with postgresql://
if "postgres://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

DATABASE_SCHEMA = os.environ.get("DATABASE_SCHEMA", None)

DATABASE_POOL_SIZE = os.environ.get("DATABASE_POOL_SIZE", 0)

if DATABASE_POOL_SIZE == "":
    DATABASE_POOL_SIZE = 0
else:
    try:
        DATABASE_POOL_SIZE = int(DATABASE_POOL_SIZE)
    except Exception:
        DATABASE_POOL_SIZE = 0

DATABASE_POOL_MAX_OVERFLOW = os.environ.get("DATABASE_POOL_MAX_OVERFLOW", 0)

if DATABASE_POOL_MAX_OVERFLOW == "":
    DATABASE_POOL_MAX_OVERFLOW = 0
else:
    try:
        DATABASE_POOL_MAX_OVERFLOW = int(DATABASE_POOL_MAX_OVERFLOW)
    except Exception:
        DATABASE_POOL_MAX_OVERFLOW = 0

DATABASE_POOL_TIMEOUT = os.environ.get("DATABASE_POOL_TIMEOUT", 30)

if DATABASE_POOL_TIMEOUT == "":
    DATABASE_POOL_TIMEOUT = 30
else:
    try:
        DATABASE_POOL_TIMEOUT = int(DATABASE_POOL_TIMEOUT)
    except Exception:
        DATABASE_POOL_TIMEOUT = 30

DATABASE_POOL_RECYCLE = os.environ.get("DATABASE_POOL_RECYCLE", 3600)

if DATABASE_POOL_RECYCLE == "":
    DATABASE_POOL_RECYCLE = 3600
else:
    try:
        DATABASE_POOL_RECYCLE = int(DATABASE_POOL_RECYCLE)
    except Exception:
        DATABASE_POOL_RECYCLE = 3600

# Database connect timeout (seconds). Helps avoid long hangs when DB is unreachable.
DATABASE_CONNECT_TIMEOUT = os.environ.get("DATABASE_CONNECT_TIMEOUT", 5)

if DATABASE_CONNECT_TIMEOUT == "":
    DATABASE_CONNECT_TIMEOUT = 5
else:
    try:
        DATABASE_CONNECT_TIMEOUT = int(DATABASE_CONNECT_TIMEOUT)
    except Exception:
        DATABASE_CONNECT_TIMEOUT = 5


def _get_admin_int(name: str, fallback: int) -> int:
    value = os.environ.get(name, "")
    if value == "":
        return fallback
    try:
        return int(value)
    except Exception:
        return fallback


ADMIN_DATABASE_URL = os.environ.get("ADMIN_DATABASE_URL", DATABASE_URL)
if "postgres://" in ADMIN_DATABASE_URL:
    ADMIN_DATABASE_URL = ADMIN_DATABASE_URL.replace("postgres://", "postgresql://")

ADMIN_DATABASE_SCHEMA = os.environ.get("ADMIN_DATABASE_SCHEMA", DATABASE_SCHEMA)
ADMIN_DATABASE_POOL_SIZE = _get_admin_int("ADMIN_DATABASE_POOL_SIZE", DATABASE_POOL_SIZE)
ADMIN_DATABASE_POOL_MAX_OVERFLOW = _get_admin_int(
    "ADMIN_DATABASE_POOL_MAX_OVERFLOW", DATABASE_POOL_MAX_OVERFLOW
)
ADMIN_DATABASE_POOL_TIMEOUT = _get_admin_int(
    "ADMIN_DATABASE_POOL_TIMEOUT", DATABASE_POOL_TIMEOUT
)
ADMIN_DATABASE_POOL_RECYCLE = _get_admin_int(
    "ADMIN_DATABASE_POOL_RECYCLE", DATABASE_POOL_RECYCLE
)

####################################
# ALERT SERVICE
####################################

ALERT_SERVICE_ADMIN_BASE_URL = os.environ.get("ALERT_SERVICE_ADMIN_BASE_URL", "")
ALERT_SERVICE_API_KEY = os.environ.get("ALERT_SERVICE_API_KEY", "")


def _get_n8n_int(name: str, fallback: int) -> int:
    value = os.environ.get(name, "")
    if value == "":
        return fallback
    try:
        return int(value)
    except Exception:
        return fallback


N8N_DATABASE_URL = os.environ.get("N8N_DATABASE_URL", "")

if not N8N_DATABASE_URL:
    N8N_DATABASE_URL = DATABASE_URL

if "postgres://" in N8N_DATABASE_URL:
    N8N_DATABASE_URL = N8N_DATABASE_URL.replace("postgres://", "postgresql://")

N8N_DATABASE_SCHEMA = os.environ.get("N8N_DATABASE_SCHEMA", DATABASE_SCHEMA)
N8N_DATABASE_POOL_SIZE = _get_n8n_int("N8N_DATABASE_POOL_SIZE", DATABASE_POOL_SIZE)
N8N_DATABASE_POOL_MAX_OVERFLOW = _get_n8n_int(
    "N8N_DATABASE_POOL_MAX_OVERFLOW", DATABASE_POOL_MAX_OVERFLOW
)
N8N_DATABASE_POOL_TIMEOUT = _get_n8n_int(
    "N8N_DATABASE_POOL_TIMEOUT", DATABASE_POOL_TIMEOUT
)
N8N_DATABASE_POOL_RECYCLE = _get_n8n_int(
    "N8N_DATABASE_POOL_RECYCLE", DATABASE_POOL_RECYCLE
)
ENV_REQUIRE_N8N = os.environ.get("ENV_REQUIRE_N8N", "true").lower() not in {
    "false",
    "0",
    "no",
}
_raw_required_tables = os.environ.get(
    "N8N_REQUIRED_TABLES", "hsai_business_api_usage_log,hsai_business_good_video_v1"
)
N8N_REQUIRED_TABLES = [
    table.strip()
    for table in _raw_required_tables.split(",")
    if table.strip()
]


RESET_CONFIG_ON_START = (
    os.environ.get("RESET_CONFIG_ON_START", "False").lower() == "true"
)

ENABLE_REALTIME_CHAT_SAVE = (
    os.environ.get("ENABLE_REALTIME_CHAT_SAVE", "False").lower() == "true"
)

####################################
# REDIS
####################################

# Redis模式配置
REDIS_MODE = os.environ.get("REDIS_MODE", "internal")

# 内网Redis配置
INTERNAL_REDIS_URL = os.environ.get("INTERNAL_REDIS_URL", "redis://localhost:6379/0")
INTERNAL_WEBSOCKET_REDIS_URL = os.environ.get("INTERNAL_WEBSOCKET_REDIS_URL", "")

# 公网Redis配置
EXTERNAL_REDIS_HOST = os.environ.get("EXTERNAL_REDIS_HOST", "")
EXTERNAL_REDIS_PORT = os.environ.get("EXTERNAL_REDIS_PORT", "6379")
EXTERNAL_REDIS_DB = os.environ.get("EXTERNAL_REDIS_DB", "0")
EXTERNAL_REDIS_USERNAME = os.environ.get("EXTERNAL_REDIS_USERNAME", "")
EXTERNAL_REDIS_PASSWORD = os.environ.get("EXTERNAL_REDIS_PASSWORD", "")
EXTERNAL_WEBSOCKET_REDIS_HOST = os.environ.get("EXTERNAL_WEBSOCKET_REDIS_HOST", "")
EXTERNAL_WEBSOCKET_REDIS_PORT = os.environ.get("EXTERNAL_WEBSOCKET_REDIS_PORT", "6379")
EXTERNAL_WEBSOCKET_REDIS_DB = os.environ.get("EXTERNAL_WEBSOCKET_REDIS_DB", "0")
EXTERNAL_WEBSOCKET_REDIS_USERNAME = os.environ.get("EXTERNAL_WEBSOCKET_REDIS_USERNAME", "")
EXTERNAL_WEBSOCKET_REDIS_PASSWORD = os.environ.get("EXTERNAL_WEBSOCKET_REDIS_PASSWORD", "")

# 根据模式自动选择Redis配置
if REDIS_MODE == "external" and EXTERNAL_REDIS_HOST:
    # 构建公网Redis URL
    if EXTERNAL_REDIS_USERNAME and EXTERNAL_REDIS_PASSWORD:
        REDIS_URL = f"redis://{EXTERNAL_REDIS_USERNAME}:{EXTERNAL_REDIS_PASSWORD}@{EXTERNAL_REDIS_HOST}:{EXTERNAL_REDIS_PORT}/{EXTERNAL_REDIS_DB}"
    else:
        REDIS_URL = f"redis://{EXTERNAL_REDIS_HOST}:{EXTERNAL_REDIS_PORT}/{EXTERNAL_REDIS_DB}"
else:
    # 使用内网Redis配置
    REDIS_URL = os.environ.get("REDIS_URL", INTERNAL_REDIS_URL)

REDIS_SENTINEL_HOSTS = os.environ.get("REDIS_SENTINEL_HOSTS", "")
REDIS_SENTINEL_PORT = os.environ.get("REDIS_SENTINEL_PORT", "26379")

# Redis client timeouts (seconds)
try:
    REDIS_SOCKET_TIMEOUT_SECONDS = int(os.environ.get("REDIS_SOCKET_TIMEOUT_SECONDS", "5"))
except ValueError:
    REDIS_SOCKET_TIMEOUT_SECONDS = 5
REDIS_SOCKET_TIMEOUT_SECONDS = max(1, REDIS_SOCKET_TIMEOUT_SECONDS)

try:
    REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS = int(os.environ.get("REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS", "5"))
except ValueError:
    REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS = 5
REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS = max(1, REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS)

try:
    REDIS_HEALTH_CHECK_INTERVAL_SECONDS = int(os.environ.get("REDIS_HEALTH_CHECK_INTERVAL_SECONDS", "30"))
except ValueError:
    REDIS_HEALTH_CHECK_INTERVAL_SECONDS = 30
REDIS_HEALTH_CHECK_INTERVAL_SECONDS = max(0, REDIS_HEALTH_CHECK_INTERVAL_SECONDS)

REDIS_RETRY_ON_TIMEOUT = os.environ.get("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"

# Enable Redis queue listener (default: False)
# When multiple instances are running, only one should listen to avoid message contention
ENABLE_REDIS_QUEUE_LISTENER = (
    os.environ.get("ENABLE_REDIS_QUEUE_LISTENER", "False").lower() == "true"
)

####################################
# HSAI MATERIALS CACHE / OSS SYNC
####################################

HSAI_MATERIALS_CACHE_ENABLED = (
    os.environ.get("HSAI_MATERIALS_CACHE_ENABLED", "true").lower() == "true"
)

try:
    HSAI_MATERIALS_CACHE_TTL_SEC = int(os.environ.get("HSAI_MATERIALS_CACHE_TTL_SEC", "900"))
except ValueError:
    HSAI_MATERIALS_CACHE_TTL_SEC = 900
HSAI_MATERIALS_CACHE_TTL_SEC = max(HSAI_MATERIALS_CACHE_TTL_SEC, 30)

try:
    HSAI_MATERIALS_CACHE_REFRESH_INTERVAL_SEC = int(
        os.environ.get("HSAI_MATERIALS_CACHE_REFRESH_INTERVAL_SEC", "300")
    )
except ValueError:
    HSAI_MATERIALS_CACHE_REFRESH_INTERVAL_SEC = 300
HSAI_MATERIALS_CACHE_REFRESH_INTERVAL_SEC = max(
    HSAI_MATERIALS_CACHE_REFRESH_INTERVAL_SEC, 30
)

try:
    HSAI_MATERIALS_CACHE_ACTIVE_COMPANIES_SCAN_COUNT = int(
        os.environ.get("HSAI_MATERIALS_CACHE_ACTIVE_COMPANIES_SCAN_COUNT", "200")
    )
except ValueError:
    HSAI_MATERIALS_CACHE_ACTIVE_COMPANIES_SCAN_COUNT = 200
HSAI_MATERIALS_CACHE_ACTIVE_COMPANIES_SCAN_COUNT = min(max(HSAI_MATERIALS_CACHE_ACTIVE_COMPANIES_SCAN_COUNT, 1), 1000)

try:
    HSAI_MATERIALS_CACHE_MAX_COMPANIES_PER_REFRESH = int(
        os.environ.get("HSAI_MATERIALS_CACHE_MAX_COMPANIES_PER_REFRESH", "200")
    )
except ValueError:
    HSAI_MATERIALS_CACHE_MAX_COMPANIES_PER_REFRESH = 200
HSAI_MATERIALS_CACHE_MAX_COMPANIES_PER_REFRESH = max(0, HSAI_MATERIALS_CACHE_MAX_COMPANIES_PER_REFRESH)

HSAI_MATERIALS_OSS_SYNC_ENABLED = (
    os.environ.get("HSAI_MATERIALS_OSS_SYNC_ENABLED", "true").lower() == "true"
)

try:
    HSAI_MATERIALS_OSS_MAX_KEYS = int(os.environ.get("HSAI_MATERIALS_OSS_MAX_KEYS", "1000"))
except ValueError:
    HSAI_MATERIALS_OSS_MAX_KEYS = 1000
HSAI_MATERIALS_OSS_MAX_KEYS = min(max(HSAI_MATERIALS_OSS_MAX_KEYS, 1), 1000)

HSAI_MATERIALS_OSS_BUCKET = os.environ.get("HSAI_MATERIALS_OSS_BUCKET", "").strip() or None

####################################
# UVICORN WORKERS
####################################

# Number of uvicorn worker processes for handling requests
UVICORN_WORKERS = os.environ.get("UVICORN_WORKERS", "1")
try:
    UVICORN_WORKERS = int(UVICORN_WORKERS)
    if UVICORN_WORKERS < 1:
        UVICORN_WORKERS = 1
except ValueError:
    UVICORN_WORKERS = 1
    log.info(f"Invalid UVICORN_WORKERS value, defaulting to {UVICORN_WORKERS}")

####################################
# WEBUI_AUTH (Required for security)
####################################

WEBUI_AUTH = os.environ.get("WEBUI_AUTH", "True").lower() == "true"
WEBUI_AUTH_TRUSTED_EMAIL_HEADER = os.environ.get(
    "WEBUI_AUTH_TRUSTED_EMAIL_HEADER", None
)
WEBUI_AUTH_TRUSTED_NAME_HEADER = os.environ.get("WEBUI_AUTH_TRUSTED_NAME_HEADER", None)
WEBUI_AUTH_TRUSTED_GROUPS_HEADER = os.environ.get(
    "WEBUI_AUTH_TRUSTED_GROUPS_HEADER", None
)


BYPASS_MODEL_ACCESS_CONTROL = (
    os.environ.get("BYPASS_MODEL_ACCESS_CONTROL", "False").lower() == "true"
)

WEBUI_AUTH_SIGNOUT_REDIRECT_URL = os.environ.get(
    "WEBUI_AUTH_SIGNOUT_REDIRECT_URL", None
)

####################################
# WEBUI_SECRET_KEY
####################################

WEBUI_SECRET_KEY = os.environ.get(
    "WEBUI_SECRET_KEY",
    os.environ.get(
        "WEBUI_JWT_SECRET_KEY", "t0p-s3cr3t"
    ),  # DEPRECATED: remove at next major version
)

WEBUI_SESSION_COOKIE_SAME_SITE = os.environ.get("WEBUI_SESSION_COOKIE_SAME_SITE", "lax")

WEBUI_SESSION_COOKIE_SECURE = (
    os.environ.get("WEBUI_SESSION_COOKIE_SECURE", "false").lower() == "true"
)

WEBUI_AUTH_COOKIE_SAME_SITE = os.environ.get(
    "WEBUI_AUTH_COOKIE_SAME_SITE", WEBUI_SESSION_COOKIE_SAME_SITE
)

WEBUI_AUTH_COOKIE_SECURE = (
    os.environ.get(
        "WEBUI_AUTH_COOKIE_SECURE",
        os.environ.get("WEBUI_SESSION_COOKIE_SECURE", "false"),
    ).lower()
    == "true"
)

if WEBUI_AUTH and WEBUI_SECRET_KEY == "":
    raise ValueError(ERROR_MESSAGES.ENV_VAR_NOT_FOUND)

ENABLE_WEBSOCKET_SUPPORT = (
    os.environ.get("ENABLE_WEBSOCKET_SUPPORT", "True").lower() == "true"
)

WEBSOCKET_MANAGER = os.environ.get("WEBSOCKET_MANAGER", "")

# 根据模式自动选择WebSocket Redis配置
if REDIS_MODE == "external" and EXTERNAL_WEBSOCKET_REDIS_HOST:
    # 构建公网WebSocket Redis URL
    if EXTERNAL_WEBSOCKET_REDIS_USERNAME and EXTERNAL_WEBSOCKET_REDIS_PASSWORD:
        WEBSOCKET_REDIS_URL = f"redis://{EXTERNAL_WEBSOCKET_REDIS_USERNAME}:{EXTERNAL_WEBSOCKET_REDIS_PASSWORD}@{EXTERNAL_WEBSOCKET_REDIS_HOST}:{EXTERNAL_WEBSOCKET_REDIS_PORT}/{EXTERNAL_WEBSOCKET_REDIS_DB}"
    else:
        WEBSOCKET_REDIS_URL = f"redis://{EXTERNAL_WEBSOCKET_REDIS_HOST}:{EXTERNAL_WEBSOCKET_REDIS_PORT}/{EXTERNAL_WEBSOCKET_REDIS_DB}"
else:
    # 使用内网WebSocket Redis配置
    WEBSOCKET_REDIS_URL = os.environ.get("WEBSOCKET_REDIS_URL", INTERNAL_WEBSOCKET_REDIS_URL if INTERNAL_WEBSOCKET_REDIS_URL else REDIS_URL)

WEBSOCKET_REDIS_LOCK_TIMEOUT = os.environ.get("WEBSOCKET_REDIS_LOCK_TIMEOUT", 60)

WEBSOCKET_SENTINEL_HOSTS = os.environ.get("WEBSOCKET_SENTINEL_HOSTS", "")

WEBSOCKET_SENTINEL_PORT = os.environ.get("WEBSOCKET_SENTINEL_PORT", "26379")

AIOHTTP_CLIENT_TIMEOUT = os.environ.get("AIOHTTP_CLIENT_TIMEOUT", "")

if AIOHTTP_CLIENT_TIMEOUT == "":
    AIOHTTP_CLIENT_TIMEOUT = None
else:
    try:
        AIOHTTP_CLIENT_TIMEOUT = int(AIOHTTP_CLIENT_TIMEOUT)
    except Exception:
        AIOHTTP_CLIENT_TIMEOUT = 300


AIOHTTP_CLIENT_SESSION_SSL = (
    os.environ.get("AIOHTTP_CLIENT_SESSION_SSL", "True").lower() == "true"
)

AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = os.environ.get(
    "AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST",
    os.environ.get("AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST", "10"),
)

if AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST == "":
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = None
else:
    try:
        AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = int(AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    except Exception:
        AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = 10


AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = os.environ.get(
    "AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA", "10"
)

if AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA == "":
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = None
else:
    try:
        AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = int(
            AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA
        )
    except Exception:
        AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = 10


AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL = (
    os.environ.get("AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL", "True").lower() == "true"
)

AIOHTTP_CLIENT_READ_BUFFER_SIZE = int(
    os.environ.get("AIOHTTP_CLIENT_READ_BUFFER_SIZE", 2**16)
)

####################################
# OPS DASHBOARD INTEGRATION
####################################

OPS_DASHBOARD_ENABLED = os.environ.get(
    "OPS_DASHBOARD_ENABLED", "false"
).lower() == "true"
OPS_DASHBOARD_BASE_URL = os.environ.get("OPS_DASHBOARD_BASE_URL", "").rstrip("/")
OPS_DASHBOARD_API_KEY = os.environ.get("OPS_DASHBOARD_API_KEY", "")


def _positive_int(value: str, default: int) -> int:
    try:
        parsed = int(str(value).strip())
        return parsed if parsed > 0 else default
    except Exception:
        return default


OPS_DASHBOARD_TIMEOUT = _positive_int(
    os.environ.get("OPS_DASHBOARD_TIMEOUT", 5), 5
)
OPS_DASHBOARD_MAX_RETRY = _positive_int(
    os.environ.get("OPS_DASHBOARD_MAX_RETRY", 3), 3
)
OPS_DASHBOARD_ALLOW_CONTENT = (
    os.environ.get("OPS_DASHBOARD_ALLOW_CONTENT", "false").lower() == "true"
)
OPS_DASHBOARD_QUEUE_MAXSIZE = _positive_int(
    os.environ.get("OPS_DASHBOARD_QUEUE_MAXSIZE", 1000), 1000
)
OPS_DASHBOARD_MAX_ATTEMPTS = _positive_int(
    os.environ.get("OPS_DASHBOARD_MAX_ATTEMPTS", 3), 3
)


####################################
# SENTENCE TRANSFORMERS
####################################


SENTENCE_TRANSFORMERS_BACKEND = os.environ.get("SENTENCE_TRANSFORMERS_BACKEND", "")
if SENTENCE_TRANSFORMERS_BACKEND == "":
    SENTENCE_TRANSFORMERS_BACKEND = "torch"


SENTENCE_TRANSFORMERS_MODEL_KWARGS = os.environ.get(
    "SENTENCE_TRANSFORMERS_MODEL_KWARGS", ""
)
if SENTENCE_TRANSFORMERS_MODEL_KWARGS == "":
    SENTENCE_TRANSFORMERS_MODEL_KWARGS = None
else:
    try:
        SENTENCE_TRANSFORMERS_MODEL_KWARGS = json.loads(
            SENTENCE_TRANSFORMERS_MODEL_KWARGS
        )
    except Exception:
        SENTENCE_TRANSFORMERS_MODEL_KWARGS = None


SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND = os.environ.get(
    "SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND", ""
)
if SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND == "":
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND = "torch"


SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = os.environ.get(
    "SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS", ""
)
if SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS == "":
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = None
else:
    try:
        SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = json.loads(
            SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS
        )
    except Exception:
        SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = None

####################################
# OFFLINE_MODE
####################################

OFFLINE_MODE = os.environ.get("OFFLINE_MODE", "false").lower() == "true"

if OFFLINE_MODE:
    os.environ["HF_HUB_OFFLINE"] = "1"


####################################
# AUDIT LOGGING
####################################
# Where to store log file
AUDIT_LOGS_FILE_PATH = f"{DATA_DIR}/audit.log"
# Maximum size of a file before rotating into a new log file
AUDIT_LOG_FILE_ROTATION_SIZE = os.getenv("AUDIT_LOG_FILE_ROTATION_SIZE", "10MB")
# METADATA | REQUEST | REQUEST_RESPONSE
AUDIT_LOG_LEVEL = os.getenv("AUDIT_LOG_LEVEL", "NONE").upper()
try:
    MAX_BODY_LOG_SIZE = int(os.environ.get("MAX_BODY_LOG_SIZE") or 2048)
except ValueError:
    MAX_BODY_LOG_SIZE = 2048

# Comma separated list for urls to exclude from audit
AUDIT_EXCLUDED_PATHS = os.getenv("AUDIT_EXCLUDED_PATHS", "/chats,/chat,/folders").split(
    ","
)
AUDIT_EXCLUDED_PATHS = [path.strip() for path in AUDIT_EXCLUDED_PATHS]
AUDIT_EXCLUDED_PATHS = [path.lstrip("/") for path in AUDIT_EXCLUDED_PATHS]


####################################
# OPENTELEMETRY
####################################

ENABLE_OTEL = os.environ.get("ENABLE_OTEL", "False").lower() == "true"
ENABLE_OTEL_METRICS = os.environ.get("ENABLE_OTEL_METRICS", "False").lower() == "true"
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
)
OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "open-webui")
OTEL_RESOURCE_ATTRIBUTES = os.environ.get(
    "OTEL_RESOURCE_ATTRIBUTES", ""
)  # e.g. key1=val1,key2=val2
OTEL_TRACES_SAMPLER = os.environ.get(
    "OTEL_TRACES_SAMPLER", "parentbased_always_on"
).lower()

####################################
# TOOLS/FUNCTIONS PIP OPTIONS
####################################

PIP_OPTIONS = os.getenv("PIP_OPTIONS", "").split()
PIP_PACKAGE_INDEX_OPTIONS = os.getenv("PIP_PACKAGE_INDEX_OPTIONS", "").split()


####################################
# PROGRESSIVE WEB APP OPTIONS
####################################

EXTERNAL_PWA_MANIFEST_URL = os.environ.get("EXTERNAL_PWA_MANIFEST_URL")
