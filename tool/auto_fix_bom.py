#!/usr/bin/env python3
"""BOM 清理脚本

用例：
    1) 根据字符扫描日志自动提取含 BOM 的文件并移除 BOM
       python tool/auto_fix_bom.py --report bom_scan.log
    2) 直接指定多个文件：
       python tool/auto_fix_bom.py --paths backend/open_webui/routers/hsai_projects.py
    3) 与字符扫描脚本串联（在 Windows PowerShell 中）：
       python tool/clean_special_chars.py --extensions .py --check | Tee-Object report.txt
       python tool/auto_fix_bom.py --report report.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Set

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR))
try:
    from clean_special_chars import BOM_BYTES  # type: ignore
except Exception:  # pragma: no cover
    BOM_BYTES = b"\xef\xbb\xbf"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="根据扫描结果或文件列表移除 UTF-8 BOM。")
    parser.add_argument(
        "--report",
        help="clean_special_chars 输出日志路径；若未指定则仅处理 --paths。",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        help="需要处理的文件路径（可与 --report 同时使用）。",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="仓库根目录（用于解析相对路径，默认当前目录）。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅输出将要修改的文件，不实际写回。",
    )
    return parser.parse_args(argv)


def read_report(report_path: Path) -> Iterable[str]:
    text = report_path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        yield line.rstrip("\n")


def extract_paths_from_report(lines: Iterable[str]) -> Set[str]:
    targets: Set[str] = set()
    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith("-"):
            # clean_special_chars 输出的条目形如 "  - <path>: 含BOM"
            continue
        if "BOM" not in line.upper():
            continue
        sep_index = line.rfind(":")
        if sep_index == -1:
            continue
        candidate = line[:sep_index].lstrip("- ").strip()
        if candidate:
            targets.add(candidate)
    return targets


def strip_bom(path: Path, dry_run: bool = False) -> bool:
    raw = path.read_bytes()
    changed = False
    if raw.startswith(BOM_BYTES):
        raw = raw[len(BOM_BYTES) :]
        changed = True

    text = raw.decode("utf-8", errors="ignore")
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
        raw = text.encode("utf-8")
        changed = True

    if changed and not dry_run:
        path.write_bytes(raw)
    return changed


def resolve_path(base: Path, path_str: str) -> Path:
    candidate = Path(path_str)
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    return candidate


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[错误] 根目录不存在：{root}", file=sys.stderr)
        return 2

    targets: Set[str] = set(args.paths or [])
    if args.report:
        report_path = Path(args.report).expanduser().resolve()
        if not report_path.exists():
            print(f"[警告] 报告文件不存在：{report_path}", file=sys.stderr)
        else:
            targets.update(extract_paths_from_report(read_report(report_path)))

    if not targets:
        print("未提供报告或显式路径，跳过。")
        return 0

    fixed: List[Path] = []
    skipped: List[str] = []

    for target in sorted(targets):
        path = resolve_path(root, target)
        try:
            path.relative_to(root)
        except ValueError:
            skipped.append(f"{path}（不在 root 内）")
            continue
        if not path.exists():
            skipped.append(f"{path}（不存在）")
            continue
        try:
            if strip_bom(path, dry_run=args.dry_run):
                fixed.append(path)
        except Exception as exc:  # pragma: no cover
            skipped.append(f"{path}（处理失败：{exc}）")

    if fixed:
        header = "[Dry Run]" if args.dry_run else "[已修复]"
        print(header, f"{len(fixed)} 个文件：")
        for item in fixed:
            print(f"  - {item}")
    else:
        print("未发现需要修复的 BOM 文件。")

    if skipped:
        print("[跳过] 以下条目未处理：")
        for item in skipped:
            print(f"  - {item}")

    if skipped and not fixed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
