#!/usr/bin/env python3
"""
清理由组织多租户设计遗留的数据库结构。

使用方式：
    python tool/remove_legacy_organization_schema.py --database-url <DATABASE_URL> [--dry-run]

建议先使用 --dry-run 查看将执行的 SQL，再在备份数据库后正式执行。
"""

import argparse
import os
import sys
from typing import Optional

from sqlalchemy import create_engine

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from open_webui.internal.migrations import remove_legacy_organization_schema  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="移除 legacy organizations 表及相关列")
    parser.add_argument(
        "--database-url",
        dest="database_url",
        default=os.environ.get("DATABASE_URL"),
        help="数据库连接 URL，默认为环境变量 DATABASE_URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将执行的 SQL，不实际变更",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.database_url:
        print("ERROR: 未提供数据库连接信息，请通过 --database-url 或设置 DATABASE_URL。")
        return 1

    engine = create_engine(args.database_url)

    def logger(message: str) -> None:
        print(message)

    result = remove_legacy_organization_schema(
        engine, dry_run=args.dry_run, logger=logger
    )
    print("清理结果:", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
