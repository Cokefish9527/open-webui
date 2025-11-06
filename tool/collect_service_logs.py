#!/usr/bin/env python3
"""
Collect service logs for task system automated testing.

支持从指定日志文件或目录中抓取 ERROR / WARNING / 自定义关键字。
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List, Optional

from task_system_utils import init_logger, load_config


def _iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for file_path in path.rglob("*"):
        if file_path.is_file():
            yield file_path


def collect_service_logs(
    log_path: Path,
    keywords: Optional[List[str]] = None,
    limit: int = 200,
) -> List[str]:
    patterns = [re.compile(r"ERROR|WARNING", re.IGNORECASE)]
    if keywords:
        for kw in keywords:
            patterns.append(re.compile(re.escape(kw), re.IGNORECASE))

    matches: List[str] = []
    for file_path in _iter_files(log_path):
        try:
            for line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if any(p.search(line) for p in patterns):
                    matches.append(f"{file_path}: {line.strip()}")
                    if len(matches) >= limit:
                        return matches
        except Exception:  # pragma: no cover
            continue
    return matches


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="收集服务端日志关键字")
    parser.add_argument("--config", help="配置文件路径", default=None)
    parser.add_argument("--log-path", required=True, help="日志文件或目录")
    parser.add_argument("--keyword", action="append", help="额外关键字，可重复")
    parser.add_argument("--limit", type=int, default=200, help="最大匹配条数")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args(argv)
    logger = init_logger("collect_service_logs", verbose=args.verbose)

    _ = load_config(args.config)  # 仅为后续扩展保留

    path = Path(args.log_path)
    if not path.exists():
        logger.error("日志路径不存在: %s", path)
        return 1

    matches = collect_service_logs(path, keywords=args.keyword, limit=args.limit)
    if matches:
        logger.warning("发现 %s 条匹配日志：", len(matches))
        for line in matches:
            logger.warning(line)
        return 1

    logger.info("日志检查通过，未发现关键字")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
